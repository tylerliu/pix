import argparse
import os
import shlex
import subprocess
import sys
import csv
import re
import json
import itertools
import signal
import atexit
from datetime import datetime


class BenchmarkRunner:
    def __init__(self, cpu_core=3, verbose=False):
        self.cpu_core = cpu_core
        self.verbose = verbose
        self.original_settings = {}
        self.setup_completed = False
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
        supported_commands = self.check_cpupower_support()
        
        # Capture current settings first
        self.get_current_settings()
        
        # Print current settings before changing
        print(f"Current CPU {self.cpu_core} settings:")
        if 'governor' in self.original_settings:
            print(f"  Governor: {self.original_settings['governor']}")
        print()
        
        # Set CPU governor to performance (if supported)
        if supported_commands.get('frequency-set', False):
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
        if supported_commands.get('idle-set', False):
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
        if 'governor' in self.original_settings:
            try:
                subprocess.run([
                    "sudo", "cpupower", "-c", str(self.cpu_core), "frequency-set",
                    "-g", self.original_settings['governor']
                ], check=True, capture_output=True)
                print(f"✓ Restored governor to {self.original_settings['governor']}")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Warning: Could not restore governor: {e}")
        
        # Re-enable CPU idle states
        try:
            subprocess.run([
                "sudo", "cpupower", "-c", str(self.cpu_core), "idle-set", "-e", "0"
            ], check=True, capture_output=True)
            print("✓ Re-enabled CPU idle states")
        except subprocess.CalledProcessError:
            pass  # Ignore if not supported
        
        print("✓ CPU settings restored")
    
    def warm_up(self, exe_path, cmd_args):
        """Run executable once to warm up caches."""
        if self.verbose:
            print(f"Warming up {exe_path}...")
        try:
            # Create warm-up command with all the same parameters but fewer iterations
            warm_up_args = []
            i = 0
            while i < len(cmd_args):
                if cmd_args[i] == "-i" and i + 1 < len(cmd_args):
                    # Replace iteration count with 10000 for warm-up
                    warm_up_args.extend(["-i", "10000"])
                    i += 2  # Skip both "-i" and the iteration count
                else:
                    warm_up_args.append(cmd_args[i])
                    i += 1
            
            subprocess.run([
                "taskset", "-c", str(self.cpu_core),
                exe_path
            ] + warm_up_args, check=True, capture_output=True)
            if self.verbose:
                print("✓ Warm-up completed")
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"✗ Warm-up failed: {e}")
            return False
        return True


def detect_and_explain_common_errors(stdout_text: str, stderr_text: str) -> None:
    combined = f"{stdout_text}\n{stderr_text}"
    lower = combined.lower()

    if ("operation not permitted" in lower or "permission denied" in lower) and hasattr(os, 'geteuid') and os.geteuid() != 0:
        print("Hint: Permission issue detected. Many DPDK/DOCA setups require root. Re-run with sudo (warning only; this script does not elevate).", file=sys.stderr)

    if "huge" in lower and "page" in lower:
        print("Hint: Hugepage-related error. Ensure hugepages are configured and available for your platform.", file=sys.stderr)

    if "eal:" in lower and ("cannot allocate memory" in lower or "could not reserve memory" in lower or "no available hugepages" in lower):
        print("Hint: EAL memory reservation failed, commonly due to missing/insufficient hugepages.", file=sys.stderr)

    if "telemetry: no legacy callbacks, legacy socket not created" in lower:
        print("Note: Telemetry legacy socket is disabled. This message is informational and usually harmless.", file=sys.stderr)

    if "cannot configure ethdev port" in lower and "null config" in lower:
        print("Hint: Port configuration called with NULL config. Update the benchmark driver to provide a valid rte_eth_conf.", file=sys.stderr)

    if ("cannot configure device:" in lower and "err=-22" in lower) or "cause: cannot configure device" in lower:
        print("Hint: Device configuration returned -EINVAL. Ensure the device is present/bound and queue settings are valid; verify EAL device args (e.g., -a, --vdev).", file=sys.stderr)


def build_executable_path(build_dir: str, prefix: str, function_name: str) -> str:
    # Executables are named like: <prefix>_<function>, e.g., dpdk_rte_eth_rx_burst
    exe_name = f"{prefix}_{function_name}"
    return os.path.join(build_dir, exe_name)


def discover_functions(build_dir: str, prefix: str) -> list[str]:
    if not os.path.isdir(build_dir):
        return []
    discovered: list[str] = []
    try:
        for entry in os.listdir(build_dir):
            if entry.startswith('.'):
                continue
            if not entry.startswith(f"{prefix}_"):
                continue
            full = os.path.join(build_dir, entry)
            if not os.path.isfile(full):
                continue
            if not os.access(full, os.X_OK):
                continue
            func = entry[len(prefix) + 1 :]
            if func:
                discovered.append(func)
    except FileNotFoundError:
        return []

    # Run 'empty' first if present
    discovered_sorted = sorted([f for f in discovered if f != 'empty'])
    if 'empty' in discovered:
        return ['empty'] + discovered_sorted
    return discovered_sorted


def discover_prefixes(build_dir: str) -> list[str]:
    if not os.path.isdir(build_dir):
        return []
    prefixes: set[str] = set()
    try:
        for entry in os.listdir(build_dir):
            if entry.startswith('.'):
                continue
            if '_' not in entry:
                continue
            full = os.path.join(build_dir, entry)
            if not os.path.isfile(full):
                continue
            if not os.access(full, os.X_OK):
                continue
            prefix = entry.split('_', 1)[0]
            if prefix:
                prefixes.add(prefix)
    except FileNotFoundError:
        return []
    # Prefer dpdk first if present
    sorted_prefixes = sorted(prefixes)
    if 'dpdk' in prefixes:
        sorted_prefixes = ['dpdk'] + [p for p in sorted_prefixes if p != 'dpdk']
    return sorted_prefixes

def choose_prefix_for_function(build_dir: str, function_name: str, candidate_prefixes: list[str]) -> str | None:
    # Prefer dpdk if present and the executable exists; otherwise first prefix with a match
    for prefix in candidate_prefixes:
        exe = build_executable_path(build_dir, prefix, function_name)
        if os.path.exists(exe):
            return prefix
    return None

def get_benchmark_config(full_config, prefix, func):
    template_config = full_config.get("templates", {}).get(prefix, {})
    benchmark_config = full_config.get("benchmarks", {}).get(func, {})

    # Deep merge benchmark config into template config
    final_config = template_config.copy()
    for key, value in benchmark_config.items():
        if isinstance(value, dict) and key in final_config and isinstance(final_config[key], dict):
            final_config[key].update(value)
        else:
            final_config[key] = value
    return final_config


def _parse_cycles(stdout_text: str) -> float | None:
    # Expect lines like: "Total cycles: <integer>" or "Cycles for <type> empty: <float>"
    match = re.search(r"(?:Total cycles|Cycles for \w+ empty):\s*([0-9]+(?:\.[0-9]+)?)", stdout_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def _parse_metadata(stdout_text: str) -> dict:
    # Look for lines like: "metadata: {'key': value, ...}"
    match = re.search(r"metadata:\s*(\{.*\})", stdout_text)
    if match:
        try:
            # Replace single quotes with double quotes for valid JSON
            json_str = match.group(1).replace("'", '"')
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return {}
    return {}


def run_benchmark(function_name: str, build_dir: str, prefix: str, runner: BenchmarkRunner, cmd_args: list[str], env: dict[str, str] | None = None, case_info: str | None = None, dry_run: bool = False) -> tuple[int, float | None, dict, str, str]:
    exe_path = build_executable_path(build_dir, prefix, function_name)

    if not os.path.exists(exe_path):
        print(f"Executable not found: {exe_path}", file=sys.stderr)
        print("Make sure you have built the project with Meson before running this script.", file=sys.stderr)
        return 1, None, {}, "", ""

    # Warm up the executable first (skip in dry-run mode)
    if not dry_run and not runner.warm_up(exe_path, cmd_args):
        print(f"Warning: Warm-up failed for {function_name}", file=sys.stderr)

    # Use taskset to pin to specific CPU core for consistent measurements
    cmd = ["taskset", "-c", str(runner.cpu_core), exe_path] + cmd_args

    case_suffix = f" ({case_info})" if case_info else ""
    print(f"\n--- Running benchmark for {function_name}{case_suffix} ---")
    print("Command:", " ".join(shlex.quote(part) for part in cmd))

    if dry_run:
        print("DRY RUN: Would execute the above command")
        return 0, None, {}, "", ""

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    except FileNotFoundError:
        print(f"Failed to execute: {exe_path} (file not found)", file=sys.stderr)
        return 1, None, {}, "", ""

    if result.returncode != 0:
        print("Error running benchmark:", file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        detect_and_explain_common_errors(result.stdout or "", result.stderr or "")
        return result.returncode, None, {}, result.stdout, result.stderr
    else:
        print(result.stdout.strip())
        cycles = _parse_cycles(result.stdout or "")
        metadata = _parse_metadata(result.stdout or "")
        return 0, cycles, metadata, result.stdout, result.stderr


def check_permissions():
    """Check if script has proper permissions for accurate measurements."""
    if hasattr(os, 'geteuid') and os.geteuid() == 0:  # Running as root
        print("✓ Script is running with sudo privileges")
        print("   This is recommended for accurate DPDK measurements")
        print("   as it allows access to hardware resources and hugepages")
        print()
        return True
    else:
        print("⚠ Warning: Script is not running with sudo privileges")
        print("   Many DPDK setups require root/sudo for:")
        print("   - Hugepage allocation")
        print("   - Device binding")
        print("   - CPU frequency control")
        print("   Solutions:")
        print("   1. Run with sudo: sudo python3 run_benchmarks.py (recommended)")
        print("   2. Ensure hugepages are pre-allocated")
        print("   3. Pre-bind devices to DPDK drivers")
        print("   Note: Some measurements may fail without proper permissions")
        print()
        return False


if __name__ == '__main__':
    # Manually split sys.argv on '--' so that everything after it is passed to the executable
    parser = argparse.ArgumentParser(
        description='Run pre-built API benchmarks with CPU optimizations for accurate measurements.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all benchmarks with optimizations
  %(prog)s --verbose                          # Run with detailed output
  %(prog)s --cpu-core 2 --iterations 5000000 # Use specific CPU core and iterations
  %(prog)s rte_eth_rx_burst                   # Run specific function
  %(prog)s --dry-run                          # Show commands without executing them

Optimizations applied:
  - CPU governor set to performance mode
  - CPU idle states disabled during benchmarking
  - Process pinned to specific CPU core using taskset
  - Warm-up runs to ensure consistent cache state
  - Proper cleanup on interruption (Ctrl+C)
  - Permission checks for DPDK requirements
        """
    )
    parser.add_argument('functions', nargs='*', help='Functions to benchmark (defaults to all discovered).')
    parser.add_argument('--build-dir', default='build', help='Meson build directory containing benchmark executables.')
    parser.add_argument('--prefix', default=None, help='Force a specific executable prefix (e.g., dpdk). If omitted, prefix is auto-detected.')
    parser.add_argument('-i', '--iterations', type=int, default=1000000, help='Number of iterations for benchmarks (default: 1000000)')
    parser.add_argument('--csv', default=None, help='Path to CSV file for results. If omitted, a timestamped file is created in the current directory.')
    parser.add_argument('--cpu-core', type=int, default=3, help='CPU core to pin benchmarks to (default: 3)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output showing detailed setup and warm-up information')
    parser.add_argument('--dry-run', action='store_true', help='Show commands that would be executed without actually running them')

    args = parser.parse_args()

    # Check permissions first
    check_permissions()

    # Create benchmark runner
    runner = BenchmarkRunner(cpu_core=args.cpu_core, verbose=args.verbose)
    
    # Set up CPU for optimal benchmarking
    # Set up CPU for benchmarking (skip in dry-run mode)
    if not args.dry_run:
        runner.setup_cpu()

    # Determine prefixes
    if args.prefix:
        prefixes = [args.prefix]
    else:
        prefixes = discover_prefixes(args.build_dir)

    if not prefixes:
        print(f"No benchmark executables discovered in {args.build_dir}. Build the project first.", file=sys.stderr)
        sys.exit(1)

    # Sudo warning only (no elevation) if any dpdk/cryptodev prefix is present
    if hasattr(os, 'geteuid') and os.geteuid() != 0 and any(p in {'dpdk', 'cryptodev', 'cryptodev_wait'} for p in prefixes):
        print("Warning: Not running as root. Many DPDK/cryptodev setups require root/sudo. This script will not elevate.", file=sys.stderr)

    exit_code = 0

    # CSV setup (skip in dry-run mode)
    csv_file = None
    csv_writer = None
    if not args.dry_run:
        csv_path = args.csv
        if not csv_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_path = f"api_perf_results_{timestamp}.csv"
        csv_file = open(csv_path, mode='w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['function', 'prefix', 'iterations', 'total_cycles', 'metadata'])

    # Load benchmark cases from JSON
    with open('benchmark_cases.json', 'r') as f:
        full_config = json.load(f)
    
    benchmark_cases = full_config["benchmarks"]

    benchmarks_to_run = []
    if len(args.functions) == 0:
        # Run all discovered, across all prefixes
        for prefix in prefixes:
            functions = discover_functions(args.build_dir, prefix)
            for func in functions:
                benchmarks_to_run.append((prefix, func))
    else:
        # Run specified functions, choosing best available prefix per function
        for func in args.functions:
            prefix = args.prefix or choose_prefix_for_function(args.build_dir, func, prefixes)
            if prefix is None:
                print(f"Executable not found for function '{func}' with any known prefix in {args.build_dir}.", file=sys.stderr)
                exit_code = 1
                continue
            benchmarks_to_run.append((prefix, func))

    # First, run empty benchmarks to get baseline cycles
    empty_cycles = {}
    for prefix in prefixes:
        if 'empty' in discover_functions(args.build_dir, prefix):
            benchmark_full_config = get_benchmark_config(full_config, prefix, 'empty')
            eal_args = benchmark_full_config.get("eal_args", [])
            benchmark_args = ['-i', str(args.iterations)]
            cmd_args = eal_args + ['--'] + benchmark_args
            
            rc, cycles, metadata, _out, _err = run_benchmark('empty', build_dir=args.build_dir, prefix=prefix, runner=runner, cmd_args=cmd_args, env=os.environ.copy(), case_info="Empty baseline", dry_run=args.dry_run)
            if cycles is not None:
                empty_cycles[prefix] = cycles
                print(f"Empty benchmark for {prefix}: {cycles} cycles")
            if rc != 0:
                exit_code = rc

    # Now run all other benchmarks
    for prefix, func in benchmarks_to_run:
        if func == 'empty':  # Skip empty benchmarks as they were already run
            continue
            
        benchmark_full_config = get_benchmark_config(full_config, prefix, func)
        params_dict = benchmark_full_config.get("params", {})
        grouped_params = benchmark_full_config.get("grouped_params", {})
        eal_args = benchmark_full_config.get("eal_args", [])
        
        # Generate parameter combinations
        if grouped_params:
            # Handle grouped parameters
            param_keys = list(params_dict.keys())
            param_values = [params_dict[k] for k in param_keys]
            
            # Generate combinations for each group
            for group_name, group_list in grouped_params.items():
                for group_item in group_list:
                    # Combine regular parameters with grouped parameters
                    for combo in itertools.product(*param_values):
                        # Build benchmark (post --) args: params then iterations
                        benchmark_args: list[str] = []
                        case_info_parts = []
                        metadata_params = {}
                        
                        # Add regular parameters
                        for i, key in enumerate(param_keys):
                            benchmark_args.extend([f"--{key}", str(combo[i])])
                            case_info_parts.append(f"{key}={combo[i]}")
                            metadata_params[key] = combo[i]
                        
                        # Add grouped parameters
                        for key, value in group_item.items():
                            if value is not None:  # Skip null values
                                benchmark_args.extend([f"--{key}", str(value)])
                                case_info_parts.append(f"{key}={value}")
                                metadata_params[key] = value
                        
                        benchmark_args.extend(['-i', str(args.iterations)])

                        # Full command: EAL args first, then '--', then benchmark args
                        cmd_args = eal_args + ['--'] + benchmark_args
                        case_info = ", ".join(case_info_parts) if case_info_parts else "Default"
                        
                        # Set up environment
                        env = os.environ.copy()
                        
                        rc, cycles, metadata, stdout, stderr = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, runner=runner, cmd_args=cmd_args, env=env, case_info=case_info, dry_run=args.dry_run)
                        
                        if cycles is not None:
                            total_cycles = cycles  # cycles is already total cycles now
                            
                            # Calculate and display cycles per call if empty benchmark data is available
                            if prefix in empty_cycles and func != 'empty':
                                empty_cycles_for_prefix = empty_cycles[prefix]
                                if total_cycles > empty_cycles_for_prefix:
                                    net_cycles = total_cycles - empty_cycles_for_prefix
                                    cycles_per_call = net_cycles / args.iterations
                                    print(f"  → Cycles per call (net): {cycles_per_call:.2f}")
                            
                            # Merge metadata from benchmark with parameters
                            metadata.update(metadata_params)
                            if csv_writer:
                                metadata_json = json.dumps(metadata).replace('"', "'")
                                csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                        if rc != 0:
                            exit_code = rc
        else:
            # Handle regular parameters (existing logic)
            param_keys = list(params_dict.keys())
            param_values = [params_dict[k] for k in param_keys]
            
            for combo in itertools.product(*param_values):
                # Build benchmark (post --) args: params then iterations
                benchmark_args: list[str] = []
                case_info_parts = []
                metadata_params = {}
                for i, key in enumerate(param_keys):
                    benchmark_args.extend([f"--{key}", str(combo[i])])
                    case_info_parts.append(f"{key}={combo[i]}")
                    metadata_params[key] = combo[i]
                benchmark_args.extend(['-i', str(args.iterations)])

                # Full command: EAL args first, then '--', then benchmark args
                cmd_args = eal_args + ['--'] + benchmark_args
                case_info = ", ".join(case_info_parts) if case_info_parts else "Default"
                
                # Set up environment
                env = os.environ.copy()
                
                rc, cycles, metadata, stdout, stderr = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, runner=runner, cmd_args=cmd_args, env=env, case_info=case_info, dry_run=args.dry_run)
                
                if cycles is not None:
                    total_cycles = cycles  # cycles is already total cycles now
                    
                    # Calculate and display cycles per call if empty benchmark data is available
                    if prefix in empty_cycles and func != 'empty':
                        empty_cycles_for_prefix = empty_cycles[prefix]
                        if total_cycles > empty_cycles_for_prefix:
                            net_cycles = total_cycles - empty_cycles_for_prefix
                            cycles_per_call = net_cycles / args.iterations
                            print(f"  → Cycles per call (net): {cycles_per_call:.2f}")
                    
                    # Merge metadata from benchmark with parameters
                    metadata.update(metadata_params)
                    if csv_writer:
                        metadata_json = json.dumps(metadata).replace('"', "'")
                        csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                if rc != 0:
                    exit_code = rc

    if csv_file:
        csv_file.flush()
        csv_file.close()
        print(f"\n--- All benchmarks complete ---\nResults written to {csv_path}")
    else:
        print(f"\n--- Dry run complete ---\nNo results file created (dry-run mode)")
    sys.exit(exit_code)
