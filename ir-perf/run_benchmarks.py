#!/usr/bin/env python3
"""
Comprehensive IR instruction benchmarking script.
Measures cycle counts with proper CPU isolation and overhead subtraction.
"""

import subprocess
import sys
import os
import re
import argparse
import signal
import atexit
from pathlib import Path
import decimal
import csv
import math
from datetime import datetime

from analyze_memory_latency import MemoryLatencyAnalyzer

class BenchmarkRunner:
    def __init__(self, cpu_core=3, iterations=100000000, verbose=False):
        self.cpu_core = cpu_core
        self.iterations = iterations
        self.verbose = verbose
        self.build_dir = Path("build")
        self.original_settings = {}
        self.setup_completed = False
        self.supported_commands = {}
        self.teardown_completed = False
        
        # Register cleanup on exit
        atexit.register(self.teardown)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals to ensure cleanup."""
        print(f"\nReceived signal {signum}, cleaning up...")
        self.teardown()
        sys.exit(1)
    
    def get_current_settings(self):
        """Get current CPU settings to restore later."""
        try:
            # Get current governor and frequency info
            result = subprocess.run([
                "cpupower", "-c", str(self.cpu_core), "frequency-info"
            ], capture_output=True, text=True, check=True)
            
            # Parse governor from output
            for line in result.stdout.split('\n'):
                if 'current policy:' in line:
                    # Extract governor from "The governor "X" may decide..."
                    if 'governor "' in line:
                        governor_start = line.find('governor "') + 9
                        governor_end = line.find('"', governor_start)
                        if governor_end > governor_start:
                            governor = line[governor_start:governor_end]
                            self.original_settings['governor'] = governor
                            break
            
            # Try to get frequency limits using the -l option for raw format
            try:
                freq_result = subprocess.run([
                    "cpupower", "-c", str(self.cpu_core), "frequency-info", "-l"
                ], capture_output=True, text=True, check=True)
                
                # Parse raw frequency format (e.g., "1500000 2900000")
                freq_lines = freq_result.stdout.strip().split('\n')
                if len(freq_lines) >= 2:
                    freq_parts = freq_lines[1].strip().split()
                    if len(freq_parts) >= 2:
                        self.original_settings['min_freq'] = freq_parts[0]
                        self.original_settings['max_freq'] = freq_parts[1]
                        print("✓ Captured current CPU settings for restoration")
                        return
            except subprocess.CalledProcessError:
                pass  # Fall back to parsing the verbose output
            
            # Fallback: Parse frequency limits from verbose output
            for line in result.stdout.split('\n'):
                if 'hardware limits:' in line:
                    # Extract min and max frequencies
                    freq_range = line.split(':')[1].strip()
                    if 'GHz' in freq_range:
                        parts = freq_range.split('-')
                        if len(parts) == 2:
                            min_freq = decimal.Decimal(parts[0].strip().replace(' GHz', '')) * 1000000
                            max_freq = decimal.Decimal(parts[1].strip().replace(' GHz', '')) * 1000000
                            self.original_settings['min_freq'] = min_freq
                            self.original_settings['max_freq'] = max_freq
                            break
            
            print("✓ Captured current CPU settings for restoration")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠ Warning: Could not capture current settings: {e}")
            # Set defaults
            self.original_settings['governor'] = 'ondemand'
    
    def check_cpupower_support(self):
        """Check which cpupower subcommands are available."""
        supported_commands = {}
        
        # Check if frequency-set is supported
        try:
            result = subprocess.run([
                "cpupower", "frequency-set", "--help"
            ], capture_output=True, text=True, check=True)
            supported_commands['frequency-set'] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            supported_commands['frequency-set'] = False
        
        # Check if idle-set is supported
        try:
            result = subprocess.run([
                "cpupower", "idle-set", "--help"
            ], capture_output=True, text=True, check=True)
            supported_commands['idle-set'] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            supported_commands['idle-set'] = False
        
        return supported_commands
    
    def setup_cpu(self):
        """Set CPU to performance mode and pin to specific core."""
        print("Setting up CPU for benchmarking...")
        
        # Check what cpupower features are available
        self.supported_commands = self.check_cpupower_support()
        
        # Capture current settings first
        self.get_current_settings()
        
        # Print current settings before changing
        print(f"Current CPU {self.cpu_core} settings:")
        if 'governor' in self.original_settings:
            print(f"  Governor: {self.original_settings['governor']}")
        if 'min_freq' in self.original_settings and 'max_freq' in self.original_settings:
            print(f"  Frequency range: {self.original_settings['min_freq']} - {self.original_settings['max_freq']} Hz")
        print()
        
        # Set CPU governor to performance (if supported)
        if self.supported_commands.get('frequency-set', False):
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "frequency-set", 
                    "-g", "performance"
                ], check=True, capture_output=True)
                print(f"✓ Set CPU {self.cpu_core} to performance mode")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not set CPU governor: {e}")
        else:
            print("⚠ Note: CPU frequency control not available, skipping governor setting")
        
        # Disable CPU idle states for more consistent performance (if supported)
        if self.supported_commands.get('idle-set', False):
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "idle-set", "-d", "0"
                ], check=True, capture_output=True)
                print("✓ Disabled CPU idle states")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not disable CPU idle states: {e}")
        else:
            print("⚠ Note: CPU idle state control not available, skipping idle state setting")
        
        self.setup_completed = True
    
    def teardown(self):
        """Restore original CPU settings."""
        if not self.setup_completed or self.teardown_completed:
            return
        
        self.teardown_completed = True
        print("\nRestoring CPU settings...")
        
        # Restore governor (only if frequency-set was supported)
        if self.supported_commands.get('frequency-set', False) and 'governor' in self.original_settings:
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "frequency-set",
                    "-g", self.original_settings['governor']
                ], check=True, capture_output=True)
                print(f"✓ Restored governor to {self.original_settings['governor']}")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not restore governor: {e}")
        elif self.supported_commands.get('frequency-set', False):
            # Fallback: restore to ondemand
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "frequency-set",
                    "-g", "ondemand"
                ], check=True, capture_output=True)
                print("✓ Restored governor to ondemand (fallback)")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not restore governor: {e}")
        
        # Restore frequency limits if we have them and frequency-set is supported
        if (self.supported_commands.get('frequency-set', False) and 
            'max_freq' in self.original_settings and 'min_freq' in self.original_settings):
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "frequency-set",
                    "-u", self.original_settings['max_freq'], 
                    "-d", self.original_settings['min_freq']
                ], check=True, capture_output=True)
                print(f"✓ Restored frequency limits")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not restore frequency limits: {e}")
        
        # Re-enable CPU idle states (only if idle-set was supported)
        if self.supported_commands.get('idle-set', False):
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "idle-set", "-e", "0"
                ], check=True, capture_output=True)
                print("✓ Re-enabled CPU idle states")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not re-enable CPU idle states: {e}")
        
        print("✓ CPU settings restored")
    
    def warm_up(self, executable):
        """Run executable once to warm up caches."""
        if self.verbose:
            print(f"Warming up {executable}...")
        try:
            subprocess.run([
                "taskset", "-c", str(self.cpu_core),
                str(self.build_dir / executable),
                str(self.iterations)
            ], check=True, capture_output=True)
            if self.verbose:
                print("✓ Warm-up completed")
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"✗ Warm-up failed: {e}")
            return False
        return True
    
    def is_memory_benchmark(self, benchmark_name):
        """Check if benchmark is memory-related."""
        return benchmark_name.startswith('bench_memory_')
    
    def detect_system_architecture(self):
        """Detect system architecture and return appropriate perf events."""
        import platform
        
        arch = platform.machine().lower()
        
        if arch in ['x86_64', 'amd64']:
            # x86_64 system events
            return {
                'basic_events': 'cycles,instructions,branch-misses',
                'memory_events': 'cycles,instructions,branch-misses,cache-misses,cache-references,L1-dcache-load-misses,L1-dcache-loads,l2_cache_req_stat.dc_access_in_l2,l2_cache_req_stat.dc_hit_in_l2',
                'memory_metrics': 'all_l1_data_cache_fills',
                'arch': 'x86_64'
            }
        elif arch in ['aarch64', 'arm64']:
            # ARM64 system events
            return {
                'basic_events': 'cpu_cycles,inst_retired,br_mis_pred',
                'memory_events': 'cpu_cycles,inst_retired,br_mis_pred,l1d_cache,l1d_cache_refill,l2d_cache,l2d_cache_refill,l3d_cache,l3d_cache_refill,ll_cache_rd,ll_cache_miss_rd',
                'memory_metrics': '',
                'arch': 'arm64'
            }
        else:
            # Fallback to basic events for unknown architecture
            return {
                'basic_events': 'cycles,instructions,branch-misses',
                'memory_events': 'cycles,instructions,branch-misses',
                'memory_metrics': '',
                'arch': 'unknown'
            }
    
    def linear_regression(self, x_values, y_values):
        """Perform linear regression using standard library."""
        if len(x_values) < 2:
            return None, None, None
        if len(y_values) != len(x_values):
            raise ValueError("x_values and y_values must have the same length")
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x_values[i] * y_values[i] for i in range(n))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return None, None, None
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R²
        y_mean = sum_y / n
        y_pred = [slope * x + intercept for x in x_values]
        
        ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return slope, intercept, r_squared
    
    def check_perf_permissions(self):
        """Check if perf works without sudo and warn if needed."""
        try:
            # Try to run a simple perf command
            result = subprocess.run([
                "perf", "stat", "-e", "cycles", "true"
            ], capture_output=True, text=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    

    
    def run_perf_measurement(self, executable):
        """Run perf stat measurement on the executable."""
        if self.verbose:
            print(f"Measuring {executable}...")
        executable_path = self.build_dir / executable
        
        # Detect system architecture and choose appropriate events
        system_config = self.detect_system_architecture()
        is_memory = self.is_memory_benchmark(executable)
        
        if is_memory:
            perf_events = system_config['memory_events']
            perf_metrics = system_config['memory_metrics']
        else:
            perf_events = system_config['basic_events']
            perf_metrics = ""
        
        if self.verbose:
            print(f"  Architecture: {system_config['arch']}")
            print(f"  Perf events: {perf_events}")
            if perf_metrics:
                print(f"  Perf metrics: {perf_metrics}")
        
        try:
            cmd = ["perf", "stat", "-e", perf_events]
            if perf_metrics:
                cmd.extend(["-M", perf_metrics])
            cmd.extend(["taskset", "-c", str(self.cpu_core), str(executable_path), str(self.iterations)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self.parse_perf_output(result.stderr, is_memory)
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"✗ Perf measurement failed: {e}")
                print(f"Command: {' '.join(e.cmd)}")
                print(f"Error output: {e.stderr}")
            else:
                # Provide helpful error message even in non-verbose mode
                if "Permission denied" in str(e.stderr) or "Operation not permitted" in str(e.stderr):
                    print(" ✗ (permission denied - try running with sudo)")
                else:
                    print(" ✗")
            return None
    
    def parse_perf_output(self, output, is_memory=False):
        """Parse perf stat output and extract metrics."""
        metrics = {}
        system_config = self.detect_system_architecture()
        
        # Define parsing patterns for different metric types
        parsing_patterns = {
            # Basic metrics (always parsed)
            'basic': {
                'cycles': r'(\d+(?:,\d+)*)\s+(?:cycles|cpu_cycles)',
                'instructions': r'(\d+(?:,\d+)*)\s+(?:instructions|inst_retired)',
                'branch_misses': r'(\d+(?:,\d+)*)\s+(?:branch-misses|br_mis_pred)'
            },
            
            # Memory metrics (only for memory benchmarks)
            'memory': {
                'l1_loads': r'(\d+(?:,\d+)*)\s+(?:L1-dcache-loads|l1d_cache)',
                'l1_load_misses': r'(\d+(?:,\d+)*)\s+(?:L1-dcache-load-misses|l1d_cache_refill)',
                'l1_stores': r'(\d+(?:,\d+)*)\s+L1-dcache-stores',
                'l3_accesses': r'(\d+(?:,\d+)*)\s+(?:l3_cache_accesses|l3d_cache)',
                'l3_misses': r'(\d+(?:,\d+)*)\s+(?:l3_misses|l3d_cache_refill)',
                'll_cache_rd': r'(\d+(?:,\d+)*)\s+ll_cache_rd',
                'll_cache_miss_rd': r'(\d+(?:,\d+)*)\s+ll_cache_miss_rd'
            },
            
            # Special metrics with different parsing logic
            'special': {}
        }
        
        # Configure architecture-specific patterns
        if system_config['arch'] == 'x86_64':
            # x86_64: Use special patterns for metric-format events
            parsing_patterns['special'].update({
                'l1_fills': {
                    'pattern': r'(\d+(?:,\d+)*)\s+[^#]*#\s*(\d+(?:\.\d+)?)\s*all_l1_data_cache_fills',
                    'group': 2,
                    'transform': lambda x: x.replace('.00', '')
                }
            })
            # x86_64: Add L2 cache request stat events
            parsing_patterns['memory'].update({
                'l2_accesses': r'(\d+(?:,\d+)*)\s+l2_cache_req_stat\.dc_access_in_l2',
                'l2_hits': r'(\d+(?:,\d+)*)\s+l2_cache_req_stat\.dc_hit_in_l2'
            })
        elif system_config['arch'] == 'arm64':
            # ARM64: Use direct event format for L2
            parsing_patterns['memory']['l2_accesses'] = r'(\d+(?:,\d+)*)\s+l2d_cache'
            parsing_patterns['memory']['l2_misses'] = r'(\d+(?:,\d+)*)\s+l2d_cache_refill'
        
        # Parse basic metrics
        for metric_name, pattern in parsing_patterns['basic'].items():
            match = re.search(pattern, output)
            if match:
                value = int(match.group(1).replace(',', ''))
                metrics[metric_name] = value
        
        # Parse memory metrics if this is a memory benchmark
        if is_memory:
            # Parse standard memory metrics
            for metric_name, pattern in parsing_patterns['memory'].items():
                match = re.search(pattern, output)
                if match:
                    value = int(match.group(1).replace(',', ''))
                    metrics[metric_name] = value
            
            # Parse special metrics
            for metric_name, config in parsing_patterns['special'].items():
                match = re.search(config['pattern'], output)
                if match:
                    value = match.group(config['group'])
                    if 'transform' in config:
                        value = config['transform'](value)
                    value = int(value.replace(',', ''))
                    
                    # Use target name if specified, otherwise use metric_name
                    target_name = config.get('target', metric_name)
                    metrics[target_name] = value
            
            # Debug: Print available metrics for troubleshooting
            if self.verbose:
                print(f"    Available memory metrics: {list(metrics.keys())}")
            
            # Calculate cache hit ratios
            self._calculate_cache_hit_ratios(metrics)
        
        # Calculate cycles per instruction
        if 'cycles' in metrics and 'instructions' in metrics:
            metrics['cycles_per_inst'] = metrics['cycles'] / metrics['instructions']
        
        return metrics
    
    def _calculate_cache_hit_ratios(self, metrics):
        """Calculate cache hit ratios from parsed metrics."""
        
        # Calculate L2 misses for x86_64 where we have accesses and hits but no direct miss metric
        if 'l2_accesses' in metrics and 'l2_hits' in metrics and 'l2_misses' not in metrics:
            if metrics['l2_accesses'] >= metrics['l2_hits']:
                metrics['l2_misses'] = metrics['l2_accesses'] - metrics['l2_hits']
            else:
                # Handle edge case where hits > accesses (measurement noise)
                metrics['l2_misses'] = 0
        
        hit_ratio_calculations = [
            {
                'ratio_name': 'l1_load_hit_ratio',
                'total': 'l1_loads',
                'misses': 'l1_load_misses',
                'formula': lambda total, misses: 1.0 - (misses / total)
            },
            {
                'ratio_name': 'l2_hit_ratio',
                'total': 'l2_accesses',
                'hits': 'l2_hits',
                'formula': lambda total, hits: hits / total
            },
            {
                'ratio_name': 'l2_hit_ratio',
                'total': 'l2_accesses',
                'misses': 'l2_misses',
                'formula': lambda total, misses: 1.0 - (misses / total)
            },
            {
                'ratio_name': 'l3_hit_ratio',
                'total': 'l3_accesses',
                'misses': 'l3_misses',
                'formula': lambda total, misses: 1.0 - (misses / total)
            },
            {
                'ratio_name': 'll_cache_hit_ratio',
                'total': 'll_cache_rd',
                'misses': 'll_cache_miss_rd',
                'formula': lambda total, misses: 1.0 - (misses / total)
            }
        ]
        
        for calc in hit_ratio_calculations:
            total_key = calc['total']
            if total_key in metrics and metrics[total_key] > 0:
                # Check if we have hits or misses
                if 'hits' in calc and calc['hits'] in metrics:
                    metrics[calc['ratio_name']] = calc['formula'](metrics[total_key], metrics[calc['hits']])
                elif 'misses' in calc and calc['misses'] in metrics:
                    metrics[calc['ratio_name']] = calc['formula'](metrics[total_key], metrics[calc['misses']])
    
    def find_benchmarks(self):
        """Find all benchmark executables."""
        benchmarks = []
        for executable in self.build_dir.glob("bench_*"):
            if executable.is_file() and os.access(executable, os.X_OK):
                benchmarks.append(executable.name)
        return sorted(benchmarks)
    
    def run_benchmarks(self, specific_benchmarks=None):
        """Run all benchmarks or specific ones."""
        if specific_benchmarks:
            benchmarks = specific_benchmarks
        else:
            benchmarks = self.find_benchmarks()
        
        if not benchmarks:
            print("✗ No benchmark executables found in build/")
            return
        
        print(f"Found {len(benchmarks)} benchmarks")
        
        # Check permissions once at the beginning
        check_permissions()
        
        # Group benchmarks by instruction type
        benchmark_groups = self.group_benchmarks(benchmarks)
        
        all_results = []
        latency_results = []
        failed_benchmarks = []
        
        for group_name, group_benchmarks in benchmark_groups.items():
            print(f"\n{'='*50}")
            print(f"Benchmarking group: {group_name}")
            print(f"{'='*50}")
            
            group_results = []
            
            for benchmark in group_benchmarks:
                if self.verbose:
                    print(f"\nBenchmarking: {benchmark}")
                else:
                    print(f"  Running {benchmark}...", end="", flush=True)
                
                # Warm up
                if not self.warm_up(benchmark):
                    if not self.verbose:
                        print(" ✗")
                    else:
                        print(f"{benchmark} warm-up failed")
                    failed_benchmarks.append(benchmark)
                    continue
                
                # Measure
                result = self.run_perf_measurement(benchmark)
                if result:
                    result['benchmark'] = benchmark
                    result['group'] = group_name
                    result['iterations'] = self.iterations
                    group_results.append(result)
                    all_results.append(result)
                    
                    # Print results (only if verbose)
                    if self.verbose:
                        print(f"Results for {benchmark}:")
                        print(f"  Cycles: {result['cycles']:,}")
                        print(f"  Instructions: {result['instructions']:,}")
                        print(f"  Branch misses: {result.get('branch_misses', 'N/A')}")
                        print(f"  Cycles/instruction: {result['cycles_per_inst']:.3f}")
                        
                        # Print memory metrics if available
                        if self.is_memory_benchmark(benchmark):
                            print(f"  Memory metrics:")
                            if 'l1_loads' in result:
                                print(f"    L1 loads: {result['l1_loads']:,}")
                            if 'l1_load_misses' in result:
                                print(f"    L1 load misses: {result['l1_load_misses']:,}")
                            if 'l1_load_hit_ratio' in result:
                                print(f"    L1 load hit ratio: {result['l1_load_hit_ratio']:.3f}")
                            if 'l1_fills' in result and result.get('l1_fills') != 'N/A':
                                print(f"    L1 fills: {result['l1_fills']:,}")
                            if 'all_data_cache_accesses' in result:
                                print(f"    All data cache accesses: {result['all_data_cache_accesses']:,}")
                            if 'l2_accesses' in result:
                                print(f"    L2 accesses: {result['l2_accesses']:,}")
                            if 'l2_hits' in result:
                                print(f"    L2 hits: {result['l2_hits']:,}")
                            if 'l2_misses' in result:
                                print(f"    L2 misses: {result['l2_misses']:,}")
                            if 'l2_hit_ratio' in result:
                                print(f"    L2 hit ratio: {result['l2_hit_ratio']:.3f}")
                            if 'l3_accesses' in result:
                                print(f"    L3 accesses: {result['l3_accesses']:,}")
                            if 'l3_misses' in result:
                                print(f"    L3 misses: {result['l3_misses']:,}")
                            if 'l3_hit_ratio' in result:
                                print(f"    L3 hit ratio: {result['l3_hit_ratio']:.3f}")
                    else:
                        print(" ✓")
                else:
                    if not self.verbose:
                        print(" ✗")
                    failed_benchmarks.append(benchmark)
            
            # Calculate latency for this group
            if len(group_results) >= 2:
                latency_result = self.calculate_latency(group_results)
                if latency_result:
                    latency_results.append(latency_result)
                    print(f"\nLatency calculation for {group_name}:")
                    print(f"  Estimated latency: {latency_result['latency']:.3f} cycles/IR instruction (R² = {latency_result['latency_r_squared']:.3f})")
                    print(f"  Translation efficiency: {latency_result['translation_efficiency']:.3f} instructions/IR instruction (R² = {latency_result['efficiency_r_squared']:.3f})")
        
        # Print summary
        self.print_summary(latency_results)
        
        # Save summary to CSV
        if latency_results:
            summary_csv_file = self.save_summary_to_csv(latency_results)
            print(f"Latency summary saved to: {summary_csv_file}")
        
        # Print failure summary
        if failed_benchmarks:
            self.print_failure_summary(failed_benchmarks)
        
        # Save detailed results to CSV
        if all_results:
            csv_file = self.save_results_to_csv(all_results)
            print(f"\nDetailed results saved to: {csv_file}")
            
            # Save memory benchmark results to separate CSV
            memory_csv_file = self.save_memory_results_to_csv(all_results)
            if memory_csv_file:
                print(f"Memory benchmark results saved to: {memory_csv_file}")
                
                # Run latency analysis if requested
                if hasattr(self, 'analyze_latency') and self.analyze_latency:
                    self.run_latency_analysis(memory_csv_file)
    
    def group_benchmarks(self, benchmarks):
        """Group benchmarks by instruction type (e.g., add-imm, add-imm-2, add-imm-4)."""
        groups = {}
        
        for benchmark in benchmarks:
            # Extract base name (e.g., "arithmetic_add_imm" from "bench_arithmetic_add_imm_2")
            parts = benchmark.split('_')
            if len(parts) >= 3:
                base_name = '_'.join(parts[1:3])  # e.g., "arithmetic_add-imm"
                
                # Find the base instruction name (without count suffix)
                if '-' in base_name:
                    base_parts = base_name.split('-')
                    if base_parts[-1].isdigit():
                        # Remove the count suffix
                        base_instruction = '-'.join(base_parts[:-1])
                    else:
                        base_instruction = base_name
                else:
                    base_instruction = base_name
                
                if base_instruction not in groups:
                    groups[base_instruction] = []
                groups[base_instruction].append(benchmark)
        
        # Sort benchmarks within each group by instruction count
        for group in groups.values():
            group.sort(key=lambda x: self.extract_instructions_per_loop(x))
        
        return groups
    
    def extract_instructions_per_loop(self, benchmark_name):
        """Extract the number of instructions from benchmark name."""
        # e.g., "bench_arithmetic_add-imm-2" -> 2
        parts = benchmark_name.split('_')
        if len(parts) >= 3:
            base_name = parts[2]
            if '-' in base_name:
                base_parts = base_name.split('-')
                if base_parts[-1].isdigit():
                    return int(base_parts[-1])
        return 1  # Default to 1 instruction
    
    def calculate_latency(self, group_results):
        """Calculate latency and translation efficiency using linear regression on all points with log-scale fitting."""
        if len(group_results) < 2:
            return None
        
        # Sort by instruction count
        group_results.sort(key=lambda x: self.extract_instructions_per_loop(x['benchmark']))
        
        # Collect data points
        target_ir_instructions = []
        cycles = []
        instructions = []
        
        for result in group_results:
            ir_instructions_per_loop = self.extract_instructions_per_loop(result['benchmark'])
            target_ir_instructions.append(ir_instructions_per_loop * self.iterations)
            cycles.append(result['cycles'])
            instructions.append(result['instructions'])
        
        # Calculate two linear regressions
        if len(target_ir_instructions) >= 2:
            # Regression 1: target_ir_instructions vs cycles (latency)
            latency_slope, latency_intercept, latency_r_squared = self.linear_regression(target_ir_instructions, cycles)
            
            # Regression 2: target_ir_instructions vs instructions (translation efficiency)
            efficiency_slope, efficiency_intercept, efficiency_r_squared = self.linear_regression(target_ir_instructions, instructions)
            
            if latency_slope is None or efficiency_slope is None:
                print(f"⚠ Warning: Could not calculate regression for {group_results[0]['group']}")
                return None
            
            # Convert slopes back to linear scale
            latency = latency_slope
            translation_efficiency = efficiency_slope
            
            # Warn about poor fits
            if latency_r_squared < 0.95:
                print(f"⚠ Warning: Poor latency fit for {group_results[0]['group']} (R² = {latency_r_squared:.3f})")
            if efficiency_r_squared < 0.95:
                print(f"⚠ Warning: Poor efficiency fit for {group_results[0]['group']} (R² = {efficiency_r_squared:.3f})")
            
            return {
                'group': group_results[0]['group'],
                'latency': latency,
                'translation_efficiency': translation_efficiency,
                'latency_r_squared': latency_r_squared,
                'efficiency_r_squared': efficiency_r_squared,
                'target_ir_instructions': target_ir_instructions,
                'cycles': cycles,
                'instructions': instructions,
                'benchmarks': [r['benchmark'] for r in group_results]
            }
        
        return None
    
    def print_summary(self, results):
        """Print a summary table of latency results."""
        if not results:
            return
        
        print(f"\n{'='*80}")
        print("IR INSTRUCTION PERFORMANCE SUMMARY")
        print(f"{'='*80}")
        print(f"{'Instruction Type':<25} {'Latency (cycles)':<15} {'Translation Eff.':<15} {'Lat R²':<8} {'Eff R²':<8} {'Benchmarks':<30}")
        print("-" * 80)
        
        for result in results:
            instruction_type = result['group']
            latency = f"{result['latency']:.3f}"
            translation_eff = f"{result['translation_efficiency']:.3f}"
            latency_r2 = f"{result['latency_r_squared']:.3f}"
            efficiency_r2 = f"{result['efficiency_r_squared']:.3f}"
            benchmarks = ", ".join(result['benchmarks'])
            
            print(f"{instruction_type:<25} {latency:<15} {translation_eff:<15} {latency_r2:<8} {efficiency_r2:<8} {benchmarks:<30}")
        
        print(f"\nNote: Both metrics calculated using linear regression.")
        print(f"R² shows fit quality (≥0.95 is good, <0.95 triggers warning).")
        print(f"Latency: cycles per IR instruction, Efficiency: native instructions per IR instruction.")
    
    def print_failure_summary(self, failed_benchmarks):
        """Print a summary of failed benchmarks."""
        print(f"\n{'='*80}")
        print("FAILED BENCHMARKS SUMMARY")
        print(f"{'='*80}")
        print(f"Total failed benchmarks: {len(failed_benchmarks)}")
        print()
        
        if failed_benchmarks:
            print("Failed benchmarks:")
            for benchmark in failed_benchmarks:
                print(f"  - {benchmark}")
            print()
            print("Possible causes:")
            print("  - Missing executable files")
            print("  - Permission issues (try running with sudo)")
            print("  - Insufficient CPU isolation")
            print("  - Hardware performance counter access denied")
            print("  - Benchmark executable crashed or timed out")
    
    def save_results_to_csv(self, all_results):
        """Save all benchmark results to a CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"benchmark_results_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['benchmark', 'group', 'cycles', 'instructions', 'branch_misses', 'cycles_per_inst']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in all_results:
                writer.writerow({
                    'benchmark': result['benchmark'],
                    'group': result['group'],
                    'cycles': result['cycles'],
                    'instructions': result['instructions'],
                    'branch_misses': result.get('branch_misses', 'N/A'),
                    'cycles_per_inst': f"{result['cycles_per_inst']:.6f}"
                })
        
        print(f"\n✓ Results saved to {csv_filename}")
        return csv_filename
    
    def save_memory_results_to_csv(self, all_results):
        """Save memory benchmark results to a separate CSV file."""
        # Filter memory benchmarks
        memory_results = [result for result in all_results if self.is_memory_benchmark(result['benchmark'])]
        
        if not memory_results:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"memory_benchmark_results_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='') as csvfile:
            # Check if L1 fill metrics are available in any result
            has_l1_fills = any('l1_fills' in result and result.get('l1_fills') != 'N/A' for result in memory_results)
            
            # Check if L2 cache metrics are available
            has_l2_cache = any('l2_accesses' in result for result in memory_results)
            
            # Check if L3 cache metrics are available
            has_l3_cache = any('l3_accesses' in result for result in memory_results)
            
            # Base fieldnames
            fieldnames = ['benchmark', 'group', 'iterations', 'cycles', 'instructions', 'branch_misses', 'cycles_per_inst',
                         'l1_loads', 'l1_load_misses', 'l1_load_hit_ratio']
            
            # Add L1 fill fields only if available
            if has_l1_fills:
                fieldnames.extend(['l1_fills'])
            
            # Add L2 cache fields if available
            if has_l2_cache:
                fieldnames.extend(['l2_accesses', 'l2_hits', 'l2_misses', 'l2_hit_ratio'])
            
            # Add L3 cache fields if available
            if has_l3_cache:
                fieldnames.extend(['l3_accesses', 'l3_misses', 'l3_hit_ratio'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in memory_results:
                row = {
                    'benchmark': result['benchmark'],
                    'group': result['group'],
                    'iterations': result['iterations'],
                    'cycles': result['cycles'],
                    'instructions': result['instructions'],
                    'branch_misses': result.get('branch_misses', 'N/A'),
                    'cycles_per_inst': f"{result['cycles_per_inst']:.6f}",
                    'l1_loads': result.get('l1_loads', 'N/A'),
                    'l1_load_misses': result.get('l1_load_misses', 'N/A'),
                    'l1_load_hit_ratio': f"{result.get('l1_load_hit_ratio', 'N/A'):.6f}" if result.get('l1_load_hit_ratio') is not None else 'N/A'
                }
                
                # Add L1 fill fields only if available
                if has_l1_fills:
                    row.update({
                        'l1_fills': result.get('l1_fills', 'N/A')
                    })
                
                # Add L2 cache fields if available
                if has_l2_cache:
                    row.update({
                        'l2_accesses': result.get('l2_accesses', 'N/A'),
                        'l2_hits': result.get('l2_hits', 'N/A'),
                        'l2_misses': result.get('l2_misses', 'N/A'),
                        'l2_hit_ratio': f"{result.get('l2_hit_ratio', 'N/A'):.6f}" if result.get('l2_hit_ratio') is not None else 'N/A'
                    })
                
                # Add L3 cache fields if available
                if has_l3_cache:
                    row.update({
                        'l3_accesses': result.get('l3_accesses', 'N/A'),
                        'l3_misses': result.get('l3_misses', 'N/A'),
                        'l3_hit_ratio': f"{result.get('l3_hit_ratio', 'N/A'):.6f}" if result.get('l3_hit_ratio') is not None else 'N/A'
                    })
                
                writer.writerow(row)
        
        print(f"✓ Memory benchmark results saved to {csv_filename}")
        return csv_filename

    def run_latency_analysis(self, memory_csv_file):
        """Run memory latency analysis by calling the analyzer class directly."""
        try:
            print("\n" + "=" * 60)
            print("RUNNING MEMORY LATENCY ANALYSIS")
            print("=" * 60)

            analyzer = MemoryLatencyAnalyzer(verbose=self.verbose, iterations=self.iterations)

            # Load data
            if not analyzer.load_csv_files(memory_csv_file):
                return

            # Analyze latencies
            analyzer.analyze_all_groups()

            # Print results
            analyzer.print_summary()

            # Save results
            analyzer.save_latency_analysis()

            print("✓ Memory latency analysis completed")

        except Exception as e:
            print(f"✗ Error running latency analysis: {e}")
    
    def save_summary_to_csv(self, latency_results):
        """Save latency summary results to a CSV file."""
        if not latency_results:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"latency_summary_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['instruction_type', 'latency', 'translation_efficiency', 'latency_r_squared', 'efficiency_r_squared', 'benchmarks']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in latency_results:
                writer.writerow({
                    'instruction_type': result['group'],
                    'latency': f"{result['latency']:.6f}",
                    'translation_efficiency': f"{result['translation_efficiency']:.6f}",
                    'latency_r_squared': f"{result['latency_r_squared']:.6f}",
                    'efficiency_r_squared': f"{result['efficiency_r_squared']:.6f}",
                    'benchmarks': ", ".join(result['benchmarks'])
                })
        
        print(f"✓ Latency summary saved to {csv_filename}")
        return csv_filename

def check_permissions():
    """Check if script has proper permissions for accurate measurements."""
    if os.geteuid() == 0:  # Running as root
        print("✓ Script is running with sudo privileges")
        print("   This is recommended for accurate CPU performance measurements")
        print("   as it allows access to hardware performance counters")
        print()
        return True
    else:
        print("⚠ Warning: Script is not running with sudo privileges")
        print("   Without sudo, hardware performance counters are not accessible")
        print("   Solutions:")
        print("   1. Run with sudo: sudo python3 run_benchmarks.py (recommended)")
        print("   2. Lower perf paranoid level: sudo sh -c 'echo -1 > /proc/sys/kernel/perf_event_paranoid'")
        print("   3. Add user to perf group: sudo usermod -a -G perf $USER")
        print("   Note: Measurements will likely fail without proper permissions")
        print()
        return False

def main():
    """Main function."""

    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Run IR instruction performance benchmarks with detailed cache analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all benchmarks
  %(prog)s --verbose                          # Run all benchmarks with verbose output
  %(prog)s bench_memory_store-32KB-4         # Run specific benchmark
  %(prog)s --cpu-core 2 --iterations 50000000 bench_memory_store-32KB-4
  %(prog)s --verbose bench_memory_store-32KB-4 bench_memory_load-1MB
        """
    )
    
    # Add arguments
    parser.add_argument(
        'benchmarks',
        nargs='*',
        help='Specific benchmarks to run (default: run all available benchmarks)'
    )
    
    parser.add_argument(
        '--cpu-core',
        type=int,
        default=3,
        help='CPU core to pin benchmarks to (default: 3)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=100000000,
        help='Number of iterations per benchmark (default: 100000000)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output showing detailed metrics'
    )

    parser.add_argument(
        '--no-analyze-latency',
        dest='analyze_latency',
        action='store_false',
        help='Disable memory latency analysis after benchmarking (default: enabled)'
    )
    # Backend selection and DPA options
    parser.add_argument(
        '--backend',
        choices=['cpu', 'dpa'],
        default='cpu',
        help='Select benchmarking backend: cpu (perf) or dpa (DOCA Telemetry DPA)'
    )
    parser.add_argument(
        '--dpa-device',
        help='DOCA device identifier (e.g., pci=0000:06:00.0). If omitted, the first supported device is used'
    )
    parser.add_argument(
        '--dpa-sample-ms',
        type=int,
        default=1000,
        help='Sampling interval in milliseconds for DPA telemetry (default: 1000)'
    )
    parser.add_argument(
        '--dpa-thread-filter',
        help='Regex to include only matching DPA threads by name or ID when sampling'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.backend == 'cpu':
        # Check for proper permissions
        check_permissions()
        
        # Create and run benchmark runner
        runner = BenchmarkRunner(cpu_core=args.cpu_core, iterations=args.iterations, verbose=args.verbose)
        runner.analyze_latency = args.analyze_latency
        runner.setup_cpu()
        runner.run_benchmarks(args.benchmarks if args.benchmarks else None)
    else:
        # DPA backend
        try:
            from dpa_runner import DPATelemetryRunner
        except ImportError:
            print("✗ DPA backend not available: missing dpa_runner module")
            print("  Ensure the repository contains dpa_runner.py and required DOCA SDK components.")
            return 1

        dpa = DPATelemetryRunner(verbose=args.verbose)
        ok = dpa.run(device=args.dpa_device, sample_ms=args.dpa_sample_ms, thread_filter=args.dpa_thread_filter)
        if not ok:
            return 1

if __name__ == "__main__":
    main() 