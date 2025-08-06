#!/usr/bin/env python3
"""
Memory Latency Analysis Script

This script analyzes memory benchmark results to estimate latencies for:
- L1 cache hits
- L2 cache hits  
- L3 cache hits (if available)
- Memory access

It works by:
1. Using linear regression within each benchmark series to get per-instruction access ratios and cycle counts
2. Setting up a system of linear equations across different benchmark cases
3. Solving for individual L1/L2/L3/memory latencies
4. Failing explicitly when the system cannot be solved reliably
"""

import argparse
import csv
import os
import glob
import re
import numpy as np
from datetime import datetime
from collections import defaultdict
import math


class MemoryLatencyAnalyzer:
    def __init__(self, verbose=False, iterations=None):
        self.verbose = verbose
        self.iterations = iterations  # If None, will be read from CSV
        self.benchmark_data = []
        self.regression_results = {}
        self.latency_results = {}
        
    def load_csv_files(self, pattern="memory_benchmark_results_*.csv"):
        """Load memory benchmark CSV files."""
        csv_files = glob.glob(pattern)
        if not csv_files:
            print(f"No CSV files found matching pattern: {pattern}")
            return False
            
        # Use the most recent file
        csv_files.sort(reverse=True)
        latest_file = csv_files[0]
        
        if self.verbose:
            print(f"Loading data from: {latest_file}")
            
        try:
            with open(latest_file, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                self.benchmark_data = list(reader)
            
            # If iterations not provided, read from CSV (assume all benchmarks use same iterations)
            if self.iterations is None and self.benchmark_data:
                if 'iterations' in self.benchmark_data[0]:
                    self.iterations = int(self.benchmark_data[0]['iterations'])
                    if self.verbose:
                        print(f"Using iterations from CSV: {self.iterations}")
                else:
                    print("⚠ Warning: No iterations data found in CSV, assuming 100M iterations")
                    self.iterations = 100000000
            
            print(f"Loaded {len(self.benchmark_data)} benchmark results")
            return True
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return False
    
    def group_benchmarks_by_type(self):
        """Group benchmarks by memory operation type and buffer size for separate analysis."""
        groups = defaultdict(list)
        
        for result in self.benchmark_data:
            benchmark = result['benchmark']
            
            # Parse benchmark name: bench_memory_{operation}-{bufferSize}-S{stride}-{countInLoop}
            # e.g., "bench_memory_load-1MB-S128-4" -> ("load", "1MB", 128, 4)
            # Also handle: "bench_memory_load-1MB-S128" -> ("load", "1MB", 128, 1)
            if 'bench_memory_' in benchmark:
                # Remove the bench_memory_ prefix
                name_part = benchmark.replace('bench_memory_', '')
                parts = name_part.split('-')
                
                if len(parts) >= 2:
                    operation = parts[0]      # store, load, atomic_add, etc.
                    buffer_size = parts[1]    # 32KB, 1MB, etc.
                    
                    # Check for stride component (-S*)
                    stride = None
                    instruction_count = 1
                    
                    # Look for stride component in any part of the name
                    stride_part = None
                    for i, part in enumerate(parts):
                        if part.startswith('S'):
                            stride_part = part
                            stride_index = i
                            break
                    
                    if stride_part:
                        # Has stride component
                        try:
                            stride = int(stride_part[1:])  # Remove 'S' prefix
                        except ValueError:
                            if self.verbose:
                                print(f"Warning: Could not parse stride from {benchmark}")
                            continue
                        
                        # Handle instruction count (could be before or after stride)
                        remaining_parts = [p for j, p in enumerate(parts) if j != stride_index]
                        if len(remaining_parts) >= 2:
                            # Check if the last part is a number (instruction count)
                            try:
                                instruction_count = int(remaining_parts[-1])
                            except ValueError:
                                # Not a number, assume instruction count is 1
                                pass
                    else:
                        # No stride component, check if third part is instruction count
                        if len(parts) >= 3:
                            count_in_loop = parts[2]  # 4, 2, 1, etc.
                            try:
                                instruction_count = int(count_in_loop)
                            except ValueError:
                                if self.verbose:
                                    print(f"Warning: Could not parse instruction count from {benchmark}")
                                continue
                        # If only 2 parts, assume instruction count is 1 (default)
                    
                    # Group by operation, buffer size, and stride
                    # This allows separate analysis of different stride patterns
                    if stride is not None:
                        group_key = f"{operation}-{buffer_size}-S{stride}"
                    else:
                        group_key = f"{operation}-{buffer_size}"
                    
                    groups[group_key].append({
                        'benchmark': benchmark,
                        'operation': operation,
                        'buffer_size': buffer_size,
                        'stride': stride,
                        'instruction_count': instruction_count,
                        'data': result
                    })
                elif self.verbose:
                    print(f"Warning: Could not parse benchmark name format: {benchmark}")
        
        # Sort each group by instruction count
        for group in groups.values():
            group.sort(key=lambda x: x['instruction_count'])
        
        if self.verbose:
            print(f"\nBenchmark groups found:")
            for group_key, group_data in groups.items():
                operation = group_data[0]['operation']
                buffer_size = group_data[0]['buffer_size']
                stride = group_data[0].get('stride', 'default')
                count = len(group_data)
                print(f"  {group_key}: {count} benchmarks ({operation} operation, {buffer_size} buffer, stride={stride})")
            
        return groups
    
    def perform_linear_regression(self, group_key, group_data):
        """
        Perform linear regression to find per-instruction slopes for metrics.
        Returns slopes and R² values.
        """
        if len(group_data) < 2:
            if self.verbose:
                print(f"  Skipping {group_key}: insufficient data points ({len(group_data)} < 2)")
            return None
            
        # Extract instruction counts and metrics
        instruction_counts = []
        metrics_data = defaultdict(list)
        
        for item in group_data:
            instruction_counts.append(item['instruction_count'])
            data = item['data']
            
            # Key metrics we want to analyze
            key_metrics = ['cycles', 'l1_loads', 'l1_load_misses', 'l1_fills',
                          'l2_accesses', 'l2_hits', 'l2_misses',
                          'l3_accesses', 'l3_misses']
            
            for metric in key_metrics:
                if metric in data and data[metric] != 'N/A':
                    try:
                        value = float(data[metric])
                        # The perf values are already for the total run (iterations * instruction_count)
                        # We regress these against instruction_count to get per-instruction slopes
                        # The slope will automatically account for the iterations
                        metrics_data[metric].append(value)
                    except (ValueError, TypeError):
                        metrics_data[metric].append(np.nan)
                else:
                    metrics_data[metric].append(np.nan)
        
        # Perform regression for each metric
        regression_results = {
            'group': group_key,
            'data_points': len(instruction_counts),
            'slopes': {},
            'r_squared': {},
            'intercepts': {}
        }
        
        x = np.array(instruction_counts)
        
        for metric, y_values in metrics_data.items():
            y = np.array(y_values)
            
            # Skip if we have NaN values or insufficient valid data
            valid_mask = ~np.isnan(y)
            if np.sum(valid_mask) < 2:  # Relaxed from 3 to 2
                continue
                
            x_valid = x[valid_mask]
            y_valid = y[valid_mask]
            
            # Skip if all values are the same (no variation)
            if len(set(y_valid)) < 2:
                if self.verbose:
                    print(f"    {metric}: no variation in data, skipping")
                continue
            
            try:
                # Use numpy polyfit for linear regression
                coeffs = np.polyfit(x_valid, y_valid, 1)
                slope, intercept = coeffs[0], coeffs[1]
                
                # Calculate R²
                y_pred = slope * x_valid + intercept
                ss_res = np.sum((y_valid - y_pred) ** 2)
                ss_tot = np.sum((y_valid - np.mean(y_valid)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                # Check for negative slopes and warn/correct
                if slope < 0:
                    if self.verbose:
                        print(f"    {metric}: negative slope ({slope:.6f}) reset to 0 - may indicate measurement noise")
                    slope = 0.0
                
                # Convert slope to per-IR-instruction units
                # slope is currently in units of "metric per instruction_count"
                # We want "metric per IR instruction" = slope / iterations
                slope_per_ir_instruction = slope / self.iterations
                
                regression_results['slopes'][metric] = slope_per_ir_instruction
                regression_results['intercepts'][metric] = intercept
                regression_results['r_squared'][metric] = r_squared
                
                if self.verbose:
                    print(f"    {metric}: slope={slope_per_ir_instruction:.6f} per IR instruction, R²={r_squared:.4f}")
                    
            except Exception as e:
                if self.verbose:
                    print(f"    {metric}: regression failed - {e}")
                continue
        
        # Include original data for comprehensive regression
        regression_results['data'] = group_data
        
        return regression_results
    
    def solve_latency_system(self):
        """
        Solve for cache latencies using a single comprehensive linear regression.
        
        Model: cycles = L1_lat*L1_accesses + L2_lat*L2_accesses + ... + Memory_lat*Memory_accesses + base_latencies
        
        Where base_latencies are series-specific constants (one per benchmark series like "load-1MB", "store-2KB", etc.)
        """
        if not self.regression_results:
            raise ValueError("No regression results available. Run analyze_all_groups() first.")
        
        print(f"Solving comprehensive latency system...")
        
        # Collect all individual data points and separate by operation
        operations_data = {}  # operation -> list of data points
        
        for group_key, results in self.regression_results.items():
            # Extract operation from group_key (e.g., "load-1MB" -> "load")
            operation = group_key.split('-')[0]
            if operation not in operations_data:
                operations_data[operation] = {'data_points': [], 'series_names': set()}
            
            # Use the original data points, not the regression slopes
            group_data = results['data']
            operations_data[operation]['series_names'].add(group_key)
            
            for data_item in group_data:
                # Extract per-instruction metrics for this specific data point
                instruction_count = data_item['instruction_count']
                raw_data = data_item['data']
                filtered_data = filter(lambda k_v: k_v[0] in ['cycles', 'l1_loads', 'l1_load_misses', 'l2_accesses', 'l2_hits', 'l2_misses', 'l3_accesses', 'l3_hits', 'l3_misses'] and k_v[1] != 'N/A', raw_data.items())
                data_point = dict(map(lambda k_v: (k_v[0], float(k_v[1])), filtered_data))
                scaled_cache_metrics = self._scale_cache_metrics(data_point, instruction_count)
                
                operations_data[operation]['data_points'].append({
                    'series': group_key,
                    'instruction_count': instruction_count,
                    'cycles': raw_data['cycles'],
                    'scaled_metrics': scaled_cache_metrics
                })
        
        if not operations_data:
            raise ValueError("No valid data points found for analysis")
        
        # Solve each operation separately
        operation_results = {}
        
        for operation, op_data in operations_data.items():
            all_data_points = op_data['data_points']
            series_list = sorted(op_data['series_names'])
            
            print(f"\nSolving {operation} operation:")
            print(f"  {len(all_data_points)} data points across {len(series_list)} series: {', '.join(series_list)}")
            
            # Determine available cache levels dynamically
            available_cache_levels = self._determine_cache_levels(all_data_points)
            print(f"  Cache levels detected: {', '.join(available_cache_levels)}")
            
            # Build the comprehensive linear system for this operation
            # Variables: [L1_lat, L2_lat, L3_lat, ..., Memory_lat, base_series1, base_series2, ...]
            n_cache_vars = len(available_cache_levels)
            n_series_vars = len(series_list)
            n_total_vars = n_cache_vars + n_series_vars
            
            A = []  # Coefficient matrix
            b = []  # RHS (cycles)
            
            for data_point in all_data_points:
                row = [0.0] * n_total_vars
                
                # Cache latency coefficients
                for i, level in enumerate(available_cache_levels):
                    if level.lower() == 'memory':
                        metric_key = 'memory_hits'
                    else:
                        metric_key = f'{level.lower()}_hits'
                    
                    if metric_key in data_point['scaled_metrics']:
                        row[i] = data_point['scaled_metrics'][metric_key]
                
                # Series base latency coefficient (1 for this series, 0 for others)
                series_idx = series_list.index(data_point['series'])
                row[n_cache_vars + series_idx] = 1.0
                
                A.append(row)
                b.append(data_point['scaled_metrics']['cycles'])
            
            A = np.array(A)
            b = np.array(b)
            
            print(f"  Solving system: {len(b)} equations, {n_total_vars} variables")
            
            if self.verbose:
                print(f"  Coefficient matrix shape: {A.shape}")
                print("  Sample equations:")
                for i in range(min(3, len(A))):
                    cache_part = " + ".join([f"{A[i][j]:.3f}*{level}" for j, level in enumerate(available_cache_levels)])
                    series_part = f" + base_{series_list[np.argmax(A[i][n_cache_vars:])]}"
                    print(f"    {cache_part}{series_part} = {b[i]:.3f}")
                
                # Show coefficient matrix statistics
                print(f"  Coefficient matrix statistics:")
                for j, level in enumerate(available_cache_levels):
                    col = A[:, j]
                    print(f"    {level}: min={col.min():.6f}, max={col.max():.6f}, mean={col.mean():.6f}, std={col.std():.6f}")
                
                # Check for near-zero columns
                near_zero_cols = []
                for j in range(A.shape[1]):
                    col = A[:, j]
                    if j < n_cache_vars:  # Cache variable columns
                        if col.max() < 1e-6:
                            near_zero_cols.append(f"{available_cache_levels[j]} (cache)")
                    else:  # Series base latency columns
                        if col.max() < 0.5:  # Series indicators should be 0 or 1
                            near_zero_cols.append(f"{series_list[j-n_cache_vars]} (base)")
                
                if near_zero_cols:
                    print(f"  ⚠ Near-zero coefficient columns: {', '.join(near_zero_cols)}")
                
                # Show full coefficient matrix
                print(f"  \nFull coefficient matrix A:")
                header = [f"{level:>10s}" for level in available_cache_levels] + [f"base_{s:>8s}" for s in series_list]
                print("    " + " ".join(header))
                for i, row in enumerate(A):
                    row_str = " ".join([f"{val:10.6f}" for val in row])
                    print(f"{i:2d}: {row_str} | {b[i]:8.3f}")
                
                print(f"  \nRHS vector b: {b}")
            
            # Solve using least squares
            try:
                solution, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
                
                if rank < n_total_vars:
                    print(f"  ⚠ Warning: System is rank deficient (rank={rank}, need {n_total_vars})")
                
                # Extract results
                cache_latencies = solution[:n_cache_vars]
                base_latencies = solution[n_cache_vars:]
                
                # Calculate R-squared
                y_pred = A @ solution
                ss_res = np.sum((b - y_pred) ** 2)
                ss_tot = np.sum((b - np.mean(b)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                # Sanity checks
                warnings = []
                for i, (level, latency) in enumerate(zip(available_cache_levels, cache_latencies)):
                    if latency < 0:
                        warnings.append(f"Negative {level} latency: {latency:.2f} cycles")
                    elif level.lower() != 'memory' and latency > 50:
                        warnings.append(f"Very high {level} latency: {latency:.2f} cycles")
                    elif level.lower() == 'memory' and latency > 1000:
                        warnings.append(f"Very high memory latency: {latency:.2f} cycles")
                
                if warnings:
                    for warning in warnings:
                        print(f"  ⚠ Warning: {warning}")
                
                # Store results for this operation
                operation_results[operation] = {
                    'cache_latencies': dict(zip(available_cache_levels, cache_latencies)),
                    'base_latencies': dict(zip(series_list, base_latencies)),
                    'r_squared': r_squared,
                    'equations_used': len(b),
                    'rank': rank,
                    'residuals': residuals[0] if len(residuals) > 0 else None,
                    'series_analyzed': series_list,
                    'cache_levels': available_cache_levels
                }
                
                print(f"  ✓ Successfully solved {operation} operation (R²={r_squared:.4f})")
                
            except Exception as e:
                print(f"  ✗ Failed to solve {operation} operation: {str(e)}")
                continue
        
        if not operation_results:
            raise ValueError("Failed to solve latencies for any operation")
        
        # Store comprehensive results
        self.latency_results = {
            'method': 'operation_specific_regression',
            'operation_results': operation_results
        }
        
        print(f"\n✓ Successfully solved latencies for {len(operation_results)} operations: {', '.join(operation_results.keys())}")
        return self.latency_results
    
    def _scale_cache_metrics(self, data_point, instruction_count):
        data_point['l1_accesses'] = data_point['l1_loads']
        data_point['l1_misses'] = data_point['l1_load_misses']

        access_counts = instruction_count * self.iterations
        hits = {}
        for i in range(0 if 'l0_hits' in data_point or 'l0_misses' in data_point else 1, 10): # possible L0 caches
            if f'l{i}_hits' in data_point and f'l{i}_accesses' in data_point:
                hit_ratios = data_point[f'l{i}_hits'] / data_point[f'l{i}_accesses']
            elif f'l{i}_misses' in data_point and f'l{i}_accesses' in data_point:
                hit_ratios = 1 - data_point[f'l{i}_misses'] / data_point[f'l{i}_accesses']
            elif f'l{i}_hits' in data_point and f'l{i}_misses' in data_point:
                hit_ratios = data_point[f'l{i}_hits'] / (data_point[f'l{i}_hits'] + data_point[f'l{i}_misses'])
            else:
                break
            hit_ratios = max(0, min(hit_ratios, 1))
            hits[f'l{i}_hits'] = access_counts * hit_ratios
            access_counts -= hits[f'l{i}_hits']
            hits[f'l{i}_hits'] /= self.iterations # convert to per-iteration
            if self.verbose:
                print(f"    L{i} hit ratio: {hit_ratios:.2f}")
        
        hits['memory_hits'] = access_counts / self.iterations # convert to per-instruction
        hits['cycles'] = data_point['cycles'] / self.iterations # convert to per-instruction
        
        return hits
    
    def _determine_cache_levels(self, data_points):
        """Dynamically determine which cache levels are available based on CSV columns"""
        
        # Check which cache-related columns are present in the data
        available_levels = []
        
        # Check if we have any data points with cache metrics
        if data_points:
            sample_metrics = data_points[0]['scaled_metrics']
            print(f"    ✓ Sample metrics: {sample_metrics}")
            
            # Check for L1 cache (l1_hits column)
            for i in range(0, 10):
                if f'l{i}_hits' in sample_metrics:
                    available_levels.append(f'L{i}')
                    if self.verbose:
                        print(f"    ✓ L{i} cache detected (l{i}_hits column present)")
                elif i > 0:
                    break
            
            # Check for Memory (memory_accesses column)
            available_levels.append('Memory')
            if self.verbose:
                print(f"    ✓ Memory added - Last level for the hierarchy")
        
        # Ensure we have at least a minimal working system
        if not available_levels:
            available_levels = ['L1', 'Memory']
            if self.verbose:
                print(f"    ⚠ No cache levels detected, using default: {available_levels}")
        elif len(available_levels) == 1:
            # Need at least 2 cache levels to solve anything meaningful
            if 'L1' not in available_levels:
                available_levels.append('L1')
                if self.verbose:
                    print(f"    ⚠ Adding L1 cache (required for minimal system)")
            if 'Memory' not in available_levels:
                available_levels.append('Memory')
                if self.verbose:
                    print(f"    ⚠ Adding Memory (required for minimal system)")
        
        if self.verbose:
            print(f"    Final cache levels: {available_levels}")
        
        return available_levels
    
    def analyze_all_groups(self):
        """Analyze all benchmark groups using comprehensive linear regression."""
        groups = self.group_benchmarks_by_type()
        
        if not groups:
            raise ValueError("No benchmark groups found")
            
        print(f"Found {len(groups)} benchmark groups to analyze")
        
        # Store grouped data (bypass per-series regression)
        for group_key, group_data in groups.items():
            if self.verbose:
                print(f"\nGroup: {group_key} ({len(group_data)} benchmarks)")
                for item in group_data:
                    print(f"  {item['benchmark']} (instr: {item['instruction_count']})")
            
            # Store the raw data directly for comprehensive regression
            self.regression_results[group_key] = {
                'data': group_data  # Store original data points for comprehensive regression
            }
        
        if not self.regression_results:
            raise ValueError("No valid benchmark groups obtained")
            
        print(f"\nPrepared {len(self.regression_results)} groups for comprehensive analysis")
        
        # Perform comprehensive latency analysis
        try:
            print("Calling solve_latency_system()...")
            self.latency_results = self.solve_latency_system()
            print("✓ Successfully solved for cache latencies")
        except ValueError as e:
            print(f"ValueError in solve_latency_system: {e}")
            raise ValueError(f"Failed to solve for cache latencies: {e}")
        except Exception as e:
            print(f"Unexpected error in solve_latency_system: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to solve for cache latencies: {e}")
    
    def save_latency_analysis(self, output_file=None):
        """Save latency analysis results to CSV."""
        if not self.latency_results:
            print("No latency results to save")
            return
            
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"memory_latency_analysis_{timestamp}.csv"
        
        # Save cache and memory latencies (primary focus)
        with open(output_file, 'w', newline='') as csvfile:
            if self.latency_results['method'] == 'operation_specific_regression':
                # Main CSV with cache and memory latencies
                fieldnames = ['operation', 'cache_level', 'latency_cycles', 'r_squared', 'equations_used', 'rank']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for operation, op_result in self.latency_results['operation_results'].items():
                    for cache_level, latency in op_result['cache_latencies'].items():
                        writer.writerow({
                            'operation': operation,
                            'cache_level': cache_level,
                            'latency_cycles': f"{latency:.4f}",
                            'r_squared': f"{op_result['r_squared']:.4f}",
                            'equations_used': op_result['equations_used'],
                            'rank': op_result['rank']
                        })
        
        os.chmod(output_file, 0o666)
        print(f"✓ Cache and memory latencies saved to: {output_file}")
        
        # Optionally save base latencies to a separate file (secondary importance)
        if any(len(op_result['base_latencies']) > 0 for op_result in self.latency_results['operation_results'].values()):
            base_file = output_file.replace('.csv', '_base_latencies.csv')
            with open(base_file, 'w', newline='') as base_csvfile:
                base_fieldnames = ['operation', 'series', 'base_latency_cycles']
                base_writer = csv.DictWriter(base_csvfile, fieldnames=base_fieldnames)
                base_writer.writeheader()
                
                for operation, op_result in self.latency_results['operation_results'].items():
                    for series, base_latency in op_result['base_latencies'].items():
                        base_writer.writerow({
                            'operation': operation,
                            'series': series,
                            'base_latency_cycles': f"{base_latency:.4f}"
                        })
            
            os.chmod(base_file, 0o666)
            print(f"  (Base latencies saved to: {base_file})")
    
    def print_summary(self):
        """Print analysis summary for comprehensive regression results"""
        if not hasattr(self, 'latency_results') or not self.latency_results:
            print("No latency analysis results available")
            return
        
        results = self.latency_results
        
        print("\n" + "="*60)
        print("MEMORY LATENCY ANALYSIS SUMMARY")
        print("="*60)
        
        if results['method'] == 'operation_specific_regression':
            operation_results = results['operation_results']
            print(f"Operation-Specific Analysis completed for {len(operation_results)} operations")
            
            for operation, op_result in operation_results.items():
                print(f"\n{operation.upper()} OPERATION:")
                print(f"  Solution quality (R²): {op_result['r_squared']:.4f}")
                print(f"  Equations used: {op_result['equations_used']}")
                print(f"  Matrix rank: {op_result['rank']} (variables: {len(op_result['cache_latencies']) + len(op_result['base_latencies'])})")
                print(f"  Series analyzed: {', '.join(op_result['series_analyzed'])}")
                print(f"  Cache levels: {', '.join(op_result['cache_levels'])}")
                
                print(f"  \nCACHE AND MEMORY LATENCIES:")
                for cache_level, latency in op_result['cache_latencies'].items():
                    print(f"    {cache_level} cache hit: {latency:.2f} cycles")
                
                # Quality assessment for this operation
                print(f"  \nQuality Assessment:")
                if op_result['r_squared'] > 0.95:
                    print("    ✓ Excellent fit (R² > 0.95)")
                elif op_result['r_squared'] > 0.8:
                    print("    ⚠ Good fit (R² > 0.8)")
                else:
                    print("    ✗ Poor fit (R² < 0.8) - results may be unreliable")
                
                # Check for unrealistic latencies
                cache_latencies = op_result['cache_latencies']
                warnings = []
                for level, latency in cache_latencies.items():
                    if latency < 0:
                        warnings.append(f"Negative {level} latency ({latency:.2f} cycles)")
                    elif level.lower() != 'memory' and latency > 50:
                        warnings.append(f"Very high {level} latency ({latency:.2f} cycles)")
                    elif level.lower() == 'memory' and latency > 1000:
                        warnings.append(f"Very high memory latency ({latency:.2f} cycles)")
                
                if warnings:
                    print("    Warnings:")
                    for warning in warnings:
                        print(f"      ⚠ {warning}")
                
                # Show base latencies only if verbose or if there are issues
                if self.verbose and op_result['base_latencies']:
                    print(f"  \nSeries Base Latencies (for reference):")
                    for series, base_latency in op_result['base_latencies'].items():
                        print(f"    {series}: {base_latency:.2f} cycles")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze memory latencies from benchmark results using comprehensive linear regression",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool performs rigorous analysis by:
1. Linear regression within each benchmark series to get per-instruction slopes
2. Comprehensive linear regression across all data points with series-specific base latencies
3. Extracting individual L1/L2/L3/memory latencies
4. Failing explicitly when results cannot be determined reliably

Examples:
  %(prog)s                           # Analyze latest memory benchmark results
  %(prog)s --verbose                 # Detailed analysis output
  %(prog)s --input pattern*.csv      # Analyze specific CSV files
  %(prog)s --output analysis.csv     # Save results to specific file
        """
    )
    
    parser.add_argument(
        '--input',
        default="memory_benchmark_results_*.csv",
        help='Input CSV file pattern (default: memory_benchmark_results_*.csv)'
    )
    
    parser.add_argument(
        '--output',
        help='Output CSV file for analysis results'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose analysis output'
    )
    
    args = parser.parse_args()
    
    try:
        # Create analyzer
        analyzer = MemoryLatencyAnalyzer(verbose=args.verbose)
        
        # Load data
        if not analyzer.load_csv_files(args.input):
            return 1
        
        # Analyze latencies
        analyzer.analyze_all_groups()
        
        # Print results
        analyzer.print_summary()
        
        # Save results
        analyzer.save_latency_analysis(args.output)
        
        return 0
        
    except ValueError as e:
        print(f"✗ Analysis failed: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main()) 