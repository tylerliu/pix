import argparse
import os
import shlex
import subprocess
import sys
import csv
import re
import json
import itertools
from datetime import datetime


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
    # Expect lines like: "Cycles per call: <float>" or "Cycles for <type> empty: <float>"
    match = re.search(r"Cycles (?:per call|for \w+ empty):\s*([0-9]+\.[0-9]+|[0-9]+)", stdout_text)
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


def run_benchmark(function_name: str, build_dir: str, prefix: str, env: dict[str, str] | None = None, case_info: str | None = None) -> tuple[int, float | None, dict, str, str]:
    exe_path = build_executable_path(build_dir, prefix, function_name)

    if not os.path.exists(exe_path):
        print(f"Executable not found: {exe_path}", file=sys.stderr)
        print("Make sure you have built the project with Meson before running this script.", file=sys.stderr)
        return 1

    cmd = [exe_path] + cmd_args

    case_suffix = f" ({case_info})" if case_info else ""
    print(f"\n--- Running benchmark for {function_name}{case_suffix} ---")
    print("Command:", " ".join(shlex.quote(part) for part in cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    except FileNotFoundError:
        print(f"Failed to execute: {exe_path} (file not found)", file=sys.stderr)
        return 1

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


if __name__ == '__main__':
    # Manually split sys.argv on '--' so that everything after it is passed to the executable
    parser = argparse.ArgumentParser(description='Run pre-built API benchmarks.')
    parser.add_argument('functions', nargs='*', help='Functions to benchmark (defaults to all discovered).')
    parser.add_argument('--build-dir', default='build', help='Meson build directory containing benchmark executables.')
    parser.add_argument('--prefix', default=None, help='Force a specific executable prefix (e.g., dpdk). If omitted, prefix is auto-detected.')
    parser.add_argument('--iterations', type=int, default=1000000, help='Number of iterations for benchmarks (default: 1000000)')
    parser.add_argument('--csv', default=None, help='Path to CSV file for results. If omitted, a timestamped file is created in the current directory.')

    args = parser.parse_args()

    # Determine prefixes
    if args.prefix:
        prefixes = [args.prefix]
    else:
        prefixes = discover_prefixes(args.build_dir)

    if not prefixes:
        print(f"No benchmark executables discovered in {args.build_dir}. Build the project first.", file=sys.stderr)
        sys.exit(1)

    # Sudo warning only (no elevation) if any dpdk/cryptodev prefix is present
    if hasattr(os, 'geteuid') and os.geteuid() != 0 and any(p in {'dpdk', 'cryptodev'} for p in prefixes):
        print("Warning: Not running as root. Many DPDK/cryptodev setups require root/sudo. This script will not elevate.", file=sys.stderr)

    exit_code = 0

    # CSV setup
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

    for prefix, func in benchmarks_to_run:
        benchmark_full_config = get_benchmark_config(full_config, prefix, func)
        params_dict = benchmark_full_config.get("params", {})
        eal_args = benchmark_full_config.get("eal_args", [])
        
        # Generate all combinations of parameters
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
            
            rc, cycles, metadata, _out, _err = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, env=os.environ.copy(), case_info=case_info)
            
            if cycles is not None:
                total_cycles = cycles * args.iterations
                # Merge metadata from benchmark with parameters
                metadata.update(metadata_params)
                metadata_json = json.dumps(metadata).replace('"', "'")
                csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
            if rc != 0:
                exit_code = rc

    csv_file.flush()
    csv_file.close()
    print(f"\n--- All benchmarks complete ---\nResults written to {csv_path}")
    sys.exit(exit_code)
