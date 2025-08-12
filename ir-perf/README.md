# IR-Perf: LLVM IR Instruction Performance Benchmarking Tool

IR-Perf is a comprehensive benchmarking framework designed to measure the performance characteristics of individual LLVM IR instructions and small instruction sequences. It provides precise cycle-level measurements with proper CPU isolation and supports both traditional CPU-based profiling and NVIDIA BlueField/ConnectX DPA (Data Processing Accelerator) telemetry.

## Features

- **Comprehensive IR Coverage**: Benchmarks all major LLVM IR instruction types including arithmetic, memory, pointer, floating-point, conversion, branching, call, and allocation operations
- **Precise Measurements**: Uses CPU isolation and overhead subtraction for accurate cycle-level performance data
- **Multiple Backends**: Supports both CPU (perf-based) and DPA (DOCA Telemetry) measurement backends
- **Automated Workflow**: Automatically generates benchmarks from IR snippets, compiles them, and runs measurements
- **Memory Latency Analysis**: Includes sophisticated memory latency analysis for cache hierarchy characterization
- **Template System**: Flexible template system for different instruction categories with customizable measurement loops
- **Statistical Analysis**: Provides detailed statistical analysis including mean, median, percentiles, and confidence intervals

## Project Structure

```
ir-perf/
├── CMakeLists.txt              # Main build configuration
├── run_benchmarks.py           # Main benchmarking script
├── dpa_runner.py              # DPA telemetry integration
├── analyze_memory_latency.py  # Memory latency analysis
├── generate_load_benchmarks.py # Load benchmark generation
├── generate_load_latency_ir.py # Load latency IR generation
├── bench-driver.c             # C driver for benchmarks
├── operators.txt              # LLVM IR operator reference
├── templates/                 # Benchmark templates by category
│   ├── arithmetic.ll         # Arithmetic operations
│   ├── memory.ll            # Memory operations
│   ├── pointer.ll           # Pointer operations
│   ├── fp-arithmetic.ll     # Floating-point arithmetic
│   ├── conversion.ll        # Type conversions
│   ├── branching.ll         # Control flow
│   ├── call.ll              # Function calls
│   └── alloca.ll            # Stack allocation
├── snippets/                 # IR instruction snippets
│   ├── arithmetic/          # Arithmetic instruction benchmarks
│   ├── memory/              # Memory instruction benchmarks
│   ├── pointer/             # Pointer instruction benchmarks
│   ├── fp-arithmetic/       # Floating-point benchmarks
│   ├── conversion/          # Type conversion benchmarks
│   ├── branching/           # Control flow benchmarks
│   ├── call/                # Function call benchmarks
│   └── alloca/              # Stack allocation benchmarks
└── cmake/                   # CMake helper scripts
    └── find_bitcode_compiler.cmake
```

## Prerequisites

### For CPU Backend
- Linux kernel with perf support
- LLVM/Clang toolchain (llc, clang, clang++)
- Python 3.6+
- cpupower utility
- Root privileges for CPU frequency control

### For DPA Backend
- NVIDIA BlueField or ConnectX device
- DOCA SDK with Telemetry DPA support
- fwctl driver loaded (`/sys/class/fwctl` should exist)
- libdoca_telemetry_dpa.so library

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pix/ir-perf
   ```

2. **Ensure LLVM toolchain is available**:
   ```bash
   # Verify LLVM tools are in PATH
   which llc clang clang++
   ```

3. **Build the project**:
   ```bash
   mkdir build && cd build
   cmake ..
   make -j$(nproc)
   ```

4. **Verify installation**:
   ```bash
   # Check that benchmarks were generated
   ls bench_*
   ```

## Usage

### Basic Benchmarking

Run all benchmarks with default settings:
```bash
cd build
python3 ../run_benchmarks.py
```

Run specific benchmarks:
```bash
python3 ../run_benchmarks.py bench_arithmetic_add-imm bench_memory_load
```

### CPU Backend Options

```bash
# Run with custom CPU core and iterations
python3 ../run_benchmarks.py --cpu-core 2 --iterations 50000000

# Enable verbose output
python3 ../run_benchmarks.py --verbose

# Disable memory latency analysis
python3 ../run_benchmarks.py --no-analyze-latency
```

### DPA Backend Usage

Run benchmarks using DPA telemetry:
```bash
python3 ../run_benchmarks.py --backend dpa
```

DPA-specific options:
```bash
# Specify DPA device
python3 ../run_benchmarks.py --backend dpa --dpa-device pci=0000:06:00.0

# Custom sampling interval
python3 ../run_benchmarks.py --backend dpa --dpa-sample-ms 500

# Thread filtering
python3 ../run_benchmarks.py --backend dpa --dpa-thread-filter "bench_.*"
```

### Complete DPA Example

```bash
# Run arithmetic benchmarks with DPA telemetry
python3 ../run_benchmarks.py \
  --backend dpa \
  --dpa-device pci=0000:06:00.0 \
  --dpa-sample-ms 1000 \
  --verbose \
  bench_arithmetic_add-imm bench_arithmetic_mul-imm
```

## Benchmark Categories

### Arithmetic Operations
- Integer arithmetic: `add`, `sub`, `mul`, `div`, `rem`
- Bitwise operations: `and`, `or`, `xor`, `shl`, `lshr`, `ashr`
- Examples: `bench_arithmetic_add-imm`, `bench_arithmetic_mul-imm`

### Memory Operations
- Load/store operations: `load`, `store`
- Memory allocation: `alloca`
- Pointer arithmetic: `getelementptr`
- Examples: `bench_memory_load`, `bench_memory_store-32KB-4`

### Floating-Point Operations
- FP arithmetic: `fadd`, `fsub`, `fmul`, `fdiv`, `frem`
- FP comparisons: `fcmp`
- Examples: `bench_fp-arithmetic_fadd`, `bench_fp-arithmetic_fmul`

### Type Conversions
- Integer conversions: `trunc`, `zext`, `sext`
- FP conversions: `fptrunc`, `fpext`, `fptoui`, `fptosi`
- Pointer conversions: `inttoptr`, `ptrtoint`, `bitcast`
- Examples: `bench_conversion_trunc`, `bench_conversion_zext`

### Control Flow
- Conditional branches: `br`, `switch`
- Phi nodes: `phi`
- Function calls: `call`
- Examples: `bench_branching_br`, `bench_call_call-simple`

## Output and Analysis

### CPU Backend Output
The CPU backend provides detailed performance metrics:
- Cycle counts per iteration
- Statistical analysis (mean, median, percentiles)
- Cache miss analysis
- Memory latency characterization

### DPA Backend Output
The DPA backend provides:
- Instruction and cycle telemetry from hardware
- Per-thread performance data
- Hardware-level performance counters

### Memory Latency Analysis
When enabled, the tool performs comprehensive memory latency analysis:
- Cache hierarchy characterization
- Memory bandwidth measurements
- Latency vs. working set size analysis

## Adding New Benchmarks

### 1. Create IR Snippet
Create a new `.ll` file in the appropriate `snippets/<category>/` directory:

```llvm
; snippets/arithmetic/my-new-op.ll
%result = add i64 %op1, %op2
```

### 2. Rebuild
```bash
cd build
make
```

### 3. Run
```bash
python3 ../run_benchmarks.py bench_arithmetic_my-new-op
```

### Adding New Template Types

1. Create template file in `templates/`:
```llvm
; templates/my-template.ll
define void @bench_loop(i64 %N) {
entry:
  br label %loop
loop:
  %i = phi i64 [0, %entry], [%next_i, %loop]
  %next_i = add i64 %i, 1
  %cond = icmp ult i64 %next_i, %N
  br i1 %cond, label %loop, label %exit
  ; INSERT_SNIPPET_HERE
exit:
  ret void
}
```

2. Update `CMakeLists.txt`:
```cmake
set(TEMPLATE_TYPES arithmetic memory pointer fp-arithmetic conversion branching call alloca my-template)
```

3. Update `generate_bench_ll.py` to include the new template type.

## Troubleshooting

### Common Issues

**Permission Denied for CPU Control**:
```bash
# Run with sudo for CPU frequency control
sudo python3 ../run_benchmarks.py
```

**LLVM Tools Not Found**:
```bash
# Ensure LLVM is in PATH
export PATH=/path/to/llvm/bin:$PATH
```

**DPA Backend Not Available**:
```bash
# Check DOCA installation
ls /opt/mellanox/doca/lib/libdoca_telemetry_dpa.so
# Check fwctl driver
ls /sys/class/fwctl
```

**Build Failures**:
```bash
# Clean and rebuild
cd build
make clean
cmake ..
make
```

### Performance Tips

1. **CPU Isolation**: Use isolated CPU cores for consistent measurements
2. **Frequency Scaling**: Disable CPU frequency scaling during measurements
3. **Cache Warming**: Run benchmarks multiple times to warm up caches
4. **Background Processes**: Minimize background processes during measurements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your benchmarks or improvements
4. Test thoroughly with both CPU and DPA backends
5. Submit a pull request

## License

This project is licensed under the same license as the parent repository.

## References

- [LLVM IR Reference](https://llvm.org/docs/LangRef.html)
- [DOCA Telemetry DPA Documentation](https://docs.nvidia.com/doca/)
- [Linux perf Documentation](https://perf.wiki.kernel.org/)
