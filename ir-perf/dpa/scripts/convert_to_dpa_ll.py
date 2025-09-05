#!/usr/bin/env python3
"""
Convert existing CPU-oriented IR benchmarks (bench_*.ll) into minimal
DPA-compatible LLVM IR modules with a __dpa_global__ thread entry.

This is an initial, conservative converter that does not splice the original
snippet body. It emits a steady-state loop and signals completion.

Inputs:
  --in-ll-dir   Directory containing bench_*.ll (default: build)
  --out-ll-dir  Output directory for converted LL (default: build/dpa_ll)

Outputs:
  <out-ll-dir>/<bench_name>.ll
"""

import argparse
import os
from pathlib import Path
import re


HEADER = "; Auto-generated DPA kernel IR\ntarget datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n32:64-S128\"\ntarget triple = \"riscv64-unknown-unknown-elf\"\n"


def sanitize_symbol(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def extract_bench_function(src_text: str) -> str | None:
    # Extract the full 'define void @bench_loop(i64 %N) { ... }' including body
    m = re.search(r"define\s+void\s+@bench_loop\s*\(i64\s+%N\)\s*\{([\s\S]*?)\}\s*\Z", src_text, re.MULTILINE)
    if not m:
        # Try a more general match to closing brace
        m = re.search(r"define\s+void\s+@bench_loop\s*\(i64\s+%N\)\s*\{([\s\S]*?)\}\s*", src_text, re.MULTILINE)
    return m.group(0) if m else None


def strip_sink_calls(ir_text: str) -> str:
    # Remove any lines that call the helper 'sink' function, with or without trailing comments
    ir_text = re.sub(r"^\s*call\s+void\s+@sink\([^\)]*\)\s*(;.*)?$", "", ir_text, flags=re.MULTILINE)
    # Also remove stray declare of sink if present
    ir_text = re.sub(r"^\s*declare\s+\w+\s+@sink\([^\)]*\)\s*$", "", ir_text, flags=re.MULTILINE)
    return ir_text


def rewrite_bench_loop_to_return_value(bench_ir: str) -> tuple[str, str | None]:
    """Rewrite bench_loop to return i64 value passed to sink(), removing sink and ret void.
    Returns (rewritten_ir, value_symbol_or_None).
    """
    # Find the value passed to sink
    m = re.search(r"call\s+void\s+@sink\s*\(\s*i64\s+([%A-Za-z0-9_\.]+)\s*\)", bench_ir)
    value_sym = m.group(1) if m else None
    # Remove sink call lines
    bench_ir2 = re.sub(r"^\s*call\s+void\s+@sink\([^\)]*\)\s*(;.*)?$", "", bench_ir, flags=re.MULTILINE)
    if value_sym:
        # Replace first 'ret void' with 'ret i64 <value_sym>'
        bench_ir2 = re.sub(r"\bret\s+void\b", f"ret i64 {value_sym}", bench_ir2, count=1)
    # Change function signature to return i64 and be dso_local
    bench_ir2 = re.sub(r"define\s+void\s+@bench_loop", "define dso_local i64 @bench_loop", bench_ir2, count=1)
    return bench_ir2, value_sym


def make_module_from_source(bench_name: str, src_text: str, loop_count: int = 10000000) -> tuple[str, str]:
    # Emit bench_loop and any auxiliary function definitions it depends on (from the same file).
    bench_ir = extract_bench_function(src_text)
    if not bench_ir:
        # Fallback bench_loop (returns a counter)
        body = (
            "\n"
            "define i64 @bench_loop(i64 noundef %N) {\n"
            "entry:\n"
            "  %i = alloca i64, align 8\n"
            "  store i64 0, ptr %i, align 8\n"
            "  br label %loop\n\n"
            "loop:\n"
            "  %v = load i64, ptr %i, align 8\n"
            "  %nv = add i64 %v, 1\n"
            "  store i64 %nv, ptr %i, align 8\n"
            f"  %cond = icmp ult i64 %nv, {loop_count}\n"
            "  br i1 %cond, label %loop, label %exit\n\n"
            "exit:\n"
            "  ret i64 %nv\n"
            "}\n"
        )
        return HEADER + body, "bench_loop"

    # Transform bench_loop: remove sink() calls and return the sink value
    bench_ir, _ret_sym = rewrite_bench_loop_to_return_value(bench_ir)

    # Collect all function definitions from src (auxiliaries), excluding bench_loop and sink
    func_def_pattern = re.compile(r"define\s+[^{]*@([A-Za-z0-9_\.\-]+)\s*\([^)]*\)\s*\{[\s\S]*?\}\s*", re.MULTILINE)
    aux_defs: list[str] = []
    for m in func_def_pattern.finditer(src_text):
        name = m.group(1)
        if name == 'bench_loop' or name == 'sink':
            continue
        aux_defs.append(m.group(0))

    # Remove sink declaration lines from source
    # We do not attempt to carry over other declares; if auxiliaries call externs, the original file will have declares which will be included below.
    declares = []
    for line in src_text.splitlines():
        if re.match(r"^\s*declare\s+", line) and ' @sink(' not in line:
            declares.append(line)

    parts = [HEADER]
    if declares:
        parts.append("\n".join(declares) + "\n\n")
    if aux_defs:
        parts.append("\n\n".join(aux_defs) + "\n\n")
    parts.append(bench_ir + "\n")
    module = "".join(parts)
    module = strip_sink_calls(module)
    return module, "bench_loop"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-ll-dir")
    ap.add_argument("--out-ll-dir")
    ap.add_argument("--in-ll")
    ap.add_argument("--out-ll")
    args = ap.parse_args()

    # Per-file mode
    if args.in_ll and args.out_ll:
        src = Path(args.in_ll)
        dst = Path(args.out_ll)
        dst.parent.mkdir(parents=True, exist_ok=True)
        bench_name = src.stem
        src_text = src.read_text()
        ll, _sym_fn = make_module_from_source(bench_name, src_text)
        dst.write_text(ll)
        print(f"Converted {src} -> {dst}")
        return 0

    # Batch mode (fallback)
    in_dir = Path(args.in_ll_dir or "build")
    out_dir = Path(args.out_ll_dir or "build/dpa_ll")
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = sorted([p for p in in_dir.glob("bench_*.ll") if p.is_file()])
    if not inputs:
        print(f"No input LL files found in {in_dir}")
        return 0

    generated = []
    for src in inputs:
        bench_name = src.stem
        src_text = src.read_text()
        ll, sym_fn = make_module_from_source(bench_name, src_text)
        dst = out_dir / f"{bench_name}.ll"
        dst.write_text(ll)
        generated.append((bench_name, sym_fn))

    with (out_dir / "benchlist.txt").open("w") as f:
        for bench, sym in generated:
            f.write(f"{bench} {sym}\n")
    print(f"Generated {len(generated)} DPA kernels in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


