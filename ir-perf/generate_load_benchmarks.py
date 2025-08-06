#!/usr/bin/env python3
"""
Generate Load Latency Benchmarks

This script detects system cache configuration and generates LLVM IR
for load latency benchmarks targeting different cache levels.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def read_cache_info():
    """Read cache information from /sys/devices/system/cpu/cpu0/cache/"""
    cache_base = Path("/sys/devices/system/cpu/cpu0/cache")
    
    if not cache_base.exists():
        print("Cache information not available, using defaults")
        return {
            'line_size': 64,
            'L1': '32K',
            'L2': '256K', 
            'L3': '8192K'
        }
    
    cache_info = {}
    
    # Get cache line size
    try:
        line_size_file = cache_base / "index0" / "coherency_line_size"
        cache_info['line_size'] = int(line_size_file.read_text().strip())
    except:
        cache_info['line_size'] = 64
    
    # Find cache levels
    cache_levels = {}
    for index_dir in sorted(cache_base.glob("index*")):
        try:
            level_file = index_dir / "level"
            type_file = index_dir / "type"
            size_file = index_dir / "size"
            
            if not all(f.exists() for f in [level_file, type_file, size_file]):
                continue
                
            level = int(level_file.read_text().strip())
            cache_type = type_file.read_text().strip()
            size = size_file.read_text().strip()
            
            # Only use Data or Unified caches
            if cache_type in ['Data', 'Unified'] and level not in cache_levels:
                cache_levels[level] = size
                print(f"Detected L{level} {cache_type} Cache: {size}")
                
        except Exception as e:
            print(f"Error reading cache info from {index_dir}: {e}")
            continue
    
    # Set detected or fallback values
    cache_info['L1'] = cache_levels.get(1, '32K')
    cache_info['L2'] = cache_levels.get(2, '256K')
    cache_info['L3'] = cache_levels.get(3, '8192K')
    
    return cache_info


def generate_benchmarks(cache_info, output_dir):
    """Generate load latency benchmark IR files"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Cache configurations: (level, size, multiplier, stride_multiplier)
    cache_configs = [
        ('L1', cache_info['L1'], 1, 2),  # L1: line_size * 2
        ('L1', cache_info['L1'], 2, 2),  # L1: line_size * 2
        ('L2', cache_info['L2'], 1, 2),  # L2: line_size * 2
        ('L2', cache_info['L2'], 2, 2),  # L2: line_size * 2
        ('L2', cache_info['L2'], 1, 32), # L2: line_size * 64 (larger stride)
        ('L2', cache_info['L2'], 2, 32), # L2: line_size * 64 (larger stride)
        ('L3', cache_info['L3'], 1, 2),  # L3: line_size * 2
        ('L3', cache_info['L3'], 2, 2),  # L3: line_size * 2
        ('L3', cache_info['L3'], 8, 2),  # L3: line_size * 2 (exceeds cache)
        ('L3', cache_info['L3'], 1, 32), # L3: line_size * 64 (larger stride)
        ('L3', cache_info['L3'], 2, 32), # L3: line_size * 64 (larger stride)
        ('L3', cache_info['L3'], 8, 32), # L3: line_size * 64 (larger stride, exceeds cache)
    ]
    
    # Instructions per loop variations
    instruction_counts = [1, 2, 4]
    
    generated_files = []
    
    for cache_level, cache_size, multiplier, stride_mult in cache_configs:
        for instructions in instruction_counts:
            # Parse cache size (e.g., "32K" -> 32, "K")
            match = re.match(r'(\d+)([KMG]?)', cache_size)
            if not match:
                print(f"Warning: Could not parse cache size: {cache_size}")
                continue
                
            size_num, size_unit = match.groups()
            size_num = int(size_num)
            
            # Calculate buffer size
            buffer_size_num = size_num * multiplier
            buffer_size_arg = f"{buffer_size_num}{size_unit}B"
            
            # Calculate stride
            stride = cache_info['line_size'] * stride_mult
            
            # Generate benchmark name with better naming scheme
            if multiplier == 1:
                # Use the actual buffer size for naming
                if size_unit == 'K':
                    if buffer_size_num >= 1024:
                        bench_name = f"load-{buffer_size_num//1024}MB"
                    else:
                        bench_name = f"load-{buffer_size_num}KB"
                elif size_unit == 'M':
                    bench_name = f"load-{buffer_size_num}MB"
                else:
                    bench_name = f"load-{buffer_size_num}{size_unit}"
            else:
                # For multiplier > 1, use the calculated size
                if size_unit == 'K':
                    if buffer_size_num >= 1024:
                        bench_name = f"load-{buffer_size_num//1024}MB"
                    else:
                        bench_name = f"load-{buffer_size_num}KB"
                elif size_unit == 'M':
                    bench_name = f"load-{buffer_size_num}MB"
                else:
                    bench_name = f"load-{buffer_size_num}{size_unit}"
            
            # Always add stride suffix
            bench_name = f"{bench_name}-S{stride}"
            
            # Add instruction count suffix following existing pattern
            if instructions == 1:
                output_file = output_dir / f"{bench_name}.ll"
            else:
                output_file = output_dir / f"{bench_name}-{instructions}.ll"
            
            # Generate the IR file
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "generate_load_latency_ir.py"),
                "--buffer-size", buffer_size_arg,
                "--stride", str(stride),
                "--instructions", str(instructions),
                "--output", str(output_file)
            ]
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                generated_files.append(output_file.name)
                print(f"Generated: {output_file.name}")
            except subprocess.CalledProcessError as e:
                print(f"Error generating {output_file.name}: {e}")
                print(f"Command: {' '.join(cmd)}")
                if e.stdout:
                    print(f"Stdout: {e.stdout}")
                if e.stderr:
                    print(f"Stderr: {e.stderr}")
    
    return generated_files


def write_cmake_list(generated_files, output_dir):
    """Write a CMake file listing the generated benchmarks"""
    cmake_file = Path(output_dir) / "load_benchmarks.cmake"
    
    with open(cmake_file, 'w') as f:
        f.write("# Generated load latency benchmarks\n")
        f.write("set(LOAD_BENCHMARK_FILES\n")
        for filename in sorted(generated_files):
            f.write(f"    {filename}\n")
        f.write(")\n")
    
    print(f"Wrote CMake list to: {cmake_file}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_load_benchmarks.py <output_dir>")
        return 1
    
    output_dir = sys.argv[1]
    
    print("Detecting system cache configuration...")
    cache_info = read_cache_info()
    
    print(f"Cache configuration:")
    print(f"  L1 line size: {cache_info['line_size']} bytes")
    print(f"  Stride: {cache_info['line_size'] * 2} bytes")
    print(f"  L1 cache size: {cache_info['L1']}")
    print(f"  L2 cache size: {cache_info['L2']}")
    print(f"  L3 cache size: {cache_info['L3']}")
    
    print(f"\nGenerating load latency benchmarks to: {output_dir}")
    generated_files = generate_benchmarks(cache_info, output_dir)
    
    write_cmake_list(generated_files, output_dir)
    
    print(f"\nGenerated {len(generated_files)} benchmark files")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 