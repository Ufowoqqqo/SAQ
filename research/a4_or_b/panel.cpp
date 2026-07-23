#include "panel.hpp"

#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>

namespace a4orb {
namespace {

constexpr const char* kInventoryHeader =
        "split\tcell_id\tvector_id\tdigest_hex\tselected_rank"
        "\tpair_id\tpair_side";

struct Inventory {
    std::vector<RowMetadata> fit;
    std::vector<RowMetadata> heldout;
};

std::uint32_t parse_u32(const std::string& value, const char* field) {
    std::size_t consumed = 0;
    const unsigned long parsed = std::stoul(value, &consumed);
    if (consumed != value.size() ||
        parsed > std::numeric_limits<std::uint32_t>::max())
        throw std::runtime_error(std::string("invalid ") + field);
    return static_cast<std::uint32_t>(parsed);
}

std::int32_t parse_i32(const std::string& value, const char* field) {
    std::size_t consumed = 0;
    const long parsed = std::stol(value, &consumed);
    if (consumed != value.size() ||
        parsed < std::numeric_limits<std::int32_t>::min() ||
        parsed > std::numeric_limits<std::int32_t>::max())
        throw std::runtime_error(std::string("invalid ") + field);
    return static_cast<std::int32_t>(parsed);
}

std::vector<std::string> split_tabs(const std::string& line) {
    std::vector<std::string> fields;
    std::size_t begin = 0;
    while (true) {
        const std::size_t end = line.find('\t', begin);
        fields.push_back(line.substr(begin, end - begin));
        if (end == std::string::npos) break;
        begin = end + 1;
    }
    return fields;
}

PairSide parse_side(const std::string& value) {
    if (value == "-") return PairSide::None;
    if (value == "left") return PairSide::Left;
    if (value == "right") return PairSide::Right;
    if (value == "unused") return PairSide::Unused;
    throw std::runtime_error("invalid pair_side");
}

Inventory read_inventory(const std::filesystem::path& path,
                         std::size_t expected_rows,
                         std::size_t expected_cells) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open inventory");
    std::string line;
    if (!std::getline(input, line) || line != kInventoryHeader)
        throw std::runtime_error("inventory header mismatch");

    Inventory result;
    result.fit.reserve(kRowsPerSplit);
    result.heldout.reserve(kRowsPerSplit);
    std::vector<std::uint8_t> seen(expected_rows, 0);
    while (std::getline(input, line)) {
        const auto fields = split_tabs(line);
        if (fields.size() != 7 || fields[3].size() != 64)
            throw std::runtime_error("inventory row shape");
        const std::uint32_t cell = parse_u32(fields[1], "cell_id");
        const std::uint32_t vector = parse_u32(fields[2], "vector_id");
        if (cell >= expected_cells || vector >= expected_rows)
            throw std::runtime_error("inventory id out of range");
        if (seen[vector]++)
            throw std::runtime_error("inventory vector appears twice");
        RowMetadata row{
                cell,
                vector,
                parse_u32(fields[4], "selected_rank"),
                parse_i32(fields[5], "pair_id"),
                parse_side(fields[6]),
        };
        if (fields[0] == "fit") {
            if (row.pair_id != -1 || row.pair_side != PairSide::None)
                throw std::runtime_error("fit row has pair metadata");
            result.fit.push_back(row);
        } else if (fields[0] == "heldout") {
            result.heldout.push_back(row);
        } else {
            throw std::runtime_error("invalid split");
        }
    }
    if (result.fit.size() != kRowsPerSplit ||
        result.heldout.size() != kRowsPerSplit)
        throw std::runtime_error("inventory split size");

    const auto order = [](const RowMetadata& a, const RowMetadata& b) {
        return std::pair{a.cell_id, a.selected_rank} <
               std::pair{b.cell_id, b.selected_rank};
    };
    if (!std::is_sorted(result.fit.begin(), result.fit.end(), order) ||
        !std::is_sorted(result.heldout.begin(), result.heldout.end(), order))
        throw std::runtime_error("inventory order");

    std::size_t index = 0;
    while (index < result.heldout.size()) {
        const auto& row = result.heldout[index];
        if (row.pair_side == PairSide::Left) {
            if (index + 1 >= result.heldout.size())
                throw std::runtime_error("truncated heldout pair");
            const auto& next = result.heldout[index + 1];
            if (next.pair_side != PairSide::Right ||
                next.cell_id != row.cell_id || next.pair_id != row.pair_id ||
                next.selected_rank != row.selected_rank + 1)
                throw std::runtime_error("heldout pair mismatch");
            index += 2;
        } else if (row.pair_side == PairSide::Unused) {
            if (row.pair_id != -1)
                throw std::runtime_error("unused row has pair id");
            ++index;
        } else {
            throw std::runtime_error("orphan heldout row");
        }
    }
    return result;
}

template <typename T>
void read_exact(std::ifstream& input, T* destination, std::size_t count,
                const char* description) {
    input.read(reinterpret_cast<char*>(destination),
               static_cast<std::streamsize>(count * sizeof(T)));
    if (!input) throw std::runtime_error(std::string("short ") + description);
}

std::vector<std::int32_t> read_assignments(const std::filesystem::path& path,
                                           std::size_t rows,
                                           std::size_t cells) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open assignments");
    std::vector<std::int32_t> result(rows);
    for (std::size_t row = 0; row < rows; ++row) {
        std::int32_t dimension = 0;
        read_exact(input, &dimension, 1, "ivecs dimension");
        if (dimension != 1) throw std::runtime_error("ivecs dimension");
        read_exact(input, &result[row], 1, "ivecs row");
        if (result[row] < 0 ||
            static_cast<std::size_t>(result[row]) >= cells)
            throw std::runtime_error("assignment out of range");
    }
    if (input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("trailing assignment bytes");
    return result;
}

std::vector<float> read_fvecs(const std::filesystem::path& path,
                              std::size_t rows, std::size_t dimensions) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open fvecs");
    std::vector<float> result(rows * dimensions);
    for (std::size_t row = 0; row < rows; ++row) {
        std::int32_t dimension = 0;
        read_exact(input, &dimension, 1, "fvecs dimension");
        if (dimension < 0 || static_cast<std::size_t>(dimension) != dimensions)
            throw std::runtime_error("fvecs dimension");
        read_exact(input, result.data() + row * dimensions, dimensions,
                   "fvecs row");
    }
    if (input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("trailing fvecs bytes");
    return result;
}

std::vector<std::size_t> group_coordinates(std::size_t dimensions) {
    if (dimensions == 0 || dimensions % 2 != 0)
        throw std::runtime_error("source dimension must be positive and even");
    const std::size_t pairs = dimensions / 2;
    std::vector<std::size_t> result;
    result.reserve(kPanelDimensions);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const std::size_t pair = ((2 * group + 1) * pairs) / 128;
        result.push_back(2 * pair);
        result.push_back(2 * pair + 1);
    }
    if (result.back() >= dimensions)
        throw std::runtime_error("coordinate out of range");
    return result;
}

struct Destination {
    std::uint8_t split = 0;
    std::uint32_t index = 0;
};

void register_destinations(
        const std::vector<RowMetadata>& metadata, std::uint8_t split,
        const std::vector<std::int32_t>& assignments,
        std::vector<Destination>& destinations) {
    for (std::size_t index = 0; index < metadata.size(); ++index) {
        const auto& meta = metadata[index];
        if (assignments[meta.vector_id] !=
            static_cast<std::int32_t>(meta.cell_id))
            throw std::runtime_error("inventory/assignment cell mismatch");
        if (destinations[meta.vector_id].split != 0)
            throw std::runtime_error("duplicate panel destination");
        destinations[meta.vector_id] = {
                split, static_cast<std::uint32_t>(index)};
    }
}

void read_selected_residuals(
        const std::filesystem::path& path, std::size_t rows,
        std::size_t dimensions, const std::vector<float>& centroids,
        const std::vector<std::int32_t>& assignments,
        const std::vector<std::size_t>& coordinates,
        const std::vector<RowMetadata>& fit_metadata,
        const std::vector<RowMetadata>& heldout_metadata,
        std::vector<float>& fit, std::vector<float>& heldout) {
    std::vector<Destination> destinations(rows);
    register_destinations(fit_metadata, 1, assignments, destinations);
    register_destinations(heldout_metadata, 2, assignments, destinations);
    fit.resize(fit_metadata.size() * coordinates.size());
    heldout.resize(heldout_metadata.size() * coordinates.size());

    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open base fvecs");
    std::vector<float> source(dimensions);
    std::size_t filled = 0;
    for (std::size_t row = 0; row < rows; ++row) {
        std::int32_t dimension = 0;
        read_exact(input, &dimension, 1, "base fvecs dimension");
        if (dimension < 0 || static_cast<std::size_t>(dimension) != dimensions)
            throw std::runtime_error("base fvecs dimension");
        read_exact(input, source.data(), dimensions, "base fvecs row");
        const Destination destination = destinations[row];
        if (destination.split == 0) continue;
        const std::size_t cell =
                static_cast<std::size_t>(assignments[row]);
        const float* center = centroids.data() + cell * dimensions;
        float* output =
                (destination.split == 1 ? fit.data() : heldout.data()) +
                static_cast<std::size_t>(destination.index) *
                        coordinates.size();
        for (std::size_t j = 0; j < coordinates.size(); ++j) {
            const std::size_t coordinate = coordinates[j];
            output[j] = source[coordinate] - center[coordinate];
        }
        ++filled;
    }
    if (input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("trailing base fvecs bytes");
    if (filled != fit_metadata.size() + heldout_metadata.size())
        throw std::runtime_error("not all selected rows were read");
}

void mix(std::uint64_t& hash, std::uint64_t value) {
    for (int byte = 0; byte < 8; ++byte) {
        hash ^= static_cast<std::uint8_t>(value >> (8 * byte));
        hash *= 1099511628211ULL;
    }
}

}  // namespace

Panel load_panel(const PanelPaths& paths, std::size_t expected_rows,
                 std::size_t expected_dimensions,
                 std::size_t expected_cells) {
    if (std::endian::native != std::endian::little)
        throw std::runtime_error("fvecs reader requires little endian");
    if (std::fegetround() != FE_TONEAREST)
        throw std::runtime_error("rounding mode must be FE_TONEAREST");
    const Inventory inventory =
            read_inventory(paths.inventory, expected_rows, expected_cells);
    const auto assignments =
            read_assignments(paths.cluster_ids, expected_rows, expected_cells);
    const auto centroids =
            read_fvecs(paths.centroids, expected_cells, expected_dimensions);
    Panel result;
    result.source_rows = expected_rows;
    result.source_dimensions = expected_dimensions;
    result.coordinates = group_coordinates(expected_dimensions);
    result.fit_rows = inventory.fit;
    result.heldout_rows = inventory.heldout;
    read_selected_residuals(
            paths.base, expected_rows, expected_dimensions, centroids,
            assignments, result.coordinates, result.fit_rows,
            result.heldout_rows, result.fit, result.heldout);
    std::set<std::uint32_t> cells;
    for (const auto& row : result.fit_rows) cells.insert(row.cell_id);
    result.eligible_cells = cells.size();
    result.heldout_pairs = static_cast<std::size_t>(
            std::count_if(result.heldout_rows.begin(), result.heldout_rows.end(),
                          [](const RowMetadata& row) {
                              return row.pair_side == PairSide::Left;
                          }));
    return result;
}

std::uint64_t panel_fingerprint(const Panel& panel) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const float value : panel.fit)
        mix(hash, std::bit_cast<std::uint32_t>(value));
    for (const float value : panel.heldout)
        mix(hash, std::bit_cast<std::uint32_t>(value));
    for (const auto& row : panel.fit_rows) {
        mix(hash, row.cell_id);
        mix(hash, row.vector_id);
    }
    for (const auto& row : panel.heldout_rows) {
        mix(hash, row.cell_id);
        mix(hash, row.vector_id);
    }
    return hash;
}

bool finite_panel(const Panel& panel) {
    return std::all_of(panel.fit.begin(), panel.fit.end(),
                       [](float value) { return std::isfinite(value); }) &&
           std::all_of(panel.heldout.begin(), panel.heldout.end(),
                       [](float value) { return std::isfinite(value); });
}

}  // namespace a4orb
