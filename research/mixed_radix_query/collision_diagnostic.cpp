#include "../structured_2d/dataset_io.hpp"
#include "../structured_2d/synthetic_timing.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/index_io.h>
#include <faiss/invlists/InvertedLists.h>
#include <omp.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kHead = 128;
constexpr std::size_t kGroups = 64;
constexpr std::size_t kTopK = 100;
constexpr std::size_t kBaseRows = 1000000;
constexpr std::size_t kLabels = 256;
constexpr std::size_t kMaskWords = kLabels / 64;

struct Shape {
    std::vector<std::uint16_t> radices;
    std::vector<std::uint16_t> used_states;
};

struct IndexData {
    std::unique_ptr<faiss::Index> owner;
    faiss::IndexIVFPQ* index = nullptr;
    std::vector<std::uint8_t> codes;
    std::vector<std::uint32_t> assignments;
};

struct Aggregate {
    std::uint64_t queries = 0;
    std::uint64_t a_hits = 0;
    std::uint64_t d_hits = 0;
    std::uint64_t candidate_hits = 0;
    std::uint64_t candidate_misses = 0;
    std::uint64_t full_witness_misses = 0;
    std::uint64_t group_witness_misses = 0;
    std::uint64_t full_ceiling_hits = 0;
    std::uint64_t group_ceiling_hits = 0;
    std::uint64_t queries_with_full_witness = 0;
    std::uint64_t queries_with_group_witness = 0;
};

std::vector<std::size_t> probes(std::size_t nlist) {
    if (nlist == 1024)
        return {1, 2, 4, 8, 16, 32, 64, 128, 256};
    if (nlist == 4096)
        return {4, 8, 16, 32, 64, 128, 256, 512, 1024};
    throw std::invalid_argument("collision nlist");
}

Shape read_a_shape(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    Shape shape;
    shape.radices.resize(kGroups);
    shape.used_states.resize(kGroups);
    for (std::size_t group = 0; group < kGroups; ++group) {
        input.read(reinterpret_cast<char*>(&shape.radices[group]), 2);
        input.read(reinterpret_cast<char*>(&shape.used_states[group]), 2);
    }
    if (!input || input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("A shape sidecar");
    return shape;
}

Shape read_d_shape(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    Shape shape;
    shape.radices.resize(kGroups);
    shape.used_states.assign(kGroups, kLabels);
    input.read(
            reinterpret_cast<char*>(shape.radices.data()),
            static_cast<std::streamsize>(kGroups * 2));
    if (!input || input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("D radix sidecar");
    return shape;
}

IndexData load_index(const std::filesystem::path& path) {
    IndexData result;
    result.owner.reset(faiss::read_index(path.c_str()));
    result.index = dynamic_cast<faiss::IndexIVFPQ*>(result.owner.get());
    if (result.index == nullptr || result.index->d != kHead ||
        result.index->pq.M != kGroups || result.index->pq.nbits != 8 ||
        result.index->ntotal != kBaseRows)
        throw std::runtime_error("collision index shape");
    result.codes.resize(kBaseRows * result.index->code_size);
    result.assignments.resize(kBaseRows);
    std::vector<bool> seen(kBaseRows, false);
    std::size_t counted = 0;
    for (std::size_t list = 0; list < result.index->nlist; ++list) {
        faiss::InvertedLists::ScopedCodes codes(
                result.index->invlists, list);
        faiss::InvertedLists::ScopedIds ids(
                result.index->invlists, list);
        const std::size_t size =
                result.index->invlists->list_size(list);
        for (std::size_t offset = 0; offset < size; ++offset) {
            const faiss::idx_t id = ids.get()[offset];
            if (id < 0 || id >= static_cast<faiss::idx_t>(kBaseRows) ||
                seen[static_cast<std::size_t>(id)])
                throw std::runtime_error("collision index ID layout");
            const std::size_t row = static_cast<std::size_t>(id);
            seen[row] = true;
            result.assignments[row] = static_cast<std::uint32_t>(list);
            std::memcpy(
                    result.codes.data() + row * result.index->code_size,
                    codes.get() + offset * result.index->code_size,
                    result.index->code_size);
            ++counted;
        }
    }
    if (counted != kBaseRows)
        throw std::runtime_error("collision index missing IDs");
    return result;
}

const std::uint8_t* code(const IndexData& data, faiss::idx_t id) {
    if (id < 0 || id >= static_cast<faiss::idx_t>(kBaseRows))
        throw std::out_of_range("collision code ID");
    return data.codes.data() +
            static_cast<std::size_t>(id) * data.index->code_size;
}

bool contains(std::span<const std::uint32_t> sorted, faiss::idx_t id) {
    return id >= 0 && std::binary_search(
            sorted.begin(), sorted.end(), static_cast<std::uint32_t>(id));
}

std::size_t recall_hits(
        std::span<const std::uint32_t> truth,
        const structured2d::admission::TopKResult& result) {
    return std::count_if(
            result.ids.begin(), result.ids.end(),
            [&](faiss::idx_t id) { return contains(truth, id); });
}

bool full_code_witness(
        faiss::idx_t missing, std::span<const faiss::idx_t> false_ids,
        const IndexData& a, const IndexData& d) {
    const std::uint8_t* missing_d = code(d, missing);
    const std::uint8_t* missing_a = code(a, missing);
    for (const faiss::idx_t false_id : false_ids)
        if (std::memcmp(
                    missing_d, code(d, false_id), d.index->code_size) == 0 &&
            std::memcmp(
                    missing_a, code(a, false_id), a.index->code_size) != 0)
            return true;
    return false;
}

std::size_t mask_offset(
        std::size_t changed_index, std::uint8_t d_label,
        std::size_t word) {
    return (changed_index * kLabels + d_label) * kMaskWords + word;
}

std::vector<bool> group_witnesses(
        faiss::idx_t missing, std::span<const std::size_t> changed,
        std::span<const std::uint64_t> false_masks,
        const IndexData& a, const IndexData& d) {
    std::vector<bool> result(changed.size(), false);
    const std::uint8_t* missing_a = code(a, missing);
    const std::uint8_t* missing_d = code(d, missing);
    for (std::size_t index = 0; index < changed.size(); ++index) {
        const std::size_t group = changed[index];
        const std::uint8_t a_label = missing_a[group];
        const std::size_t same_word = a_label / 64;
        const std::uint64_t same_bit = std::uint64_t{1} << (a_label % 64);
        for (std::size_t word = 0; word < kMaskWords; ++word) {
            std::uint64_t mask = false_masks[mask_offset(
                    index, missing_d[group], word)];
            if (word == same_word) mask &= ~same_bit;
            result[index] = result[index] || mask != 0;
        }
    }
    return result;
}

void self_test() {
    std::vector<std::uint8_t> a_codes(kBaseRows * kGroups, 0);
    std::vector<std::uint8_t> d_codes(kBaseRows * kGroups, 0);
    IndexData a, d;
    faiss::IndexFlatL2 coarse(kHead);
    a.owner = std::make_unique<faiss::IndexIVFPQ>(
            &coarse, kHead, 1, kGroups, 8, faiss::METRIC_L2);
    d.owner = std::make_unique<faiss::IndexIVFPQ>(
            &coarse, kHead, 1, kGroups, 8, faiss::METRIC_L2);
    a.index = dynamic_cast<faiss::IndexIVFPQ*>(a.owner.get());
    d.index = dynamic_cast<faiss::IndexIVFPQ*>(d.owner.get());
    a.codes = std::move(a_codes);
    d.codes = std::move(d_codes);
    a.codes[0] = 3;
    a.codes[kGroups] = 5;
    d.codes[0] = 7;
    d.codes[kGroups] = 7;
    const std::array<faiss::idx_t, 1> false_ids{1};
    if (!full_code_witness(0, false_ids, a, d))
        throw std::runtime_error("full-code self-test");
    std::vector<std::uint64_t> masks(kLabels * kMaskWords, 0);
    masks[mask_offset(0, 7, 5 / 64)] |= std::uint64_t{1} << (5 % 64);
    const std::array<std::size_t, 1> changed{0};
    if (!group_witnesses(0, changed, masks, a, d)[0])
        throw std::runtime_error("group self-test");
    masks.assign(kLabels * kMaskWords, 0);
    masks[mask_offset(0, 7, 3 / 64)] |= std::uint64_t{1} << (3 % 64);
    if (group_witnesses(0, changed, masks, a, d)[0])
        throw std::runtime_error("same-A-label self-test");
}

struct Outputs {
    std::ofstream summary;
    std::ofstream groups;
};

void write_headers(Outputs& output) {
    output.summary <<
            "dataset\tnlist\tnprobe\tqueries\tchanged_groups"
            "\ta_hits\td_hits\tcandidate_hits\tcandidate_present_d_misses"
            "\tfull_code_witness_misses\tchanged_group_witness_misses"
            "\tqueries_with_full_witness\tqueries_with_group_witness"
            "\ta_recall\td_recall\tcandidate_recall_ceiling"
            "\tfull_code_collision_ceiling\tchanged_group_collision_ceiling"
            "\tfull_code_ceiling_delta\tchanged_group_ceiling_delta\n";
    output.groups <<
            "dataset\tnlist\tnprobe\tgroup\ta_k1\ta_k2\ta_used"
            "\td_k1\td_k2\td_used\twitnessed_candidate_misses\n";
}

void run_cell(
        const std::string& dataset, std::size_t nlist,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& schedule_root,
        const std::filesystem::path& data_root,
        Outputs& output) {
    const std::size_t dimensions = dataset == "sift" ? 128 : 960;
    const std::size_t query_count = dataset == "sift" ? 10000 : 1000;
    const std::size_t tail_start = dataset == "gist" ? kHead : dimensions;
    const auto cell_dir = pool_root / dataset /
            ("nlist_" + std::to_string(nlist));
    IndexData a = load_index(cell_dir / "A128_B8.faiss");
    IndexData d = load_index(cell_dir / "D128_B8.faiss");
    if (a.assignments != d.assignments)
        throw std::runtime_error("A/D base assignment mismatch");
    const Shape a_shape = read_a_shape(
            cell_dir / "A128_B8.faiss.shape.u16");
    const Shape d_shape = read_d_shape(
            cell_dir / "D128_B8.faiss.radix.u16");
    std::vector<std::size_t> changed;
    for (std::size_t group = 0; group < kGroups; ++group) {
        if (a_shape.radices[group] == 0 || d_shape.radices[group] == 0 ||
            a_shape.used_states[group] % a_shape.radices[group] != 0 ||
            d_shape.used_states[group] % d_shape.radices[group] != 0)
            throw std::runtime_error("invalid collision shape");
        if (a_shape.radices[group] != d_shape.radices[group] ||
            a_shape.used_states[group] != d_shape.used_states[group])
            changed.push_back(group);
    }

    const auto schedule = schedule_root / dataset;
    structured2d::admission::FvecsReader query_reader(
            schedule / "query_pca.fvecs", query_count, dimensions);
    const auto queries = structured2d::admission::read_all(query_reader);
    const auto frozen_probes = probes(nlist);
    const auto selected_u32 = structured2d::admission::read_u32(
            schedule / ("nlist_" + std::to_string(nlist)) /
                    "query_selected_lists.u32",
            query_count * frozen_probes.back());
    std::vector<faiss::idx_t> selected(
            selected_u32.begin(), selected_u32.end());
    auto truth = structured2d::admission::read_ivecs(
            data_root / dataset /
                    (dataset + "_groundtruth.ivecs"),
            query_count, kTopK, kBaseRows, true);
    for (std::size_t query = 0; query < query_count; ++query)
        std::sort(
                truth.begin() + query * kTopK,
                truth.begin() + (query + 1) * kTopK);
    std::unique_ptr<faiss::Index> coarse_owner(faiss::read_index(
            (admission_root / dataset /
             ("nlist_" + std::to_string(nlist)) / "coarse.faiss").c_str()));
    const auto* coarse = dynamic_cast<const faiss::IndexFlatL2*>(
            coarse_owner.get());
    if (coarse == nullptr || coarse->d != static_cast<int>(dimensions) ||
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("collision coarse index");
    const std::span<const float> centroids(
            coarse->get_xb(), nlist * dimensions);

    for (const std::size_t nprobe : frozen_probes) {
        Aggregate aggregate;
        std::vector<std::uint64_t> group_misses(changed.size(), 0);
        std::vector<std::uint32_t> list_stamp(nlist, 0);
        for (std::size_t query = 0; query < query_count; ++query) {
            const auto query_vector = std::span<const float>(
                    queries.data() + query * dimensions, dimensions);
            const auto lists = std::span<const faiss::idx_t>(
                    selected.data() + query * frozen_probes.back(), nprobe);
            auto a_result =
                    structured2d::admission::search_mixed_radix_lists(
                            *a.index, a_shape.radices, a_shape.used_states,
                            query_vector, centroids, dimensions, tail_start,
                            lists, kTopK);
            auto d_result =
                    structured2d::admission::search_mixed_radix_lists(
                            *d.index, d_shape.radices, d_shape.used_states,
                            query_vector, centroids, dimensions, tail_start,
                            lists, kTopK);
            structured2d::admission::normalize_topk(a_result, kTopK);
            structured2d::admission::normalize_topk(d_result, kTopK);
            const auto truth_row = std::span<const std::uint32_t>(
                    truth.data() + query * kTopK, kTopK);
            const std::size_t a_hits = recall_hits(truth_row, a_result);
            const std::size_t d_hits = recall_hits(truth_row, d_result);
            aggregate.a_hits += a_hits;
            aggregate.d_hits += d_hits;
            ++aggregate.queries;

            const std::uint32_t stamp = static_cast<std::uint32_t>(query + 1);
            for (const faiss::idx_t list : lists) {
                if (list < 0 || list >= static_cast<faiss::idx_t>(nlist))
                    throw std::runtime_error("selected list range");
                list_stamp[static_cast<std::size_t>(list)] = stamp;
            }
            std::vector<faiss::idx_t> returned = d_result.ids;
            std::sort(returned.begin(), returned.end());
            std::vector<faiss::idx_t> false_ids;
            for (const faiss::idx_t id : d_result.ids)
                if (id >= 0 && !contains(truth_row, id))
                    false_ids.push_back(id);
            std::vector<faiss::idx_t> missing;
            std::size_t candidate_hits = 0;
            for (const std::uint32_t id : truth_row) {
                const bool present = list_stamp[d.assignments[id]] == stamp;
                candidate_hits += present;
                if (present && !std::binary_search(
                            returned.begin(), returned.end(),
                            static_cast<faiss::idx_t>(id)))
                    missing.push_back(id);
            }
            aggregate.candidate_hits += candidate_hits;
            aggregate.candidate_misses += missing.size();

            std::vector<std::uint64_t> masks(
                    changed.size() * kLabels * kMaskWords, 0);
            for (const faiss::idx_t id : false_ids) {
                const std::uint8_t* a_code = code(a, id);
                const std::uint8_t* d_code = code(d, id);
                for (std::size_t index = 0; index < changed.size(); ++index) {
                    const std::size_t group = changed[index];
                    const std::uint8_t label = a_code[group];
                    masks[mask_offset(
                            index, d_code[group], label / 64)] |=
                            std::uint64_t{1} << (label % 64);
                }
            }
            std::size_t full_witnesses = 0;
            std::size_t group_witness_count = 0;
            for (const faiss::idx_t id : missing) {
                full_witnesses += full_code_witness(
                        id, false_ids, a, d);
                const auto witnessed = group_witnesses(
                        id, changed, masks, a, d);
                const bool any = std::any_of(
                        witnessed.begin(), witnessed.end(),
                        [](bool value) { return value; });
                group_witness_count += any;
                for (std::size_t index = 0;
                     index < witnessed.size(); ++index)
                    group_misses[index] += witnessed[index];
            }
            aggregate.full_witness_misses += full_witnesses;
            aggregate.group_witness_misses += group_witness_count;
            aggregate.queries_with_full_witness += full_witnesses != 0;
            aggregate.queries_with_group_witness +=
                    group_witness_count != 0;
            aggregate.full_ceiling_hits += std::min(
                    kTopK, d_hits + full_witnesses);
            aggregate.group_ceiling_hits += std::min(
                    kTopK, d_hits + group_witness_count);
        }
        const double denominator =
                static_cast<double>(aggregate.queries * kTopK);
        const double d_recall = aggregate.d_hits / denominator;
        const double full_ceiling =
                aggregate.full_ceiling_hits / denominator;
        const double group_ceiling =
                aggregate.group_ceiling_hits / denominator;
        output.summary << std::setprecision(17)
                << dataset << '\t' << nlist << '\t' << nprobe << '\t'
                << aggregate.queries << '\t' << changed.size() << '\t'
                << aggregate.a_hits << '\t' << aggregate.d_hits << '\t'
                << aggregate.candidate_hits << '\t'
                << aggregate.candidate_misses << '\t'
                << aggregate.full_witness_misses << '\t'
                << aggregate.group_witness_misses << '\t'
                << aggregate.queries_with_full_witness << '\t'
                << aggregate.queries_with_group_witness << '\t'
                << aggregate.a_hits / denominator << '\t' << d_recall
                << '\t' << aggregate.candidate_hits / denominator << '\t'
                << full_ceiling << '\t' << group_ceiling << '\t'
                << full_ceiling - d_recall << '\t'
                << group_ceiling - d_recall << '\n';
        for (std::size_t index = 0; index < changed.size(); ++index) {
            const std::size_t group = changed[index];
            output.groups << dataset << '\t' << nlist << '\t' << nprobe
                    << '\t' << group << '\t'
                    << a_shape.radices[group] << '\t'
                    << a_shape.used_states[group] / a_shape.radices[group]
                    << '\t' << a_shape.used_states[group] << '\t'
                    << d_shape.radices[group] << '\t'
                    << d_shape.used_states[group] / d_shape.radices[group]
                    << '\t' << d_shape.used_states[group] << '\t'
                    << group_misses[index] << '\n';
        }
        output.summary.flush();
        output.groups.flush();
        std::cerr << "DONE " << dataset << " nlist=" << nlist
                  << " nprobe=" << nprobe << '\n';
    }
}

void run(
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& schedule_root,
        const std::filesystem::path& data_root,
        const std::filesystem::path& summary_path,
        const std::filesystem::path& groups_path) {
    Outputs output{
            std::ofstream(summary_path, std::ios::trunc),
            std::ofstream(groups_path, std::ios::trunc)};
    if (!output.summary || !output.groups)
        throw std::runtime_error("collision output open");
    write_headers(output);
    for (const std::string dataset : {"sift", "gist"})
        for (const std::size_t nlist : {1024, 4096}) {
            std::cerr << "RUN " << dataset << " nlist=" << nlist << '\n';
            run_cell(
                    dataset, nlist, admission_root, pool_root,
                    schedule_root, data_root, output);
        }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        omp_set_dynamic(0);
        omp_set_num_threads(1);
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            self_test();
            std::cout << "PASS\n";
            return 0;
        }
        if (argc != 7)
            throw std::invalid_argument(
                    "usage: mixed_radix_collision_diagnostic "
                    "<admission_root> <pool_root> <schedule_root> "
                    "<data_root> <summary.tsv> <groups.tsv>; or --self-test");
        self_test();
        run(argv[1], argv[2], argv[3], argv[4], argv[5], argv[6]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "mixed_radix_collision_diagnostic: "
                  << error.what() << '\n';
        return 1;
    }
}
