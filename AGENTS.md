# AGENTS.md

Durable guidance for future Codex sessions working in this repository.

## Repo Layout

- `saqlib/`: header-heavy SAQ/CAQ implementation, quantizers, estimators, IVF index helpers, utilities, and fast scan code.
- `src/`: C++ command-line binaries such as `create_index`, `test_qps`, `test_relative_error`, `compare_search_results`, attribution tools, and diagnostics.
- `unit_test/`: GoogleTest unit tests built as `bin/unit_tests`.
- `script/`: Python and shell experiment drivers, diagnostics, planner sweeps, and report-generation helpers.
- `python/`: dataset download/preprocess, PCA, IVF, and groundtruth utility scripts.
- `data/`: dataset directories. Generated dataset subdirectories are ignored by git.
- `docs/`: experiment notes, audits, synthesis reports, and meeting-facing project documentation.
- `results/`: figures/notebooks and generated result directories. Generated SAQ/LLM result subdirectories are ignored by git.
- `bin/`: CMake runtime output directory for built binaries. Ignored by git.

## Setup, Build, Test, Lint

Prerequisites:

```bash
apt install libfmt-dev libgoogle-glog-dev libgflags-dev libgtest-dev
```

AVX512 is required. CMake fails intentionally if AVX512 support is unavailable.

Build:

```bash
mkdir -p build bin
cd build
cmake ..
make -j
```

Equivalent out-of-tree form from repo root:

```bash
cmake -S . -B build
cmake --build build -j
```

Build without unit tests:

```bash
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Run unit tests:

```bash
cd build
ctest --output-on-failure
```

or:

```bash
./bin/unit_tests
```

Python syntax check for experiment drivers:

```bash
python -m py_compile script/*.py python/*.py python/utils/*.py
```

Main binaries:

```bash
./bin/create_index -dataset gist -K 4096 -B 4
./bin/test_relative_error -dataset gist -K 4096 -B 4
./bin/test_qps -dataset gist -K 4096 -B 4
./bin/test_ivf -dataset gist -K 4096 -B 4
```

Dataset preparation:

```bash
python ./python/ivf.py <dataset> <K>
python ./python/pca.py <dataset>
```

For datasets without bundled groundtruth, use the Python or C++ groundtruth
tools:

```bash
python ./python/compute_gt.py <dataset>
./bin/compute_gt -dataset <dataset>
```

## Coding Conventions

- C++ standard is C++20.
- Runtime binaries are written to `bin/`.
- Follow `.clang-format`: LLVM base style, 4-space indentation, no column limit.
- `.clang-tidy` enables modernize, bugprone, clang-analyzer, and concurrency checks, with selected modernize exceptions.
- Keep C++ changes compatible with AVX512 compile flags in the top-level `CMakeLists.txt`.
- Keep experiment scripts deterministic where practical; expose parameters as flags instead of hard-coding one-off values.
- Put durable experiment writeups in `docs/`; do not rely on local `/tmp` artifacts as the only record.

## Verification Checklist

Before committing code changes:

```bash
cmake --build build -j
ctest --test-dir build --output-on-failure
python -m py_compile script/*.py python/*.py python/utils/*.py
git diff --check
```

For measured recall/QPS claims involving multi-segment search, use the corrected
safe searcher:

```text
-searcher_safe_block_min_mode=2
```

For planner or custom segment-plan changes, verify at least:

- index builds successfully with `create_index`;
- recall is measured with `compare_search_results` or the relevant evaluation driver;
- QPS is measured with `test_qps` when making speed claims;
- generated reports include exact dataset, `K`, `B`, PCA setting, top-k/recall metric, nprobe values, searcher mode, and artifact paths.

## Recurring Constraints And Do-Not Rules

- Keep this follow-up direction query-unaware unless the user explicitly changes the research direction.
- Do not promote an offline planner result as a real improvement until it has been validated with measured safe-searcher recall and, when relevant, QPS.
- Do not use native multi-segment search measurements for final claims when the safe-searcher mode is available.
- Do not commit generated datasets, built binaries, `build/`, `bin/`, or generated result directories ignored by `.gitignore`.
- Do not rewrite unrelated experiment history or revert user changes while working in this branch.
- Do not assume bundled groundtruth exists for every dataset; check `data/<dataset>/` and generate groundtruth when needed.

## Known Pitfalls

- AVX512 is mandatory; builds on machines without AVX512 support are expected to fail.
- Dataset directories must contain the raw vectors, query vectors, groundtruth, IVF centroids/cluster ids, and PCA artifacts expected by the binaries.
- SAQ index building assumes PCA/IVF preprocessing has already been run for the dataset and `K`.
- Generated local artifacts under `/tmp` or ignored `data/*/` and `results/saq/` paths are useful for experiments but are not durable repository state.
- Planner rankings are proxies. Prior work in this repository found that low offline recall-risk can still be a measured false positive, so always validate candidate plans end to end.
