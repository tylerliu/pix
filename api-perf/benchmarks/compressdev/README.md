# DPDK Compression Device Benchmarks

This directory contains benchmarks for DPDK compression device APIs, following the same pattern as the cryptodev benchmarks.

## Overview

The compression device benchmarks measure the performance of key DPDK compression operations including:
- Private transform creation and cleanup
- Operation allocation and management
- Compression and decompression data path operations

## Benchmarks

### 1. `rte_compressdev_private_xform_create_free`
Measures the latency of creating and freeing private transforms for stateless compression operations.

### 2. `rte_comp_op_bulk_alloc_free`
Benchmarks bulk allocation and deallocation of compression operations with configurable batch sizes.

### 3. `rte_compressdev_enqueue_dequeue_burst_compress`
Benchmarks the full compression data path including enqueue, processing, and dequeue operations.

### 4. `rte_compressdev_enqueue_dequeue_burst_decompress`
Benchmarks the full decompression data path including enqueue, processing, and dequeue operations.

## Configuration

The benchmarks use **grouped parameters** to ensure only valid algorithm/checksum/huffman combinations are tested:

### Regular Parameters
- `burst_size`: Number of operations to process in a batch [1, 2, 8, 32]
- `data_size`: Size of data to compress/decompress [32, 128, 512, 2048] bytes
- `window_size`: Window size in bytes [1024, 2048, 4096, 8192, 16384, 32768]

### Grouped Parameters (algorithm_config)
The framework automatically tests all valid combinations:

**DEFLATE Algorithm:**
- `algorithm=deflate`, `checksum=none`, `huffman=fixed`
- `algorithm=deflate`, `checksum=none`, `huffman=dynamic`
- `algorithm=deflate`, `checksum=crc32`, `huffman=fixed`
- `algorithm=deflate`, `checksum=crc32`, `huffman=dynamic`
- `algorithm=deflate`, `checksum=adler32`, `huffman=fixed`
- `algorithm=deflate`, `checksum=adler32`, `huffman=dynamic`

**LZ4 Algorithm:**
- `algorithm=lz4`, `checksum=none`, `huffman=null`
- `algorithm=lz4`, `checksum=xxhash32`, `huffman=null`

**NULL Algorithm:**
- `algorithm=null`, `checksum=none`, `huffman=null`
- `algorithm=null`, `checksum=crc32`, `huffman=null`
- `algorithm=null`, `checksum=adler32`, `huffman=null`

## Supported Algorithms

### DEFLATE Algorithm
- **Huffman Types**: FIXED, DYNAMIC
- **Window Sizes**: 1KB, 2KB, 4KB, 8KB, 16KB, 32KB
- **Checksums**: CRC32, Adler32, Combined checksum
- **Shareable transformation**: Yes

### LZ4 Algorithm
- **Flags**: Block checksum, Block independence
- **Window Sizes**: 1KB, 2KB, 4KB, 8KB, 16KB, 32KB
- **Checksums**: xxHash-32 checksum
- **Shareable transformation**: Yes

### NULL Algorithm
- **Purpose**: DMA operations (memory-to-memory tasks)
- **Checksums**: CRC32, Adler32, Combined checksum
- **Shareable transformation**: Yes

## Hardware Limitations

### MLX5 Algorithm Support
Based on the [MLX5 compression driver documentation](https://doc.dpdk.org/guides/compressdevs/mlx5.html), the following limitations apply:

**BlueField-2:**
- ✅ DEFLATE algorithm supported
- ✅ NULL algorithm supported  
- ❌ LZ4 algorithm **not supported**
- ❌ Compress operation **not supported** (decompress only)

**BlueField-3:**
- ✅ DEFLATE algorithm supported
- ✅ LZ4 algorithm supported
- ✅ NULL algorithm supported
- ❌ Compress operation **not supported** (decompress only)

**General MLX5 Limitations:**
- ❌ Scatter-Gather operations not supported
- ❌ SHA operations not supported
- ❌ Stateful compression not supported
- ❌ Non-compressed block not supported in compress (supported in decompress)

### MLX5 Stateful API Support
**Important**: MLX5 compression devices do not support the stateful compression API. Therefore, the following functions are **not tested** in these benchmarks:

- `rte_compressdev_stream_create()`
- `rte_compressdev_stream_free()`
- Stateful compression operations

These benchmarks focus on **stateless compression** operations which are supported by MLX5 and most other compression devices.

## Usage

The benchmarks can be run using the standard benchmark framework:

```bash
# Run all compression device benchmarks (tests all valid algorithm/checksum/huffman combinations)
python run_benchmarks.py --template compressdev

# Run specific benchmark (automatically tests all valid combinations)
python run_benchmarks.py --template compressdev --benchmark rte_compressdev_enqueue_dequeue_burst_compress

# The framework will automatically test all valid combinations:
# - DEFLATE with all checksum/huffman combinations
# - LZ4 with xxHash-32 and no checksum
# - NULL with CRC32, Adler32, and no checksum
# - All burst sizes, data sizes, and window sizes
```

## EAL Arguments

The compressdev template uses the following EAL arguments:
```json
"compressdev": {
    "eal_args": ["-a", "03:00.0,class=compress"]
}
```

Adjust the PCI address (`03:00.0`) to match your compression device.

## Performance Metrics

The benchmarks measure:
- **Latency**: Cycles per operation
- **Throughput**: Operations per second
- **Polling overhead**: Time spent waiting for completion

Results include metadata about burst sizes and polling cycles for analysis.
