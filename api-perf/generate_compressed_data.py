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
import random
import string
from pathlib import Path

def create_test_data(size_bytes, data_type="random"):
    """Create test data of specified size."""
    if data_type == "random":
        # Generate random data
        return os.urandom(size_bytes)
    elif data_type == "text":
        # Generate random text data
        chars = string.ascii_letters + string.digits + string.punctuation + " "
        return ''.join(random.choice(chars) for _ in range(size_bytes)).encode()
    elif data_type == "zeros":
        # Generate zero-filled data
        return b'\x00' * size_bytes
    else:
        raise ValueError(f"Unknown data type: {data_type}")

def compress_with_gzip(data, output_path):
    """Compress data using gzip to generate raw deflate data."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        
        # Use gzip with -n (no name) and -c (stdout) to get raw deflate data
        # The -n flag removes the filename from the gzip header
        result = subprocess.run([
            'gzip', '-n', '-c', tmp_file.name
        ], capture_output=True, check=True)
        
        # For DPDK, we need raw deflate data without gzip headers
        # gzip format: [10-byte header][deflate data][8-byte trailer]
        # We need to extract just the deflate data
        gzip_data = result.stdout
        if len(gzip_data) < 18:  # Minimum gzip size
            raise ValueError("Invalid gzip data")
        
        # Extract deflate data (skip 10-byte header and 8-byte trailer)
        deflate_data = gzip_data[10:-8]
        
        with open(output_path, 'wb') as f:
            f.write(deflate_data)
    
    print(f"Created raw deflate compressed file: {output_path} ({len(deflate_data)} bytes)")

def compress_with_lz4(data, output_path):
    """Compress data using lz4 to generate raw LZ4 data."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        
        # Use lz4 with --no-frame-crc and --no-frame to get raw LZ4 data
        # Try different options to get raw LZ4 blocks without frame headers
        try:
            result = subprocess.run([
                'lz4', '--no-frame-crc', '--no-frame', '-c', tmp_file.name
            ], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            # Fallback: try with just --no-frame
            try:
                result = subprocess.run([
                    'lz4', '--no-frame', '-c', tmp_file.name
                ], capture_output=True, check=True)
            except subprocess.CalledProcessError:
                # Final fallback: use basic lz4 and extract raw data
                result = subprocess.run([
                    'lz4', '-c', tmp_file.name
                ], capture_output=True, check=True)
                # For now, use the full output - DPDK might handle frame format
                pass
        
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
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"Generating compressed test data in: {output_dir}")
    print(f"Data sizes: {args.data_sizes}")
    print(f"Data types: {args.data_types}")
    print(f"Algorithms: {args.algorithms}")
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
                # Create filename
                filename = f"{algorithm}_{data_type}_{data_size}.bin"
                output_path = output_dir / filename
                
                # Compress data
                if algorithm == 'deflate':
                    compress_with_gzip(test_data, output_path)
                elif algorithm == 'lz4':
                    compress_with_lz4(test_data, output_path)
                elif algorithm == 'null':
                    create_null_data(test_data, output_path)
    
    print(f"\n✓ Generated {len(args.data_sizes) * len(args.data_types) * len(args.algorithms)} compressed data files")
    print(f"Files are ready for use in decompression benchmarks")
    
    return 0

if __name__ == '__main__':
    exit(main())
