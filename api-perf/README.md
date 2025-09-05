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

# Performance Analysis

The project includes a comprehensive latency analysis script that processes benchmark results and generates performance models.

## Analysis Script

Use `analyze_latency.py` to analyze CSV results from benchmark runs:

```bash
python3 analyze_latency.py [--csv-dir .] [--output function_latency_map.json] [--polling-output polling_analysis.json] [--correlations correlations.json]
```

## Output Files

The analysis generates three complementary JSON files:

### 1. `function_latency_map.json` - Performance Model
Clean mapping of each function to its base latency and significant parameter coefficients:

```json
{
  "rte_eth_rx_burst": {
    "base_latency_cycles": 15.2,
    "parameters": {
      "burst_size": 2.45,
      "packets_received": -0.0001
    }
  }
}
```

**Interpretation:**
- `base_latency_cycles`: Base latency when all parameters are at their reference values
- `parameters`: How much latency changes per unit change in each parameter
- Only statistically significant parameters (p < 0.05) are included

### 2. `correlations.json` - Statistical Analysis
Complete statistical analysis for all parameters:

```json
{
  "rte_eth_rx_burst": {
    "burst_size": {
      "coefficient": 2.45,
      "intercept": 10.1,
      "correlation": 0.89,
      "p_value": 0.001,
      "significant": true,
      "n_samples": 9
    }
  }
}
```

**Fields:**
- `coefficient`: Linear regression slope (cycles per unit parameter change)
- `intercept`: Y-intercept from individual regression
- `correlation`: Pearson correlation coefficient (-1 to 1)
- `p_value`: Statistical significance (p < 0.05 is significant)
- `significant`: Boolean indicating statistical significance
- `n_samples`: Number of data points used

### 3. `polling_analysis.json` - Polling Overhead
Analysis of polling/wait time for functions that use it, with regression coefficients and correlation analysis:

```json
{
  "rte_cryptodev_enqueue_wait_dequeue_burst_encrypt": {
    "base_poll_cycles_per_iteration": 1200.45,
    "parameters": {
      "burst_size": 12.5
    },
    "correlations": {
      "burst_size": {
        "coefficient": 12.5,
        "intercept": 1200.45,
        "correlation": 0.89,
        "p_value": 0.001,
        "significant": true,
        "n_samples": 16
      }
    },
    "std_poll_cycles_per_iteration": 145.83,
    "n_measurements": 16
  }
}
```

**Interpretation:**
- `base_poll_cycles_per_iteration`: Base polling time when parameters are at reference values
- `parameters`: How much polling time changes per unit change in each parameter (significant only)
- `correlations`: Complete statistical analysis for all parameters (significant and non-significant)
- Only statistically significant parameters (p < 0.05) are included in `parameters`
- Additional statistics show the distribution of polling times

## Analysis Methodology

The analysis uses a two-step approach:

1. **Individual Significance Testing**: Tests each parameter individually using linear regression to determine statistical significance (p < 0.05)

2. **Multivariate Linear Regression**: Performs multivariate linear regression using only the significant parameters to get accurate coefficients that account for parameter interactions

## Benchmark Types

### Standard Benchmarks (`dpdk`, `cryptodev`)
- Measure actual function performance
- Include metadata about operation parameters (burst_size, data_size, etc.)
- Results show per-operation latency

### Wait-Based Benchmarks (`cryptodev-wait`)
- Use polling loops instead of fixed wait times
- Measure actual crypto work time, excluding polling overhead
- Include polling time analysis in separate file
- More realistic performance measurement

### Data Filtering
- Automatically filters out invalid measurements (e.g., rx_burst with 0 packets when network traffic is expected)
- Preserves baseline measurements (e.g., rx_burst with 0 packets when no network traffic is configured)
