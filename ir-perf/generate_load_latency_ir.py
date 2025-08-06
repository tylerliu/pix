#!/usr/bin/env python3
"""
LLVM IR Generator for Memory Load Latency Benchmarks

Based on the pointer chasing methodology from:
https://www.alibabacloud.com/blog/the-mechanism-behind-measuring-cache-access-latency_599384

This script generates LLVM IR that measures cache access latency using:
1. Pointer chasing to avoid cache prefetcher interference
2. Configurable buffer sizes to target different cache levels
3. Configurable strides and instructions per iteration
4. Load operations only

Usage:
    python generate_load_latency_ir.py --buffer-size 32KB --stride 64 --instructions 4 --output bench.ll
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
    
    def calculate_buffer_elements(self, buffer_size_bytes: int, stride: int) -> int:
        """Calculate number of elements in buffer based on size and stride."""
        # Ensure we have at least one element
        return max(1, buffer_size_bytes // stride)
    
    def generate_pointer_chain_init(self, num_elements: int, stride: int, buffer_size: int) -> str:
        """Generate initialization code for pointer chasing chain using a loop."""
        if num_elements <= 1:
            # Special case for single element
            return f'''  ; Single element chain - points to itself
  %buffer_start = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i32 0
  %buffer_ptr = bitcast i8* %buffer_start to i8**
  store i8* %buffer_start, i8** %buffer_ptr, align 8'''
        
        # Loop for all elements except the last one
        loop_count = num_elements - 1
        return f'''  ; Initialize pointer chasing chain for {num_elements} elements
  ; Each element is {stride} bytes apart
  ; Loop {loop_count} times for elements 0 to {loop_count-1}

  br label %init_loop

init_loop:
  %i = phi i64 [0, %entry], [%next_i, %init_loop]

  ; Calculate current pointer location
  %current_offset = mul i64 %i, {stride}
  %current_ptr = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i64 %current_offset
  
  ; Convert to i8** for storing pointer
  %current_ptr_ptr = bitcast i8* %current_ptr to i8**
  
  ; Point to current_ptr + stride
  %next_ptr = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i64 %current_offset
  %next_ptr_offset = getelementptr inbounds i8, i8* %next_ptr, i64 {stride}
  store i8* %next_ptr_offset, i8** %current_ptr_ptr, align 8

  ; Continue loop
  %next_i = add i64 %i, 1
  %continue = icmp slt i64 %next_i, {loop_count}
  br i1 %continue, label %init_loop, label %init_last_element

init_last_element:
  ; Handle last element (index {loop_count}) - point back to buffer start
  %last_offset = mul i64 %next_i, {stride}
  %last_ptr = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i64 %last_offset
  %last_ptr_ptr = bitcast i8* %last_ptr to i8**
  %buffer_start = getelementptr inbounds [{buffer_size} x i8], [{buffer_size} x i8]* @buffer, i32 0, i32 0
  store i8* %buffer_start, i8** %last_ptr_ptr, align 8
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
    
    def generate_initialization_function(self, num_elements: int, stride: int, buffer_size: int) -> str:
        """Generate function to initialize the pointer chasing chain."""
        init_code = self.generate_pointer_chain_init(num_elements, stride, buffer_size)
        
        return f'''define void @init_buffer() {{
entry:
{init_code}
  ret void
}}'''
    
    def generate_ir(self, buffer_size_bytes: int, stride: int, 
                   instructions_per_iter: int) -> str:
        """Generate complete LLVM IR for memory latency benchmark."""
        
        num_elements = self.calculate_buffer_elements(buffer_size_bytes, stride)
        
        # Ensure buffer is large enough to hold all elements with proper alignment
        actual_buffer_size = max(buffer_size_bytes, num_elements * stride + stride)
        
        ir_code = f"""; Memory Latency Benchmark - Generated LLVM IR
; Operation: load
; Buffer Size: {buffer_size_bytes} bytes ({buffer_size_bytes // 1024}KB)
; Stride: {stride} bytes
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
{self.generate_initialization_function(num_elements, stride, actual_buffer_size)}
"""
        
        return ir_code


def main():
    parser = argparse.ArgumentParser(
        description="Generate LLVM IR for memory load latency benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # L1 cache test (32KB buffer, 64-byte stride, 4 loads per iteration)
  python generate_load_latency_ir.py --buffer-size 32KB --stride 64 --instructions 4 --output l1_test.ll
  
  # L2 cache test (256KB buffer, 64-byte stride, 2 loads per iteration)  
  python generate_load_latency_ir.py --buffer-size 256KB --stride 64 --instructions 2 --output l2_test.ll
  
  # L3 cache test (8MB buffer, 64-byte stride, 1 load per iteration)
  python generate_load_latency_ir.py --buffer-size 8MB --stride 64 --instructions 1 --output l3_test.ll
  
  # Memory test (64MB buffer, 64-byte stride, 1 load per iteration)
  python generate_load_latency_ir.py --buffer-size 64MB --stride 64 --instructions 1 --output memory_test.ll
        """
    )
    
    parser.add_argument('--buffer-size', required=True,
                       help='Buffer size (e.g., 32KB, 1MB, 2GB)')
    parser.add_argument('--stride', type=int, default=64,
                       help='Stride between accesses in bytes (default: 64)')
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
            print(f"  Load instructions per iteration: {args.instructions}")
        
        # Generate IR
        ir_code = generator.generate_ir(
            buffer_size_bytes=buffer_size_bytes,
            stride=args.stride,
            instructions_per_iter=args.instructions
        )
        
        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ir_code)
        
        print(f"Generated LLVM IR written to: {args.output}")
        
        if args.verbose:
            num_elements = generator.calculate_buffer_elements(buffer_size_bytes, args.stride)
            print(f"Buffer contains {num_elements} pointer chain elements")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 