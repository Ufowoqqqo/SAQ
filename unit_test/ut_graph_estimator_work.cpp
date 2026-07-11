#include <vector>

#include <gtest/gtest.h>

#include "analysis/graph_estimator_work.hpp"

using namespace saqlib;

TEST(GraphEstimatorWorkTest, SymphonyQGGistDegree32Accounting) {
    const auto model = analysis::makeSymphonyQGWorkModel(960, 1024, 32);

    EXPECT_EQ(model.code_bytes_per_candidate, 128);
    EXPECT_EQ(model.factor_bytes_per_candidate, 12);
    EXPECT_EQ(model.query_lut_bytes, 4096);
    EXPECT_EQ(model.code_bytes_per_root(), 4096);
    EXPECT_EQ(model.factor_bytes_per_root(), 384);
    EXPECT_EQ(model.edge_index_bytes_per_node(), 4608);
    EXPECT_EQ(model.cached_current_logical_read_bytes_per_root(), 8576);
    EXPECT_EQ(model.cold_current_logical_read_bytes_per_root(), 12416);
    EXPECT_EQ(model.avx512_accumulation_iterations_per_root(), 64);
}

TEST(GraphEstimatorWorkTest, SaqGistFastAndFirstPrefixAccounting) {
    const SaqData::QuantPlanT plan = {
        {64, 11}, {192, 6}, {320, 4}, {256, 2}, {128, 0}};
    const auto fast = analysis::makeSaqStageWorkModel(960, plan, 32, 0);
    const auto prefix1 = analysis::makeSaqStageWorkModel(960, plan, 32, 1);

    EXPECT_EQ(fast.padded_dimension, 960);
    EXPECT_EQ(fast.num_segments, 5);
    EXPECT_EQ(fast.positive_segments, 4);
    EXPECT_EQ(fast.short_code_bytes_per_candidate, 104);
    EXPECT_EQ(fast.full_long_code_payload_bytes_per_candidate, 352);
    EXPECT_EQ(fast.full_index_long_code_bytes_per_candidate, 368);
    EXPECT_EQ(fast.short_factor_storage_bytes_per_candidate, 40);
    EXPECT_EQ(fast.long_factor_storage_bytes_per_candidate, 40);
    EXPECT_EQ(fast.full_saq_payload_bytes_per_vector(), 556);
    EXPECT_EQ(fast.short_code_bytes_per_block, 3328);
    EXPECT_EQ(fast.factor_value_bytes_per_block, 640);
    EXPECT_EQ(fast.query_lut_bytes_read_per_block, 6656);
    EXPECT_EQ(fast.block_scan_logical_read_bytes(), 10624);
    EXPECT_EQ(fast.query_state_bytes, 15360);
    EXPECT_EQ(fast.cluster_prepare_input_bytes, 7680);
    EXPECT_EQ(fast.cluster_prepare_query_state_write_bytes, 3840);
    EXPECT_EQ(fast.cluster_prepare_lut_write_bytes, 7680);

    EXPECT_EQ(prefix1.stage_code_bytes_per_candidate(), 184);
    EXPECT_EQ(prefix1.selected_long_code_bytes_per_candidate, 80);
    EXPECT_EQ(prefix1.factor_value_bytes_read_per_candidate, 4);
    EXPECT_EQ(prefix1.accurate_query_bytes_read_per_candidate, 256);
    EXPECT_EQ(prefix1.accurate_logical_read_bytes_per_candidate(), 340);
    EXPECT_DOUBLE_EQ(
        prefix1.selected_long_code_cacheline_bytes_per_candidate, 128.0);
    EXPECT_DOUBLE_EQ(
        prefix1.selected_long_factor_cacheline_bytes_per_candidate, 64.0);
    EXPECT_DOUBLE_EQ(prefix1.accurate_cacheline_read_bytes_per_candidate(), 448.0);
}

TEST(GraphEstimatorWorkTest, TraceAccountingSeparatesBlockAndPrepareWork) {
    const SaqData::QuantPlanT plan = {
        {64, 11}, {192, 6}, {320, 4}, {256, 2}, {128, 0}};
    const auto prefix1 = analysis::makeSaqStageWorkModel(960, plan, 32, 1);
    const analysis::SaqTraceWork trace{
        .root_events = 1,
        .candidates = 32,
        .block_scan_calls = 10,
        .cluster_prepare_calls = 5,
    };
    const auto bytes = analysis::calculateSaqTraceBytes(prefix1, trace);

    EXPECT_EQ(bytes.short_code, 33280);
    EXPECT_EQ(bytes.short_factor_values, 6400);
    EXPECT_EQ(bytes.query_lut, 66560);
    EXPECT_EQ(bytes.accurate_long_code, 2560);
    EXPECT_EQ(bytes.accurate_factor_values, 128);
    EXPECT_EQ(bytes.accurate_query, 8192);
    EXPECT_EQ(bytes.cluster_prepare_inputs, 38400);
    EXPECT_EQ(bytes.cluster_prepare_query_state_writes, 19200);
    EXPECT_EQ(bytes.cluster_prepare_lut_writes, 38400);
    EXPECT_EQ(bytes.totalLogicalReads(), 155520);
}

TEST(GraphEstimatorWorkTest, RejectsInvalidConfigurations) {
    EXPECT_THROW(
        analysis::makeSymphonyQGWorkModel(960, 960, 32),
        std::invalid_argument);
    EXPECT_THROW(
        analysis::makeSaqStageWorkModel(960, {}, 32, 0),
        std::invalid_argument);
    EXPECT_THROW(
        analysis::makeSaqStageWorkModel(128, {{64, 4}}, 32, 0),
        std::invalid_argument);
}
