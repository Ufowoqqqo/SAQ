#pragma once

#include <algorithm>
#include <bit>
#include <cstddef>
#include <numeric>
#include <stdexcept>
#include <utility>
#include <vector>

#include "defines.hpp"
#include "quantization/cluster_data.hpp"
#include "quantization/saq_data.hpp"

namespace saqlib::analysis {

constexpr size_t kCacheLineBytes = 64;
// Mirrors SaqCluData's per-segment long-code alignment.
constexpr size_t kSaqLongCodeAlignmentBytes = 16;

inline size_t roundUpCacheLine(size_t bytes) {
    return bytes == 0 ? 0 : ((bytes + kCacheLineBytes - 1) / kCacheLineBytes) * kCacheLineBytes;
}

inline double averageStridedAccessCacheLineBytes(
    size_t stride_bytes, size_t access_bytes, size_t field_offset_bytes = 0) {
    if (stride_bytes == 0 || access_bytes == 0 ||
        field_offset_bytes + access_bytes > stride_bytes) {
        return 0.0;
    }
    const size_t period = kCacheLineBytes / std::gcd(kCacheLineBytes, stride_bytes);
    double total = 0.0;
    for (size_t record = 0; record < period; ++record) {
        const size_t offset =
            (record * stride_bytes + field_offset_bytes) % kCacheLineBytes;
        const size_t lines =
            (offset + access_bytes + kCacheLineBytes - 1) / kCacheLineBytes;
        total += static_cast<double>(lines * kCacheLineBytes);
    }
    return total / static_cast<double>(period);
}

inline double averageRecordCacheLineBytes(size_t record_bytes) {
    return averageStridedAccessCacheLineBytes(record_bytes, record_bytes);
}

struct SymphonyQGWorkModel {
    size_t original_dimension = 0;
    size_t padded_dimension = 0;
    size_t degree = 0;

    size_t code_bytes_per_candidate = 0;
    size_t factor_bytes_per_candidate = 0;
    size_t graph_id_bytes_per_candidate = sizeof(PID);
    size_t query_lut_bytes = 0;
    size_t exact_current_vector_bytes_per_root = 0;

    size_t code_bytes_per_root() const { return degree * code_bytes_per_candidate; }
    size_t factor_bytes_per_root() const { return degree * factor_bytes_per_candidate; }
    size_t edge_index_bytes_per_node() const {
        return degree * (graph_id_bytes_per_candidate + code_bytes_per_candidate +
                         factor_bytes_per_candidate);
    }
    size_t cached_current_logical_read_bytes_per_root() const {
        return code_bytes_per_root() + factor_bytes_per_root() + query_lut_bytes;
    }
    size_t cold_current_logical_read_bytes_per_root() const {
        return cached_current_logical_read_bytes_per_root() +
               exact_current_vector_bytes_per_root;
    }
    size_t avx512_accumulation_iterations_per_root() const {
        return padded_dimension / 16;
    }
};

inline SymphonyQGWorkModel makeSymphonyQGWorkModel(
    size_t original_dimension, size_t padded_dimension, size_t degree) {
    if (original_dimension == 0 || padded_dimension < original_dimension ||
        !std::has_single_bit(padded_dimension) ||
        padded_dimension % 64 != 0 || degree == 0) {
        throw std::invalid_argument("invalid SymphonyQG work-model dimensions");
    }
    SymphonyQGWorkModel model;
    model.original_dimension = original_dimension;
    model.padded_dimension = padded_dimension;
    model.degree = degree;
    model.code_bytes_per_candidate = padded_dimension / 8;
    model.factor_bytes_per_candidate = 3 * sizeof(float);
    model.query_lut_bytes = padded_dimension * 4;
    model.exact_current_vector_bytes_per_root = original_dimension * sizeof(float);
    return model;
}

struct SaqStageWorkModel {
    size_t original_dimension = 0;
    size_t padded_dimension = 0;
    size_t degree = 0;
    size_t num_segments = 0;
    size_t positive_segments = 0;
    size_t accurate_prefix_segments = 0;

    size_t short_code_bytes_per_candidate = 0;
    size_t selected_long_code_bytes_per_candidate = 0;
    size_t full_long_code_payload_bytes_per_candidate = 0;
    size_t full_index_long_code_bytes_per_candidate = 0;
    size_t short_factor_storage_bytes_per_candidate = 0;
    size_t long_factor_storage_bytes_per_candidate = 0;
    size_t factor_value_bytes_read_per_candidate = 0;
    size_t accurate_query_bytes_read_per_candidate = 0;
    size_t graph_id_bytes_per_candidate = sizeof(PID);
    size_t locator_bytes_per_candidate = 2 * sizeof(PID);

    size_t short_code_bytes_per_block = 0;
    size_t factor_value_bytes_per_block = 0;
    size_t query_lut_bytes_read_per_block = 0;
    size_t query_state_bytes = 0;
    size_t cluster_prepare_input_bytes = 0;
    size_t cluster_prepare_query_state_write_bytes = 0;
    size_t cluster_prepare_lut_write_bytes = 0;

    double selected_long_code_cacheline_bytes_per_candidate = 0.0;
    double selected_long_factor_cacheline_bytes_per_candidate = 0.0;

    size_t stage_code_bytes_per_candidate() const {
        return short_code_bytes_per_candidate + selected_long_code_bytes_per_candidate;
    }
    size_t full_saq_payload_bytes_per_vector() const {
        return short_code_bytes_per_candidate + full_index_long_code_bytes_per_candidate +
               short_factor_storage_bytes_per_candidate +
               long_factor_storage_bytes_per_candidate + sizeof(PID);
    }
    size_t block_scan_logical_read_bytes() const {
        return short_code_bytes_per_block + factor_value_bytes_per_block +
               query_lut_bytes_read_per_block;
    }
    size_t accurate_logical_read_bytes_per_candidate() const {
        return selected_long_code_bytes_per_candidate +
               factor_value_bytes_read_per_candidate +
               accurate_query_bytes_read_per_candidate;
    }
    double accurate_cacheline_read_bytes_per_candidate() const {
        return selected_long_code_cacheline_bytes_per_candidate +
               selected_long_factor_cacheline_bytes_per_candidate +
               static_cast<double>(roundUpCacheLine(accurate_query_bytes_read_per_candidate));
    }
};

inline SaqStageWorkModel makeSaqStageWorkModel(
    size_t original_dimension, const SaqData::QuantPlanT &quant_plan,
    size_t degree, size_t accurate_prefix_segments) {
    if (original_dimension == 0 || quant_plan.empty() || degree == 0 ||
        accurate_prefix_segments > quant_plan.size()) {
        throw std::invalid_argument("invalid SAQ work-model configuration");
    }

    SaqStageWorkModel model;
    model.original_dimension = original_dimension;
    model.degree = degree;
    model.num_segments = quant_plan.size();
    model.accurate_prefix_segments = accurate_prefix_segments;

    for (size_t segment = 0; segment < quant_plan.size(); ++segment) {
        const auto [dimension, bits] = quant_plan[segment];
        if (dimension == 0 || dimension % kDimPaddingSize != 0) {
            throw std::invalid_argument("SAQ segment dimensions must be positive multiples of 64");
        }
        model.padded_dimension += dimension;
        model.short_factor_storage_bytes_per_candidate +=
            CAQClusterData::kNumShortFactors * sizeof(float);
        model.long_factor_storage_bytes_per_candidate += sizeof(ExFactor);
        model.factor_value_bytes_per_block += KFastScanSize * sizeof(float);

        if (bits > 0) {
            ++model.positive_segments;
            model.short_code_bytes_per_candidate += dimension / 8;
            const size_t long_bytes = dimension * (bits - 1) / 8;
            model.full_long_code_payload_bytes_per_candidate += long_bytes;
            model.full_index_long_code_bytes_per_candidate +=
                quant_plan.size() == 1
                    ? long_bytes
                    : ((long_bytes + kSaqLongCodeAlignmentBytes - 1) /
                       kSaqLongCodeAlignmentBytes) *
                          kSaqLongCodeAlignmentBytes;
            model.query_lut_bytes_read_per_block += 8 * dimension;
        }
        if (segment < accurate_prefix_segments && bits > 0) {
            const size_t long_bytes = dimension * (bits - 1) / 8;
            model.selected_long_code_bytes_per_candidate += long_bytes;
            model.factor_value_bytes_read_per_candidate += sizeof(float);
            model.accurate_query_bytes_read_per_candidate += dimension * sizeof(float);
            model.selected_long_code_cacheline_bytes_per_candidate +=
                averageRecordCacheLineBytes(long_bytes);
        }
    }

    model.short_code_bytes_per_block =
        model.short_code_bytes_per_candidate * KFastScanSize;
    // CaqCluEstimator retains the transformed query; Lut retains the residual
    // query and its 16-bit packed table.
    model.query_state_bytes =
        2 * model.padded_dimension * sizeof(float) +
        8 * model.padded_dimension;
    model.cluster_prepare_input_bytes =
        2 * model.padded_dimension * sizeof(float);
    model.cluster_prepare_query_state_write_bytes =
        model.padded_dimension * sizeof(float);
    model.cluster_prepare_lut_write_bytes = 8 * model.padded_dimension;

    if (model.factor_value_bytes_read_per_candidate > 0) {
        const size_t factor_record_bytes = model.num_segments * sizeof(ExFactor);
        model.selected_long_factor_cacheline_bytes_per_candidate =
            averageStridedAccessCacheLineBytes(
                factor_record_bytes, sizeof(float));
    }
    if (model.padded_dimension < original_dimension) {
        throw std::invalid_argument(
            "SAQ quantization plan does not cover the original dimension");
    }
    return model;
}

struct SaqTraceWork {
    size_t root_events = 0;
    size_t candidates = 0;
    size_t block_scan_calls = 0;
    size_t cluster_prepare_calls = 0;
};

struct SaqTraceBytes {
    size_t short_code = 0;
    size_t short_factor_values = 0;
    size_t query_lut = 0;
    size_t accurate_long_code = 0;
    size_t accurate_factor_values = 0;
    size_t accurate_query = 0;
    size_t cluster_prepare_inputs = 0;
    size_t cluster_prepare_query_state_writes = 0;
    size_t cluster_prepare_lut_writes = 0;

    size_t totalLogicalReads() const {
        return short_code + short_factor_values + query_lut +
               accurate_long_code + accurate_factor_values + accurate_query +
               cluster_prepare_inputs;
    }
};

inline SaqTraceBytes calculateSaqTraceBytes(
    const SaqStageWorkModel &model, const SaqTraceWork &trace) {
    SaqTraceBytes bytes;
    bytes.short_code = trace.block_scan_calls * model.short_code_bytes_per_block;
    bytes.short_factor_values =
        trace.block_scan_calls * model.factor_value_bytes_per_block;
    bytes.query_lut = trace.block_scan_calls * model.query_lut_bytes_read_per_block;
    bytes.accurate_long_code =
        trace.candidates * model.selected_long_code_bytes_per_candidate;
    bytes.accurate_factor_values =
        trace.candidates * model.factor_value_bytes_read_per_candidate;
    bytes.accurate_query =
        trace.candidates * model.accurate_query_bytes_read_per_candidate;
    bytes.cluster_prepare_inputs =
        trace.cluster_prepare_calls * model.cluster_prepare_input_bytes;
    bytes.cluster_prepare_query_state_writes =
        trace.cluster_prepare_calls *
        model.cluster_prepare_query_state_write_bytes;
    bytes.cluster_prepare_lut_writes =
        trace.cluster_prepare_calls * model.cluster_prepare_lut_write_bytes;
    return bytes;
}

} // namespace saqlib::analysis
