# IR Microbenchmark Tool

This tool is designed to measure the performance of individual LLVM IR instructions or small instruction sequences. It automates the process of benchmarking IR code snippets by integrating them into appropriate loop templates, compiling them, and running them via a C driver.

## Features
- Benchmarks non-memory LLVM IR instructions
- Supports multiple template types (arithmetic, memory, phi)
- Automates snippet insertion, compilation, and executable generation
- Easy to add new instruction benchmarks and template types
- Generates a separate executable for each snippet

## How It Works
1. **Snippets:** Place your LLVM IR instruction(s) in a file in the appropriate `snippets/<category>/` directory (one snippet per file).
2. **Templates:** Each snippet is inserted into a loop in the appropriate template from `templates/` at a marked location.
3. **Build:** CMake automatically generates a new `.ll` file for each snippet, compiles it to an object file, and links it with a C driver (`bench-driver.c`) to create an executable.
4. **Run:** Each executable runs the loop with your instruction(s) and prevents dead-code elimination by calling an external `sink` function.

## Directory Structure
```
pix/ir-perf/
├── templates/           # Different benchmark templates
│   ├── arithmetic.ll   # For add, sub, mul, etc.
│   ├── memory.ll       # For load/store instructions
│   └── phi.ll          # For phi node operations
├── snippets/           # Instruction snippets (organized by type)
│   ├── arithmetic/     # Arithmetic operations
│   ├── memory/         # Memory operations
│   └── phi/            # Phi node operations
├── cmake/              # CMake helper scripts
├── bench-driver.c      # C driver
├── generate_bench_ll.py # Python script for snippet insertion
└── CMakeLists.txt      # Build configuration
```

## Installation & Build
1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd <repo-directory>/pix/ir-perf
   ```
2. Ensure you have LLVM tools (llc, clang, etc.) available and configured in `cmake/find_bitcode_compiler.cmake`.
3. Build with CMake:
   ```bash
   mkdir build && cd build
   cmake ..
   make
   ```
   This will generate one executable per snippet, organized by template type (e.g., `bench_arithmetic_add-imm` for `snippets/arithmetic/add-imm.ll`).

## Usage
Run the generated benchmark executable(s):
```bash
./bench_arithmetic_add-imm 100000000
./bench_memory_load 100000000
./bench_phi_phi-simple 100000000
```
- The argument is the number of loop iterations (default is 100,000,000 if not specified).

## Input/Output
- **Input:** LLVM IR snippet files organized by category (see `snippets/` for examples)
- **Output:**
  - One executable per snippet, named after the template type and snippet file
  - Console output as defined in `bench-driver.c` (typically none; use external timing tools to measure performance)

## Adding New Benchmarks

### Adding New Snippets
1. Create a new `.ll` file in the appropriate `snippets/<category>/` directory containing the IR instruction(s) you want to benchmark.
2. Re-run the build (`make`).
3. A new executable will be generated for your snippet.

### Adding New Template Types
1. Create a new template file in `templates/` (e.g., `templates/control.ll`).
2. Add the template type to the `TEMPLATE_TYPES` list in `CMakeLists.txt`.
3. Update `generate_bench_ll.py` to include the new template type in the `template_configs` dictionary.
4. Create a corresponding `snippets/<new-type>/` directory.

## Template Types

### Arithmetic Template (`templates/arithmetic.ll`)
- Designed for arithmetic operations: add, sub, mul, div, etc.
- Uses simple loop with accumulator pattern
- Snippets: `snippets/arithmetic/`

### Memory Template (`templates/memory.ll`)
- Designed for memory operations: load, store, getelementptr, etc.
- Includes memory allocation and pointer operations
- Snippets: `snippets/memory/`

### Phi Template (`templates/phi.ll`)
- Designed for phi node operations
- Includes multiple basic blocks to demonstrate phi behavior
- Snippets: `snippets/phi/`

## Configuration
- Edit template files in `templates/` to change the loop structure or measurement region for each category.
- Edit `bench-driver.c` to change how the benchmark is invoked or how results are handled.
- CMake scripts handle snippet discovery and build automation.

## Example Snippets

### Arithmetic (`snippets/arithmetic/add-imm.ll`)
```llvm
%next_op1 = add i64 %op1, 42
```

### Memory (`snippets/memory/load.ll`)
```llvm
%val = load i64, i64* %ptr
%next_sum = add i64 %sum, %val
```

### Phi (`snippets/phi/phi-simple.ll`)
```llvm
%next_val = phi i64 [%val, %loop], [42, %entry]
```