#!/usr/bin/env python3
"""
Simple script to generate compressed test data for decompression benchmarks.
Uses standard tools (gzip, lz4) to create compressed data files.
"""

import os
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path

def create_test_data(size_bytes, data_type="random"):
    """Create test data of specified size."""
    if data_type == "random":
        # Generate random data
        return os.urandom(size_bytes)
    elif data_type == "text":
        # Generate repetitive text data (good for compression)
        pattern = "This is test data for compression benchmarking. " * 100
        return (pattern * (size_bytes // len(pattern) + 1))[:size_bytes].encode()
    elif data_type == "zeros":
        # Generate zero-filled data
        return b'\x00' * size_bytes
    else:
        raise ValueError(f"Unknown data type: {data_type}")

def compress_with_gzip(data, output_path, window_size=None):
    """Compress data using gzip (deflate algorithm)."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        
        # Use gzip to compress with optional window size
        cmd = ['gzip', '-c']
        if window_size is not None:
            # gzip uses -w for window size (1-15, where 15 = 32KB)
            # Convert window_size to gzip format: 1024->10, 4096->12, 16384->15
            if window_size <= 1024:
                gzip_window = 10
            elif window_size <= 4096:
                gzip_window = 12
            elif window_size <= 16384:
                gzip_window = 15
            else:
                gzip_window = 15  # Max window size
            cmd.extend(['-w', str(gzip_window)])
        
        cmd.append(tmp_file.name)
        result = subprocess.run(cmd, capture_output=True, check=True)
        
        with open(output_path, 'wb') as f:
            f.write(result.stdout)
    
    window_info = f" (window={window_size})" if window_size else ""
    print(f"Created gzip compressed file: {output_path} ({len(result.stdout)} bytes){window_info}")

def compress_with_lz4(data, output_path):
    """Compress data using lz4."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        
        # Use lz4 to compress
        result = subprocess.run([
            'lz4', '-c', tmp_file.name
        ], capture_output=True, check=True)
        
        with open(output_path, 'wb') as f:
            f.write(result.stdout)
    
    print(f"Created lz4 compressed file: {output_path} ({len(result.stdout)} bytes)")

def create_null_data(data, output_path):
    """Create 'null' compressed data (just copy the original data)."""
    with open(output_path, 'wb') as f:
        f.write(data)
    
    print(f"Created null compressed file: {output_path} ({len(data)} bytes)")

def main():
    parser = argparse.ArgumentParser(description='Generate compressed test data for benchmarks')
    parser.add_argument('--output-dir', default='compressed_data', 
                       help='Output directory for compressed data files')
    parser.add_argument('--data-sizes', nargs='+', type=int, default=[32, 256, 2048, 32768],
                       help='Data sizes to generate (in bytes)')
    parser.add_argument('--data-types', nargs='+', default=['random', 'text'],
                       choices=['random', 'text', 'zeros'],
                       help='Types of data to generate')
    parser.add_argument('--algorithms', nargs='+', default=['deflate', 'lz4', 'null'],
                       choices=['deflate', 'lz4', 'null'],
                       help='Compression algorithms to use')
    parser.add_argument('--window-sizes', nargs='+', type=int, default=[1024, 4096, 16384],
                       help='Window sizes to generate (for deflate algorithm)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"Generating compressed test data in: {output_dir}")
    print(f"Data sizes: {args.data_sizes}")
    print(f"Data types: {args.data_types}")
    print(f"Algorithms: {args.algorithms}")
    print(f"Window sizes: {args.window_sizes}")
    print()
    
    # Check for required tools
    required_tools = []
    if 'deflate' in args.algorithms:
        required_tools.append('gzip')
    if 'lz4' in args.algorithms:
        required_tools.append('lz4')
    
    for tool in required_tools:
        if not shutil.which(tool):
            print(f"Error: Required tool '{tool}' not found. Please install it.")
            return 1
    
    # Generate compressed data files
    for data_size in args.data_sizes:
        for data_type in args.data_types:
            # Create test data
            test_data = create_test_data(data_size, data_type)
            
            for algorithm in args.algorithms:
                if algorithm == 'deflate':
                    # For deflate, generate files for each window size
                    for window_size in args.window_sizes:
                        # Create filename with window size
                        filename = f"{algorithm}_{data_type}_{data_size}_w{window_size}.bin"
                        output_path = output_dir / filename
                        
                        # Compress data with specific window size
                        compress_with_gzip(test_data, output_path, window_size)
                else:
                    # For lz4 and null, window size doesn't apply
                    filename = f"{algorithm}_{data_type}_{data_size}.bin"
                    output_path = output_dir / filename
                    
                    if algorithm == 'lz4':
                        compress_with_lz4(test_data, output_path)
                    elif algorithm == 'null':
                        create_null_data(test_data, output_path)
    
    # Calculate total files generated
    total_files = 0
    for algorithm in args.algorithms:
        if algorithm == 'deflate':
            total_files += len(args.data_sizes) * len(args.data_types) * len(args.window_sizes)
        else:
            total_files += len(args.data_sizes) * len(args.data_types)
    
    print(f"\n✓ Generated {total_files} compressed data files")
    print(f"Files are ready for use in decompression benchmarks")
    
    return 0

if __name__ == '__main__':
    exit(main())
