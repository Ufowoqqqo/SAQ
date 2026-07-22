#include "core.hpp"

#include <iostream>
#include <string>

int main() {
    std::string failure;
    double max_error = 0;
    std::size_t passed = 0, roundtrips = 0, lookups = 0, oracle_cleared = 0;
    if (!a4or::faiss_contract_smoke()) {
        std::cerr << "FAIL faiss contract smoke\n";
        return 1;
    }
    if (!a4or::run_tiny_exact(failure, max_error, passed, oracle_cleared)) {
        std::cerr << "FAIL " << failure << " after " << passed << " cases\n";
        return 2;
    }
    if (!a4or::run_representation_checks(failure, roundtrips, lookups)) {
        std::cerr << "FAIL " << failure << "\n";
        return 3;
    }
    const auto panel = a4or::synthetic_panel();
    if (panel.size() != 8192 * 128) {
        std::cerr << "FAIL synthetic shape\n";
        return 4;
    }
    std::cout << "PASS tiny_total=" << passed
              << " max_objective_error=" << max_error
              << " oracle_cleared=" << oracle_cleared
              << " roundtrips=" << roundtrips
              << " lookups=" << lookups << '\n';
    return 0;
}
