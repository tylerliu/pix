#!/usr/bin/env python3
"""
LLVM IR Generator for Memory Load Latency Benchmarks

Based on the pointer chasing methodology from:
https://www.alibabacloud.com/blog/the-mechanism-behind-measuring-cache-access-latency_599384

This script generates LLVM IR that measures cache access latency using:
1. Pointer chasing to avoid cache prefetcher interference
2. Configurable buffer sizes to target different cache levels
3. Configurable cache line sizes for pointer placement
4. Configurable strides and instructions per iteration
5. Load operations only

Usage:
    python generate_load_latency_ir.py --buffer-size 32KB --cache-line-size 64 --stride 64 --instructions 4 --output bench.ll
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple
import math


class MemoryLatencyIRGenerator:
    def __init__(self):
        pass
        
    def parse_size(self, size_str: str) -> int:
        """Parse size string like '32KB', '1MB', '2GB' to bytes."""
        size_str = size_str.upper().strip()
        
        # Extract number and unit
        i = 0
        while i < len(size_str) and (size_str[i].isdigit() or size_str[i] == '.'):
            i += 1
        
        if i == 0:
            raise ValueError(f"Invalid size format: {size_str}")
            
        number = float(size_str[:i])
        unit = size_str[i:].strip()
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024,
            '': 1  # No unit means bytes
        }
        
        if unit not in multipliers:
            raise ValueError(f"Unknown size unit: {unit}")
            
        return int(number * multipliers[unit])
    
    def calculate_buffer_elements(self, buffer_size_bytes: int, cache_line_size: int) -> int:
        """Calculate number of elements in buffer based on size and cache line size."""
        # Ensure we have at least one element
        return max(1, buffer_size_bytes // cache_line_size)
    
    def generate_pointer_chain_init(self, num_elements: int, stride: int, cache_line_size: int, buffer_size: int) -> str:
        """Generate initialization code for pointer chasing chain using optimized loops based on working C code."""
        if num_elements <= 1:
            # Special case for single element
            return f'''  ; Single element chain - points to itself
  %buffer_start = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i32 0
  %buffer_ptr = bitcast i8* %buffer_start to i8**
  store i8* %buffer_start, i8** %buffer_ptr, align 8'''
        
        return f'''  ; Initialize pointer chasing chain for {num_elements} elements
  ; Each element is placed every {cache_line_size} bytes (cache line size)
  ; Stride between accesses is {stride} bytes
  ; Based on working C logic from debug_init.c

  ; Initialize pointers
  %buffer_start = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i32 0
  %buffer_end = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i64 {buffer_size}
  %current_ptr_start = bitcast i8* %buffer_start to i8**
  %next_ptr_start = getelementptr inbounds i8, i8* %buffer_start, i64 {stride}
  
  ; Check if we have any in-bounds elements
  %has_in_bounds = icmp ult i8* %next_ptr_start, %buffer_end
  br i1 %has_in_bounds, label %init_in_bounds_loop, label %init_out_bounds_setup

init_in_bounds_loop:
  %current_ptr_in = phi i8** [%current_ptr_start, %entry], [%next_current_ptr_in, %init_in_bounds_loop]
  %next_ptr_in = phi i8* [%next_ptr_start, %entry], [%next_next_ptr_in, %init_in_bounds_loop]

  ; Store the pointer: *current_ptr = next_ptr
  store i8* %next_ptr_in, i8** %current_ptr_in, align 8

  ; Move to next cache line: current_ptr += cache_line_size
  %current_ptr_in_i8 = bitcast i8** %current_ptr_in to i8*
  %next_current_ptr_in_i8 = getelementptr inbounds i8, i8* %current_ptr_in_i8, i64 {cache_line_size}
  %next_current_ptr_in = bitcast i8* %next_current_ptr_in_i8 to i8**
  
  ; Calculate next pointer: next_ptr = current_ptr + stride
  %next_next_ptr_in = getelementptr inbounds i8, i8* %next_current_ptr_in_i8, i64 {stride}

  ; Check if next pointer is still in bounds
  %still_in_bounds = icmp ult i8* %next_next_ptr_in, %buffer_end
  br i1 %still_in_bounds, label %init_in_bounds_loop, label %init_out_bounds_setup

init_out_bounds_setup:
  %current_ptr_out_start = phi i8** [%current_ptr_start, %entry], [%next_current_ptr_in, %init_in_bounds_loop]
  %next_out_ptr_start = getelementptr inbounds i8, i8* %buffer_start, i64 {cache_line_size}
  %stride_end = getelementptr inbounds i8, i8* %buffer_start, i64 {stride}
  
  ; Check if we have any out-of-bounds elements
  %has_out_bounds = icmp ult i8* %next_out_ptr_start, %stride_end
  br i1 %has_out_bounds, label %init_out_bounds_loop, label %init_last_element

init_out_bounds_loop:
  %current_ptr_out = phi i8** [%current_ptr_out_start, %init_out_bounds_setup], [%next_current_ptr_out, %init_out_bounds_loop]
  %next_ptr_out = phi i8* [%next_out_ptr_start, %init_out_bounds_setup], [%next_next_ptr_out, %init_out_bounds_loop]

  ; Store the pointer: *current_ptr = next_ptr
  store i8* %next_ptr_out, i8** %current_ptr_out, align 8

  ; Move to next cache line: current_ptr += cache_line_size
  %current_ptr_out_i8 = bitcast i8** %current_ptr_out to i8*
  %next_current_ptr_out_i8 = getelementptr inbounds i8, i8* %current_ptr_out_i8, i64 {cache_line_size}
  %next_current_ptr_out = bitcast i8* %next_current_ptr_out_i8 to i8**
  
  ; Move to next out-of-bounds target: next_ptr += cache_line_size
  %next_next_ptr_out = getelementptr inbounds i8, i8* %next_ptr_out, i64 {cache_line_size}

  ; Check if next pointer is still within stride range
  %still_out_bounds = icmp ult i8* %next_next_ptr_out, %stride_end
  br i1 %still_out_bounds, label %init_out_bounds_loop, label %init_last_element

init_last_element:
  %last_ptr = phi i8** [%current_ptr_out_start, %init_out_bounds_setup], [%next_current_ptr_out, %init_out_bounds_loop]
  
  ; Last element points back to buffer start: *last_ptr = buffer
  store i8* %buffer_start, i8** %last_ptr, align 8
  br label %init_done

init_done:'''
    
    def generate_load_chain(self, instructions_per_iter: int) -> str:
        """Generate load operations using pointer chasing."""
        operations = []
        
        # Use pointer chasing pattern - each load follows the pointer stored at current location
        current_ptr = "load_ptr"
        
        for i in range(instructions_per_iter):
            if i == instructions_per_iter - 1:
                # For the last load, name it next_load_ptr directly
                operations.append(f"  %next_load_ptr = load i8*, i8** %{current_ptr}, align 8")
            else:
                # Load the pointer
                operations.append(f"  %loaded_ptr{i} = load i8*, i8** %{current_ptr}, align 8")
                # Convert to i8** for next load
                operations.append(f"  %loaded_ptr{i}_ptr = bitcast i8* %loaded_ptr{i} to i8**")
                current_ptr = f"loaded_ptr{i}_ptr"
        
        return f'''  ; Load operations using pointer chasing
{chr(10).join(operations)}'''
    
    def generate_benchmark_function(self, instructions_per_iter: int, buffer_size: int) -> str:
        """Generate the main benchmark loop function."""
        
        op_code = self.generate_load_chain(instructions_per_iter)
        
        return f'''define void @bench_loop(i64 %N) {{
entry:
  ; Initialize the pointer chasing chain
  call void @init_buffer()
  
  ; Get pointer to buffer for initial load
  %buffer_start = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i32 0
  %buffer_ptr = bitcast i8* %buffer_start to i8**
  br label %loop

loop:
  %iv = phi i64 [0, %entry], [%next_iv, %loop]
  %load_ptr = phi i8** [%buffer_ptr, %entry], [%next_load_ptr_ptr, %loop]

  ; --- Memory latency measurement operations ---
{op_code}
  ; --- End of measured operations ---

  ; Convert next_load_ptr to i8** for next iteration
  %next_load_ptr_ptr = bitcast i8* %next_load_ptr to i8**

  ; Update loop counter
  %next_iv = add i64 %iv, 1
  %cmp = icmp slt i64 %iv, %N
  br i1 %cmp, label %loop, label %exit

exit:
  %final_ptr_int = ptrtoint i8* %next_load_ptr to i64
  call void @sink(i64 %final_ptr_int)    ; prevent dead-code elimination
  ret void
}}'''
    
    def generate_initialization_function(self, num_elements: int, stride: int, cache_line_size: int, buffer_size: int) -> str:
        """Generate function to initialize the pointer chasing chain."""
        init_code = self.generate_pointer_chain_init(num_elements, stride, cache_line_size, buffer_size)
        
        return f'''define void @init_buffer() {{
entry:
{init_code}
  ret void
}}'''
    
    def generate_ir(self, buffer_size_bytes: int, stride: int, cache_line_size: int,
                   instructions_per_iter: int) -> str:
        """Generate complete LLVM IR for memory latency benchmark."""
        
        num_elements = self.calculate_buffer_elements(buffer_size_bytes, cache_line_size)
        
        # Ensure buffer is large enough to hold all elements with proper alignment
        actual_buffer_size = max(buffer_size_bytes, num_elements * cache_line_size + cache_line_size)
        
        ir_code = f"""; Memory Latency Benchmark - Generated LLVM IR
; Operation: load
; Buffer Size: {buffer_size_bytes} bytes ({buffer_size_bytes // 1024}KB)
; Stride: {stride} bytes
; Cache Line Size: {cache_line_size} bytes
; Instructions per iteration: {instructions_per_iter}
; Elements in chain: {num_elements}
; Actual buffer size: {actual_buffer_size} bytes

; Declare external sink function to prevent optimization
declare void @sink(i64)

; Global buffer for pointer chasing - aligned to cache line
@buffer = private local_unnamed_addr global [{actual_buffer_size} x i8] zeroinitializer, align 64

; Main benchmark function
{self.generate_benchmark_function(instructions_per_iter, actual_buffer_size)}

; Initialization function
{self.generate_initialization_function(num_elements, stride, cache_line_size, actual_buffer_size)}
"""
        
        return ir_code


def main():
    parser = argparse.ArgumentParser(
        description="Generate LLVM IR for memory load latency benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # L1 cache test (32KB buffer, 64-byte cache line, 64-byte stride, 4 loads per iteration)
  python generate_load_latency_ir.py --buffer-size 32KB --cache-line-size 64 --stride 64 --instructions 4 --output l1_test.ll
  
  # L2 cache test (256KB buffer, 64-byte cache line, 64-byte stride, 2 loads per iteration)  
  python generate_load_latency_ir.py --buffer-size 256KB --cache-line-size 64 --stride 64 --instructions 2 --output l2_test.ll
  
  # L3 cache test (8MB buffer, 64-byte cache line, 64-byte stride, 1 load per iteration)
  python generate_load_latency_ir.py --buffer-size 8MB --cache-line-size 64 --stride 64 --instructions 1 --output l3_test.ll
  
  # Memory test (64MB buffer, 64-byte cache line, 64-byte stride, 1 load per iteration)
  python generate_load_latency_ir.py --buffer-size 64MB --cache-line-size 64 --stride 64 --instructions 1 --output memory_test.ll
  
  # Custom cache line size test (1MB buffer, 128-byte cache line, 256-byte stride)
  python generate_load_latency_ir.py --buffer-size 1MB --cache-line-size 128 --stride 256 --instructions 1 --output custom_test.ll
        """
    )
    
    parser.add_argument('--buffer-size', required=True,
                       help='Buffer size (e.g., 32KB, 1MB, 2GB)')
    parser.add_argument('--stride', type=int, default=64,
                       help='Stride between accesses in bytes (default: 64)')
    parser.add_argument('--cache-line-size', type=int, default=64,
                       help='Cache line size in bytes (default: 64)')
    parser.add_argument('--instructions', type=int, default=1,
                       help='Number of load instructions per loop iteration (default: 1)')
    parser.add_argument('--output', required=True,
                       help='Output LLVM IR file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    try:
        generator = MemoryLatencyIRGenerator()
        
        # Parse buffer size
        buffer_size_bytes = generator.parse_size(args.buffer_size)
        
        # Validate parameters
        if args.stride <= 0:
            raise ValueError("Stride must be positive")
        if args.cache_line_size <= 0:
            raise ValueError("Cache line size must be positive")
        if args.instructions <= 0:
            raise ValueError("Instructions per iteration must be positive")
        
        # Ensure stride is at least 8 bytes for pointer storage
        if args.stride < 8:
            print(f"Warning: Stride {args.stride} is less than 8 bytes, adjusting to 8")
            args.stride = 8
        
        if args.verbose:
            print(f"Generating LLVM IR for load latency benchmark:")
            print(f"  Buffer size: {buffer_size_bytes} bytes ({buffer_size_bytes // 1024}KB)")
            print(f"  Stride: {args.stride} bytes")
            print(f"  Cache line size: {args.cache_line_size} bytes")
            print(f"  Load instructions per iteration: {args.instructions}")
        
        # Generate IR
        ir_code = generator.generate_ir(
            buffer_size_bytes=buffer_size_bytes,
            stride=args.stride,
            cache_line_size=args.cache_line_size,
            instructions_per_iter=args.instructions
        )
        
        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ir_code)
        
        print(f"Generated LLVM IR written to: {args.output}")
        
        if args.verbose:
            num_elements = generator.calculate_buffer_elements(buffer_size_bytes, args.cache_line_size)
            print(f"Buffer contains {num_elements} pointer chain elements")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 