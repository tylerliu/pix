#!/usr/bin/env python3
"""
End-to-end orchestrator for DPA benchmarks:
 - Convert existing bench_*.ll to DPA kernels
 - Build per-bench dpacc archives and the host runner
 - Launch a bench and collect metrics via CLI (dpa-ps, dpa-statistics)
 - Save results to CSV
"""

import argparse
import csv
import os
import re
import shlex
import subprocess
import time
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DPA_LL = BUILD / "dpa_ll"
DPA_ART = BUILD / "dpa_artifacts"


def run(cmd: str, check: bool = True, capture: bool = False):
    if capture:
        return subprocess.run(cmd, shell=True, text=True, capture_output=True)
    else:
        print(cmd)
        return subprocess.run(cmd, shell=True, check=check)


def ensure_conversion():
    (BUILD).mkdir(exist_ok=True)
    script = ROOT / 'dpa/scripts/convert_to_dpa_ll.py'
    run(f"{shlex.quote(sys.executable)} {shlex.quote(str(script))} --in-ll-dir {shlex.quote(str(BUILD))} --out-ll-dir {shlex.quote(str(DPA_LL))}")


def ensure_build():
    (DPA_ART).mkdir(parents=True, exist_ok=True)
    # Build per-bench archive via build_one_bench.py then link a host runner
    b1 = ROOT / 'dpa/scripts/build_one_bench.py'
    host_src = ROOT / 'dpa/host/dpa_bench_host.c'

    # Load bench symbol overrides if available
    bl = DPA_LL / 'benchlist.txt'
    bench_syms = {}
    if bl.exists():
        for line in bl.read_text().splitlines():
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                bench_syms[parts[0]] = parts[1]

    for ll in sorted(DPA_LL.glob('bench_*.ll')):
        bench = ll.stem
        # 1) Build dpacc archive for this bench
        run(f"{shlex.quote(sys.executable)} {shlex.quote(str(b1))} --ll {shlex.quote(str(ll))} --out-dir {shlex.quote(str(DPA_ART))}")

        # 2) Generate minimal bench index for this bench
        idx = DPA_ART / f"bench_index_{bench}.c"
        sym = bench_syms.get(bench, f"{bench}_thread")
        with idx.open('w') as f:
            f.write('#include <stddef.h>\n')
            f.write('#include <doca_dpa.h>\n\n')
            f.write(f"extern doca_dpa_func_t {sym}_kernel;\n")
            f.write('struct bench_entry { const char *name; doca_dpa_func_t *func; };\n')
            f.write('struct bench_entry g_bench_index[] = {\n')
            f.write(f"  {{ \"{bench}\", &{sym}_kernel }},\n")
            f.write('};\n')
            f.write('size_t g_bench_index_len = 1;\n')

        # 3) Link host runner for this bench
        out_exe = DPA_ART / f"bench_host_{bench}"
        archive = DPA_ART / f"{bench}.a"
        DOCA_INC = '/opt/mellanox/doca/include/'
        DOCA_LIB = '/opt/mellanox/doca/lib/x86_64-linux-gnu/'
        FLEXIO_LIB_BF3 = '/opt/mellanox/flexio/lib/bf3'
        app_sym = f"dpa_ir_bench_app_{bench}"
        cmd = (
            f"gcc {shlex.quote(str(host_src))} {shlex.quote(str(idx))} -o {shlex.quote(str(out_exe))} "
            f"{shlex.quote(str(archive))} -DAPP_SYM={app_sym} "
            f"-I{shlex.quote(DOCA_INC)} -DDOCA_ALLOW_EXPERIMENTAL_API "
            f"-L{shlex.quote(DOCA_LIB)} -ldoca_dpa -ldoca_common "
            f"-L{shlex.quote(FLEXIO_LIB_BF3)}/.. -lflexio -lstdc++ -libverbs -lmlx5"
        )
        run(cmd)


def list_benches():
    return sorted(p.stem for p in DPA_LL.glob("bench_*.ll"))


def start_bench(bench: str):
    exe = DPA_ART / f"bench_host_{bench}"
    cmd = f"sudo {shlex.quote(str(exe))} --bench {shlex.quote(bench)}"
    # Start in background
    return subprocess.Popen(cmd, shell=True)


def dpa_ps(device: str) -> str:
    res = run(f"sudo dpa-ps -d {shlex.quote(device)}", capture=True)
    return res.stdout


def extract_pid(output: str, app_name: str = "dpa_ir_bench_app"):
    # Heuristic: find line containing app name; earlier columns hold ProcessID in hex
    for line in output.splitlines():
        if app_name in line:
            # Split by whitespace and return the first hex-like token
            parts = line.strip().split()
            for tok in parts:
                if re.fullmatch(r"[0-9A-Fa-f]+", tok):
                    return tok
    return None


def dpa_statistics_collect(device: str, pid_hex: str, sample_ms: int) -> str:
    res = run(f"sudo dpa-statistics collect -d {shlex.quote(device)} -p {shlex.quote(pid_hex)} -r -t {sample_ms}", capture=True)
    return res.stdout + res.stderr


def parse_statistics_output(text: str):
    rows = []
    # Expect lines like: ThreadID Cycles Instruction Time Executions Thread Name
    pat = re.compile(r"^\s*([0-9A-Fa-fx]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+(\S+)")
    current_proc = None
    current_name = None
    for line in text.splitlines():
        line = line.rstrip()
        if "ProcessID" in line and "Process Name" in line:
            continue
        mproc = re.match(r"^\s*([0-9A-Fa-fx]+)\s+(.+)$", line)
        if mproc and "PROCESS" in mproc.group(2):
            current_proc = mproc.group(1)
            current_name = mproc.group(2).strip()
            continue
        m = pat.match(line)
        if m:
            rows.append({
                "process_id": current_proc,
                "process_name": current_name,
                "thread_id": m.group(1),
                "cycles": int(m.group(2)),
                "instructions": int(m.group(3)),
                "time_ticks": int(m.group(4)),
                "executions": int(m.group(5)),
                "thread_name": m.group(6),
            })
    return rows


def save_csv(rows, out_csv: Path):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "bench", "process_id", "process_name", "thread_id", "cycles",
            "instructions", "time_ticks", "executions", "thread_name",
            "cycles_per_instruction",
        ])
        w.writeheader()
        for r in rows:
            cpi = (r["cycles"] / r["instructions"]) if r.get("instructions") else 0.0
            r2 = dict(r)
            r2["cycles_per_instruction"] = f"{cpi:.6f}"
            w.writerow(r2)


def run_one(device: str, bench: str, sample_ms: int, thread_filter: str | None, out_csv: Path):
    proc = start_bench(bench)
    # Give time for DPA app registration
    time.sleep(0.4)
    ps = dpa_ps(device)
    pid_hex = extract_pid(ps)
    if not pid_hex:
        proc.terminate()
        raise RuntimeError("Could not find DPA process id via dpa-ps")
    stats = dpa_statistics_collect(device, pid_hex, sample_ms)
    rows = parse_statistics_output(stats)
    # Annotate with bench and optionally filter
    rows = [dict({"bench": bench}, **r) for r in rows if (not thread_filter or re.search(thread_filter, r["thread_name"]))]
    save_csv(rows, out_csv)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True, help="DPA device (e.g., mlx5_0)")
    ap.add_argument("--sample-ms", type=int, default=1000)
    ap.add_argument("--thread-filter")
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--benches", nargs="*")
    args = ap.parse_args()

    ensure_conversion()
    ensure_build()
    if args.prepare_only:
        return 0

    benches = args.benches or list_benches()
    all_rows = []
    for b in benches:
        out_csv = BUILD / f"dpa_results_{b}.csv"
        rows = run_one(args.device, b, args.sample_ms, args.thread_filter, out_csv)
        all_rows.extend(rows)
        print(f"Collected: {b} -> {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


