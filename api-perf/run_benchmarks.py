import argparse
import os
import shlex
import subprocess
import sys
import csv
import re
import json
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


def choose_prefix_for_function(build_dir: str, function_name: str, candidate_prefixes: list[str]) -> str | None:
    # Prefer dpdk if present and the executable exists; otherwise first prefix with a match
    for prefix in candidate_prefixes:
        exe = build_executable_path(build_dir, prefix, function_name)
        if os.path.exists(exe):
            return prefix
    return None


def _parse_cycles(stdout_text: str) -> float | None:
    # Expect lines like: "Cycles per call: <float>" or similar
    match = re.search(r"Cycles per call:\s*([0-9]+\.[0-9]+|[0-9]+)", stdout_text)
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


def run_benchmark(function_name: str, build_dir: str, prefix: str, exec_args: list[str], env: dict[str, str] | None = None, case_info: str | None = None) -> tuple[int, float | None, dict, str, str]:
    exe_path = build_executable_path(build_dir, prefix, function_name)

    if not os.path.exists(exe_path):
        print(f"Executable not found: {exe_path}", file=sys.stderr)
        print("Make sure you have built the project with Meson before running this script.", file=sys.stderr)
        return 1

    cmd = [exe_path] + exec_args

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
    argv = sys.argv[1:]
    exec_args: list[str] = []
    if '--' in argv:
        sep_index = argv.index('--')
        argv, exec_args = argv[:sep_index], argv[sep_index + 1:]

    parser = argparse.ArgumentParser(description='Run pre-built API benchmarks.')
    parser.add_argument('functions', nargs='*', help='Functions to benchmark (defaults to all discovered).')
    parser.add_argument('--build-dir', default='build', help='Meson build directory containing benchmark executables.')
    parser.add_argument('--prefix', default=None, help='Force a specific executable prefix (e.g., dpdk). If omitted, prefix is auto-detected.')
    parser.add_argument('--iterations', type=int, default=1000000, help='Number of iterations for benchmarks (default: 1000000)')
    parser.add_argument('--csv', default=None, help='Path to CSV file for results. If omitted, a timestamped file is created in the current directory.')

    args = parser.parse_args(argv)

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

    # Fixed cases for burst-based functions
    BURST_TEST_FUNCTIONS: set[str] = { 'rte_eth_tx_burst', 'rte_eth_rx_burst' }
    DEFAULT_BURST_CASES: list[int] = [1, 2, 8, 32]

    if len(args.functions) == 0:
        # Run all discovered, across all prefixes
        for prefix in prefixes:
            functions = discover_functions(args.build_dir, prefix)
            for func in functions:
                if func in BURST_TEST_FUNCTIONS:
                    for b in DEFAULT_BURST_CASES:
                        cmd_args = ['-b', str(b), '-i', str(args.iterations), '--'] + exec_args
                        rc, cycles, metadata, _out, _err = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, exec_args=cmd_args, env=os.environ.copy(), case_info=f"burst_size={b}")
                        if cycles is not None:
                            total_cycles = cycles * args.iterations
                            metadata_json = json.dumps(metadata).replace('"', "'")
                            csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                        if rc != 0:
                            exit_code = rc
                else:
                    cmd_args = ['-i', str(args.iterations), '--'] + exec_args
                    rc, cycles, metadata, _out, _err = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, exec_args=cmd_args, env=os.environ.copy())
                    if cycles is not None:
                        total_cycles = cycles * args.iterations
                        metadata_json = json.dumps(metadata).replace('"', "'")
                        csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                    if rc != 0:
                        exit_code = rc
    else:
        # Run specified functions, choosing best available prefix per function
        for func in args.functions:
            prefix = args.prefix or choose_prefix_for_function(args.build_dir, func, prefixes)
            if prefix is None:
                print(f"Executable not found for function '{func}' with any known prefix in {args.build_dir}.", file=sys.stderr)
                exit_code = 1
                continue
            if func in BURST_TEST_FUNCTIONS:
                for b in DEFAULT_BURST_CASES:
                    cmd_args = ['-b', str(b), '-i', str(args.iterations), '--'] + exec_args
                    rc, cycles, metadata, _out, _err = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, exec_args=cmd_args, env=os.environ.copy(), case_info=f"burst_size={b}")
                    if cycles is not None:
                        total_cycles = cycles * args.iterations
                        metadata_json = json.dumps(metadata).replace('"', "'")
                        csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                    if rc != 0:
                        exit_code = rc
            else:
                cmd_args = ['-i', str(args.iterations), '--'] + exec_args
                rc, cycles, metadata, _out, _err = run_benchmark(func, build_dir=args.build_dir, prefix=prefix, exec_args=cmd_args, env=os.environ.copy())
                if cycles is not None:
                    total_cycles = cycles * args.iterations
                    metadata_json = json.dumps(metadata).replace('"', "'")
                    csv_writer.writerow([func, prefix, args.iterations, total_cycles, metadata_json])
                if rc != 0:
                    exit_code = rc

    csv_file.flush()
    csv_file.close()
    print(f"\n--- All benchmarks complete ---\nResults written to {csv_path}")
    sys.exit(exit_code)