# Project Overview

This project is a C-based performance benchmarking suite for DPDK (Data Plane Development Kit) APIs. It uses the Meson build system to compile the C code and Python scripts to automate the generation and execution of benchmarks.

The primary goal of this project is to measure the performance of individual DPDK functions in a controlled environment. It achieves this by dynamically generating C source files for each function to be benchmarked, compiling them, and then running them to collect performance data.

## Key Technologies

*   **C:** The core benchmarking logic is written in C.
*   **DPDK:** The Data Plane Development Kit is used for high-performance packet processing.
*   **Meson:** The project is built using the Meson build system.
*   **Python:** Python scripts are used to automate the benchmark generation and execution process.

## Architecture

The project is structured into three main components:

1.  **Benchmark Driver:** The `driver` directory contains the `benchmark_driver.c` and `benchmark_driver.h` files, which are responsible for initializing and cleaning up the DPDK environment.
2.  **Benchmark Templates and Snippets:** The `benchmarks/dpdk` directory contains a `template.c` file that serves as a template for generating the benchmark source code. It also contains subdirectories for each function to be benchmarked, with `call.c`, `setup.c`, and `headers.c` snippets that are injected into the template.
3.  **Automation Scripts:**
    *   `generate_benchmark.py`: This script generates the C source code for a given benchmark function by combining the template with the corresponding snippets.
    *   `run_benchmarks.py`: This script runs prebuilt benchmarks and passes per-type options, with helpful diagnostics for common issues.

# Building

Use Meson/Ninja to build the executables once. Generation is handled in `meson.build`.

```bash
meson setup build
ninja -C build
```

This produces executables in `build/` named like `dpdk_<function>` (e.g., `dpdk_rte_eth_rx_burst`).

# Running

Use `run_benchmarks.py` to run the prebuilt binaries and pass per-type arguments cleanly.

Basic usage:

```bash
python3 run_benchmarks.py [--type dpdk|doca|cryptodev|custom] [--build-dir build] [--prefix <prefix>] \
  <function> [<function> ...] -- <args passed to executable>
```

Examples:

```bash
# DPDK: bind auxiliary SF and run rx burst
python3 run_benchmarks.py --type dpdk rte_eth_rx_burst -- -l 1 -n 4 -a auxiliary:mlx5_core.sf.4

# DPDK: run tx burst on a null vdev
python3 run_benchmarks.py --type dpdk rte_eth_tx_burst -- -l 1 -n 4 --vdev=eth_null0

# DOCA (example): pass device-specific args
python3 run_benchmarks.py --type doca some_doca_func -- --dev pci:03:00.0 --queue 0
```

Notes:

- Arguments after `--` are passed verbatim to the executable.
- If you see permission or hugepage errors, the script prints hints. Ensure hugepages are configured for your platform before running DPDK.
- If not running as root for `--type dpdk`/`cryptodev`, the script prints a warning but does not elevate privileges.

# Development Conventions

*   **Adding New Benchmarks:** To add a new benchmark for a DPDK function, create a new subdirectory in `benchmarks/dpdk` with the same name as the function. Inside this directory, create the following files:
    *   `call.c`: This file should contain the C code that calls the function to be benchmarked.
    *   `setup.c` (optional): This file can contain any setup code that needs to be run before the benchmark loop.
    *   `headers.c` (optional): This file can contain any additional headers that need to be included in the generated C source file.
    *   `teardown.c` (optional): This file can contain any teardown code that needs to be run after the benchmark loop.
*   **Code Style:** The C code follows a consistent style, which should be maintained when adding new code.
