#pragma once

#include <iosfwd>
#include <string>

namespace saq::a4_v2::producer {

void WriteNativeSmoke(const std::string& output_path);
void WriteScalarSuite(const std::string& input_path,
                      const std::string& output_path);
void WriteScalarParitySuite(const std::string& input_path,
                            const std::string& output_path);
void WriteBlockSuite(const std::string& input_path,
                     const std::string& output_path);
void WriteBlockParitySuite(const std::string& input_path,
                           const std::string& output_path);
void WriteRepresentationSuite(std::ostream& output);
void WriteAllocationSuite(const std::string& input_path,
                          const std::string& output_path);
void WriteAllocationItem(const std::string& input_path,
                         const std::string& output_path);
void WriteEncodingSuite(const std::string& input_path,
                        const std::string& output_path);

}  // namespace saq::a4_v2::producer
