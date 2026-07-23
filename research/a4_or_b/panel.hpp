#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

namespace a4orb {

constexpr std::size_t kRowsPerSplit = 8192;
constexpr std::size_t kGroups = 64;
constexpr std::size_t kPanelDimensions = 2 * kGroups;

enum class PairSide : std::uint8_t { None, Left, Right, Unused };

struct RowMetadata {
    std::uint32_t cell_id;
    std::uint32_t vector_id;
    std::uint32_t selected_rank;
    std::int32_t pair_id;
    PairSide pair_side;
};

struct Panel {
    std::size_t source_rows = 0;
    std::size_t source_dimensions = 0;
    std::vector<std::size_t> coordinates;
    std::vector<float> fit;
    std::vector<float> heldout;
    std::vector<RowMetadata> fit_rows;
    std::vector<RowMetadata> heldout_rows;
    std::size_t eligible_cells = 0;
    std::size_t heldout_pairs = 0;
};

struct PanelPaths {
    std::filesystem::path base;
    std::filesystem::path centroids;
    std::filesystem::path cluster_ids;
    std::filesystem::path inventory;
};

Panel load_panel(const PanelPaths& paths, std::size_t expected_rows,
                 std::size_t expected_dimensions,
                 std::size_t expected_cells = 512);
std::uint64_t panel_fingerprint(const Panel& panel);
bool finite_panel(const Panel& panel);

}  // namespace a4orb
