#include "native_cli.hpp"
#include "numeric_runtime.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace saq::a4_v2::producer {
namespace {

[[nodiscard]] int Run(int argc, char** argv) {
  const NumericManifest initial = InitializeNumericRuntime();
  if (argc < 2) {
    throw std::invalid_argument(
        "usage: a4_v2_native manifest | native-smoke OUT | scalar-suite IN OUT | "
        "par-scalar IN OUT | par-block IN OUT | "
        "block-suite IN OUT | representation-suite | allocation-suite IN OUT | "
        "allocation-item IN OUT | encoding-suite IN OUT");
  }
  const std::string command(argv[1]);
  if (command == "manifest") {
    if (argc != 2) throw std::invalid_argument("manifest accepts no arguments");
    std::cout << NumericManifestJson(initial, CaptureNumericRuntime()) << '\n';
  } else if (command == "native-smoke") {
    if (argc != 3) throw std::invalid_argument("native-smoke requires OUT");
    WriteNativeSmoke(argv[2]);
  } else if (command == "scalar-suite") {
    if (argc != 4) throw std::invalid_argument("scalar-suite requires IN OUT");
    WriteScalarSuite(argv[2], argv[3]);
  } else if (command == "par-scalar") {
    if (argc != 4) throw std::invalid_argument("par-scalar requires IN OUT");
    WriteScalarParitySuite(argv[2], argv[3]);
  } else if (command == "block-suite") {
    if (argc != 4) throw std::invalid_argument("block-suite requires IN OUT");
    WriteBlockSuite(argv[2], argv[3]);
  } else if (command == "par-block") {
    if (argc != 4) throw std::invalid_argument("par-block requires IN OUT");
    WriteBlockParitySuite(argv[2], argv[3]);
  } else if (command == "representation-suite") {
    if (argc != 2) throw std::invalid_argument("representation-suite takes no arguments");
    WriteRepresentationSuite(std::cout);
  } else if (command == "allocation-suite") {
    if (argc != 4) throw std::invalid_argument("allocation-suite requires IN OUT");
    WriteAllocationSuite(argv[2], argv[3]);
  } else if (command == "allocation-item") {
    if (argc != 4) throw std::invalid_argument("allocation-item requires IN OUT");
    WriteAllocationItem(argv[2], argv[3]);
  } else if (command == "encoding-suite") {
    if (argc != 4) throw std::invalid_argument("encoding-suite requires IN OUT");
    WriteEncodingSuite(argv[2], argv[3]);
  } else {
    throw std::invalid_argument("unknown A4-V2 native command");
  }
  VerifyNumericRuntime();
  return 0;
}

}  // namespace
}  // namespace saq::a4_v2::producer

int main(int argc, char** argv) {
  try {
    return saq::a4_v2::producer::Run(argc, argv);
  } catch (const std::exception& error) {
    std::cerr << "A4-V2 IMPLEMENTATION_INVALID: " << error.what() << '\n';
    return 2;
  }
}
