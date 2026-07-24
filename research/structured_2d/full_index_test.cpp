#include "full_index.hpp"

#include "compact.hpp"
#include "microbench.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace {

constexpr std::size_t kDimensions = 132;
constexpr std::size_t kCells = 3;
constexpr std::size_t kRows = 120;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

structured2d::SharedAffineModel make_model(int word_bits) {
    const std::size_t side = word_bits == 4 ? 4 : 16;
    structured2d::SharedAffineModel model;
    model.word_bits = word_bits;
    model.shape.resize(2 * side * side);
    for (std::size_t y = 0; y < side; ++y) {
        for (std::size_t x = 0; x < side; ++x) {
            const std::size_t label = y * side + x;
            model.shape[2 * label] =
                    0.4F * static_cast<float>(x) -
                    0.2F * static_cast<float>(side - 1);
            model.shape[2 * label + 1] =
                    0.3F * static_cast<float>(y) -
                    0.15F * static_cast<float>(side - 1);
        }
    }
    model.groups.resize(a4orb::kGroups);
    for (std::size_t group = 0;
         group < model.groups.size(); ++group) {
        auto& affine = model.groups[group];
        affine.mean[0] = 0.01F * static_cast<float>(group);
        affine.mean[1] = -0.02F * static_cast<float>(group);
        affine.transform[0] =
                0.8F + 0.002F * static_cast<float>(group);
        affine.transform[1] = 0.07F;
        affine.transform[2] = -0.04F;
        affine.transform[3] =
                1.1F - 0.001F * static_cast<float>(group);
    }
    model.expanded = structured2d::expand(
            word_bits, model.shape, model.groups);
    require(structured2d::finite(model), "synthetic model finite");
    return model;
}

struct SyntheticInput {
    std::vector<float> centroids;
    std::vector<std::uint32_t> assignments;
    std::vector<std::uint32_t> ids;
    std::vector<float> base;
};

SyntheticInput make_input(
        const structured2d::SharedAffineModel& model) {
    SyntheticInput input;
    input.centroids.assign(kCells * kDimensions, 0);
    // Identical heads isolate the list-dependent, unencoded tail term.
    for (std::size_t dimension = a4orb::kPanelDimensions;
         dimension < kDimensions; ++dimension) {
        input.centroids[dimension] = 0;
        input.centroids[kDimensions + dimension] = 10;
        input.centroids[2 * kDimensions + dimension] = -10;
    }

    input.assignments.resize(kRows);
    input.ids.resize(kRows);
    input.base.resize(kRows * kDimensions);
    const std::size_t centers =
            std::size_t{1} << model.word_bits;
    for (std::size_t row = 0; row < kRows; ++row) {
        const std::size_t cell = row % kCells;
        input.assignments[row] = static_cast<std::uint32_t>(cell);
        input.ids[row] = static_cast<std::uint32_t>(
                1000 + ((37 * row) % kRows));
        for (std::size_t group = 0;
             group < a4orb::kGroups; ++group) {
            // The first row of every list shares one code; row 3 duplicates
            // row 0 inside list 0 to exercise deterministic ID tie-breaking.
            const std::size_t label = row < kCells || row == kCells
                    ? (11 * group + 3) % centers
                    : (17 * row + 13 * group + cell) % centers;
            for (std::size_t coordinate = 0; coordinate < 2;
                 ++coordinate) {
                const std::size_t dimension =
                        2 * group + coordinate;
                input.base[row * kDimensions + dimension] =
                        input.centroids[cell * kDimensions + dimension] +
                        structured2d::compact_center_coordinate(
                                model, group, label, coordinate);
            }
        }
        for (std::size_t dimension = a4orb::kPanelDimensions;
             dimension < kDimensions; ++dimension)
            input.base[row * kDimensions + dimension] =
                    input.centroids[cell * kDimensions + dimension] +
                    0.25F * static_cast<float>((row + dimension) % 5);
    }
    return input;
}

std::vector<structured2d::SearchHit> direct_top_k(
        const structured2d::FullIndex& index,
        const std::vector<float>& query,
        const std::vector<std::uint32_t>& lists,
        std::size_t top_k) {
    std::vector<structured2d::SearchHit> result;
    for (const std::uint32_t list : lists) {
        const std::size_t count = static_cast<std::size_t>(
                index.list_offsets[list + 1] -
                index.list_offsets[list]);
        for (std::size_t position = 0; position < count; ++position) {
            const std::size_t stored =
                    static_cast<std::size_t>(
                            index.list_offsets[list]) +
                    position;
            result.push_back({
                    index.ids[stored],
                    structured2d::direct_reconstruction_score(
                            index, query, list, position)});
        }
    }
    std::sort(
            result.begin(), result.end(),
            [](const auto& left, const auto& right) {
                if (left.distance != right.distance)
                    return left.distance < right.distance;
                return left.id < right.id;
            });
    if (result.size() > top_k) result.resize(top_k);
    return result;
}

void require_score_parity(
        const std::vector<structured2d::SearchHit>& actual,
        const std::vector<structured2d::SearchHit>& reference) {
    require(actual.size() == reference.size(), "reference result size");
    for (std::size_t rank = 0; rank < actual.size(); ++rank) {
        require(actual[rank].id == reference[rank].id,
                "direct result id parity");
        // Each compact table entry is independently rounded to binary32.
        // Sum the existing eight-ULP-per-entry bound over 64 groups.
        const double tolerance =
                8 * std::numeric_limits<float>::epsilon() *
                (a4orb::kGroups +
                 std::fabs(reference[rank].distance)) +
                1e-12;
        require(
                std::fabs(
                        actual[rank].distance -
                        reference[rank].distance) <= tolerance,
                "direct binary64 score parity");
    }
}

void require_index_equal(
        const structured2d::FullIndex& left,
        const structured2d::FullIndex& right) {
    require(left.dimensions == right.dimensions, "roundtrip dimensions");
    require(left.model.word_bits == right.model.word_bits,
            "roundtrip word bits");
    require(left.model.shape == right.model.shape, "roundtrip shape");
    require(left.model.groups.size() == right.model.groups.size(),
            "roundtrip groups");
    for (std::size_t group = 0;
         group < left.model.groups.size(); ++group) {
        require(
                left.model.groups[group].mean[0] ==
                                right.model.groups[group].mean[0] &&
                        left.model.groups[group].mean[1] ==
                                right.model.groups[group].mean[1],
                "roundtrip means");
        for (std::size_t entry = 0; entry < 4; ++entry)
            require(
                    left.model.groups[group].transform[entry] ==
                            right.model.groups[group].transform[entry],
                    "roundtrip transforms");
    }
    require(left.centroids == right.centroids, "roundtrip centroids");
    require(left.list_offsets == right.list_offsets, "roundtrip offsets");
    require(left.ids == right.ids, "roundtrip ids");
    require(left.payload == right.payload, "roundtrip payload");
}

void full_index_fixture(int word_bits) {
    const auto model = make_model(word_bits);
    const auto input = make_input(model);
    const auto index = structured2d::build_full_index(
            kDimensions, input.centroids, input.assignments,
            input.ids, input.base, model);
    require(structured2d::valid_full_index(index), "valid full index");
    require(index.list_offsets ==
                    std::vector<std::uint64_t>{0, 40, 80, 120},
            "multi-cell offsets");
    require(index.payload.size() ==
                    kRows *
                    structured2d::payload_bytes_per_candidate(word_bits),
            "complete packed payload");

    std::vector<float> query(kDimensions, 0);
    for (std::size_t group = 0;
         group < a4orb::kGroups; ++group) {
        const std::size_t centers = std::size_t{1} << word_bits;
        const std::size_t label = (11 * group + 3) % centers;
        query[2 * group] =
                structured2d::compact_center_coordinate(
                        model, group, label, 0);
        query[2 * group + 1] =
                structured2d::compact_center_coordinate(
                        model, group, label, 1);
    }
    for (std::size_t dimension = a4orb::kPanelDimensions;
         dimension < kDimensions; ++dimension)
        query[dimension] = 9;

    const std::vector<std::uint32_t> schedule{2, 0, 1};
    const auto actual = structured2d::search_preassigned(
            index, query, schedule, 100);
    const auto reference = direct_top_k(
            index, query, schedule, 100);
    require(actual.visited_lists == schedule, "preassigned list order");
    require(actual.candidates_scored == kRows, "candidate count");
    require(actual.hits.size() == 100, "deterministic top-100 size");
    require_score_parity(actual.hits, reference);
    require(
            structured2d::search_preassigned(
                    index, query, schedule, 100) == actual,
            "deterministic replay");

    // Candidate zero in lists 0 and 1 has the same head code. The query tail
    // is near list 1, so omitting the nonzero tail term would turn this strict
    // order into a tie.
    const double list0 = structured2d::direct_reconstruction_score(
            index, query, 0, 0);
    const double list1 = structured2d::direct_reconstruction_score(
            index, query, 1, 0);
    require(list1 + 300 < list0, "nonzero tail changes list ordering");
    const auto all = structured2d::search_preassigned(
            index, query, schedule, kRows);
    require_score_parity(
            all.hits, direct_top_k(index, query, schedule, kRows));
    std::unordered_map<std::uint32_t, double> measured;
    for (const auto& hit : all.hits)
        measured.emplace(hit.id, hit.distance);
    const std::uint32_t list0_id = index.ids[index.list_offsets[0]];
    const std::uint32_t list1_id = index.ids[index.list_offsets[1]];
    require(
            measured.at(list1_id) + 300 < measured.at(list0_id),
            "search path includes nonzero tail");

    const std::uint32_t tied_low_id = std::min(
            input.ids[0], input.ids[kCells]);
    const std::uint32_t tied_high_id = std::max(
            input.ids[0], input.ids[kCells]);
    const auto low = std::find_if(
            all.hits.begin(), all.hits.end(),
            [tied_low_id](const auto& hit) {
                return hit.id == tied_low_id;
            });
    const auto high = std::find_if(
            all.hits.begin(), all.hits.end(),
            [tied_high_id](const auto& hit) {
                return hit.id == tied_high_id;
            });
    require(low != all.hits.end() && high != all.hits.end(),
            "tied candidates present");
    require(low->distance == high->distance && low < high,
            "deterministic distance-id tie");

    const auto accounting = structured2d::byte_accounting(index);
    require(accounting.model_bytes ==
                    structured2d::persistent_model_bytes(model),
            "compact model byte accounting");
    require(accounting.packed_code_bytes == index.payload.size(),
            "payload byte accounting");
    require(accounting.complete_serialized_bytes ==
                    accounting.header_bytes + accounting.model_bytes +
                            accounting.centroid_bytes +
                            accounting.list_offset_bytes +
                            accounting.database_id_bytes +
                            accounting.packed_code_bytes,
            "complete byte accounting");

    const auto path = std::filesystem::temp_directory_path() /
            ("structured_2d_full_index_fixture_b" +
             std::to_string(word_bits) + ".bin");
    std::filesystem::remove(path);
    structured2d::save_full_index(index, path);
    require(std::filesystem::file_size(path) ==
                    accounting.complete_serialized_bytes,
            "serialized file byte accounting");
    const auto loaded = structured2d::load_full_index(path);
    require_index_equal(index, loaded);
    require(structured2d::byte_accounting(loaded).
                            complete_serialized_bytes ==
                    accounting.complete_serialized_bytes,
            "roundtrip byte accounting");
    require(
            structured2d::search_preassigned(
                    loaded, query, schedule, 100) == actual,
            "save/load search parity");
    std::filesystem::remove(path);

    bool rejected = false;
    try {
        const std::vector<std::uint32_t> duplicate{1, 1};
        (void)structured2d::search_preassigned(
                index, query, duplicate, 100);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "duplicate list rejection");
}

}  // namespace

int main() {
    try {
        full_index_fixture(4);
        full_index_fixture(8);
        std::cout << "PASS structured_2d_full_index_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
