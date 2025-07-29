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
from datetime import datetime

class BenchmarkRunner:
    def __init__(self, cpu_core=3, iterations=100000000, verbose=False):
        self.cpu_core = cpu_core
        self.iterations = iterations
        self.verbose = verbose
        self.build_dir = Path("build")
        self.original_settings = {}
        self.setup_completed = False
        self.supported_commands = {}
        
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
        if not self.setup_completed:
            return
        
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
    
    def warn_perf_permissions(self):
        """Warn about perf permission issues."""
        if not self.check_perf_permissions():
            print("⚠ Warning: perf may require elevated permissions")
            print("   Try one of these solutions:")
            print("   1. Run with sudo: sudo python3 run_benchmarks.py")
            print("   2. Lower perf paranoid level: sudo sh -c 'echo -1 > /proc/sys/kernel/perf_event_paranoid'")
            print("   3. Add user to perf group: sudo usermod -a -G perf $USER")
            print("   Note: Using sudo may affect measurement accuracy")
            return False
        return True
    
    def run_perf_measurement(self, executable):
        """Run perf stat measurement on the executable."""
        if self.verbose:
            print(f"Measuring {executable}...")
        executable_path = self.build_dir / executable
        
        # Check perf permissions first
        if not self.warn_perf_permissions():
            if self.verbose:
                print("   Continuing anyway, but measurements may fail...")
        
        try:
            result = subprocess.run([
                "perf", "stat", "-e", "cycles,instructions,branch-misses",
                "taskset", "-c", str(self.cpu_core), str(executable_path), str(self.iterations)
            ], capture_output=True, text=True, check=True)
            return self.parse_perf_output(result.stderr)
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"✗ Perf measurement failed: {e}")
                print(f"Command: {' '.join(e.cmd)}")
                print(f"Error output: {e.stderr}")
            return None
    
    def parse_perf_output(self, output):
        """Parse perf stat output and extract metrics."""
        metrics = {}
        
        # Parse cycles
        cycles_match = re.search(r'(\d+(?:,\d+)*)\s+cycles', output)
        if cycles_match:
            cycles = int(cycles_match.group(1).replace(',', ''))
            metrics['cycles'] = cycles
        
        # Parse instructions
        insts_match = re.search(r'(\d+(?:,\d+)*)\s+instructions', output)
        if insts_match:
            instructions = int(insts_match.group(1).replace(',', ''))
            metrics['instructions'] = instructions
        
        # Parse branch misses
        branch_misses_match = re.search(r'(\d+(?:,\d+)*)\s+branch-misses', output)
        if branch_misses_match:
            branch_misses = int(branch_misses_match.group(1).replace(',', ''))
            metrics['branch_misses'] = branch_misses
        
        if 'cycles' in metrics and 'instructions' in metrics:
            metrics['cycles_per_inst'] = metrics['cycles'] / metrics['instructions']
        
        return metrics
    
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
        
        # Group benchmarks by instruction type
        benchmark_groups = self.group_benchmarks(benchmarks)
        
        all_results = []
        latency_results = []
        
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
                    continue
                
                # Measure
                result = self.run_perf_measurement(benchmark)
                if result:
                    result['benchmark'] = benchmark
                    result['group'] = group_name
                    group_results.append(result)
                    all_results.append(result)
                    
                    # Print results (only if verbose)
                    if self.verbose:
                        print(f"Results for {benchmark}:")
                        print(f"  Cycles: {result['cycles']:,}")
                        print(f"  Instructions: {result['instructions']:,}")
                        print(f"  Branch misses: {result.get('branch_misses', 'N/A')}")
                        print(f"  Cycles/instruction: {result['cycles_per_inst']:.3f}")
                    else:
                        print(" ✓")
            
            # Calculate latency for this group
            if len(group_results) >= 2:
                latency_result = self.calculate_latency(group_results)
                if latency_result:
                    latency_results.append(latency_result)
                    print(f"\nLatency calculation for {group_name}:")
                    print(f"  Estimated latency: {latency_result['latency']:.3f} cycles/instruction")
        
        # Print summary
        self.print_summary(latency_results)
        
        # Save detailed results to CSV
        if all_results:
            csv_file = self.save_results_to_csv(all_results)
            print(f"\nDetailed results saved to: {csv_file}")
    
    def group_benchmarks(self, benchmarks):
        """Group benchmarks by instruction type (e.g., add-imm, add-imm-2, add-imm-4)."""
        groups = {}
        
        for benchmark in benchmarks:
            # Extract base name (e.g., "add-imm" from "bench_arithmetic_add-imm-2")
            parts = benchmark.split('_')
            if len(parts) >= 3:
                base_name = parts[2]  # e.g., "add-imm"
                
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
            group.sort(key=lambda x: self.extract_instruction_count(x))
        
        return groups
    
    def extract_instruction_count(self, benchmark_name):
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
        """Calculate latency by comparing different instruction counts."""
        if len(group_results) < 2:
            return None
        
        # Sort by instruction count
        group_results.sort(key=lambda x: self.extract_instruction_count(x['benchmark']))
        
        # Calculate latency using linear regression
        instruction_counts = []
        cycles_per_inst = []
        
        for result in group_results:
            count = self.extract_instruction_count(result['benchmark'])
            instruction_counts.append(count)
            cycles_per_inst.append(result['cycles_per_inst'])
        
        # Calculate slope (latency per instruction)
        if len(instruction_counts) >= 2:
            # Simple linear regression: slope = (y2-y1)/(x2-x1)
            x1, y1 = instruction_counts[0], cycles_per_inst[0]
            x2, y2 = instruction_counts[-1], cycles_per_inst[-1]
            
            if x2 != x1:
                latency = (y2 - y1) / (x2 - x1)
            else:
                latency = 0
            
            return {
                'group': group_results[0]['group'],
                'latency': latency,
                'instruction_counts': instruction_counts,
                'cycles_per_inst': cycles_per_inst,
                'benchmarks': [r['benchmark'] for r in group_results]
            }
        
        return None
    
    def print_summary(self, results):
        """Print a summary table of latency results."""
        if not results:
            return
        
        print(f"\n{'='*80}")
        print("LATENCY SUMMARY")
        print(f"{'='*80}")
        print(f"{'Instruction Type':<25} {'Latency (cycles)':<15} {'Benchmarks':<30}")
        print("-" * 80)
        
        for result in results:
            instruction_type = result['group']
            latency = f"{result['latency']:.3f}"
            benchmarks = ", ".join(result['benchmarks'])
            
            print(f"{instruction_type:<25} {latency:<15} {benchmarks:<30}")
        
        print(f"\nNote: Latency is calculated as the difference in cycles/instruction")
        print(f"between different numbers of the same instruction.")
    
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

def check_sudo_usage():
    """Check if script is running with sudo and warn about it."""
    if os.geteuid() == 0:  # Running as root
        print("⚠ Warning: Script is running with sudo/root privileges")
        print("   This may affect measurement accuracy and is generally not recommended")
        print("   Consider using one of these alternatives instead:")
        print("   1. Lower perf paranoid level: sudo sh -c 'echo -1 > /proc/sys/kernel/perf_event_paranoid'")
        print("   2. Add user to perf group: sudo usermod -a -G perf $USER")
        print("   3. Use perf with user events only (may be less accurate)")
        print()
        return True
    return False

def main():
    """Main function."""
    import sys
    
    # Check for sudo usage
    check_sudo_usage()
    
    # Parse command line arguments
    cpu_core = 3
    iterations = 100000000
    specific_benchmarks = None
    verbose = False
    
    # Check for verbose flag
    if "--verbose" in sys.argv:
        verbose = True
        sys.argv.remove("--verbose")
    
    if len(sys.argv) > 1:
        try:
            cpu_core = int(sys.argv[1])
        except ValueError:
            print("Usage: python3 run_benchmarks.py [cpu_core] [iterations] [benchmark1] [benchmark2] ... [--verbose]")
            print("Example: python3 run_benchmarks.py 3 100000000 bench_arithmetic_add-imm --verbose")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            iterations = int(sys.argv[2])
        except ValueError:
            print("Usage: python3 run_benchmarks.py [cpu_core] [iterations] [benchmark1] [benchmark2] ... [--verbose]")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        specific_benchmarks = sys.argv[3:]
    
    # Create and run benchmark runner
    runner = BenchmarkRunner(cpu_core=cpu_core, iterations=iterations, verbose=verbose)
    runner.setup_cpu()
    runner.run_benchmarks(specific_benchmarks)

if __name__ == "__main__":
    main() 