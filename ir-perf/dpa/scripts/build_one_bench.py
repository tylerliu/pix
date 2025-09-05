#!/usr/bin/env python3
"""
Build one DPA benchmark from a converted LLVM IR file using dpacc.

Inputs:
  --ll         Path to converted DPA kernel .ll (from dpa_ll/)
  --out-dir    Output directory for artifacts (archive .a)
  --app-prefix Prefix for dpacc --app-name (default: dpa_ir_bench_app)

Output:
  <out-dir>/<bench>.a
"""

import argparse
import os
import shlex
import subprocess
from pathlib import Path


DOCA_INC = "/opt/mellanox/doca/include/"
FLEXIO_INC = "/opt/mellanox/flexio/include"
DPA_LLVM_CLANG_INC = "/opt/mellanox/doca/lib/x86_64-linux-gnu/dpa_llvm/lib/clang/18/include"
DPA_CLANG = "/opt/mellanox/doca/tools/dpa-clang"
DPA_FATBIN = "/opt/mellanox/doca/tools/dpa-fatbin"
OBJPROC = "/opt/mellanox/doca/tools/objproc"


def run(cmd: str):
    print(cmd)
    subprocess.check_call(cmd, shell=True)


def symify(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ll", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--app-prefix", default="dpa_ir_bench_app")
    args = ap.parse_args()

    ll_path = Path(args.ll)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bench_name = ll_path.stem
    out_a = out_dir / f"{bench_name}.a"
    app_name = f"{args.app_prefix}_{bench_name}"
    tmp = out_dir / f"tmp_{bench_name}"
    tmp.mkdir(parents=True, exist_ok=True)

    # 1) Create a minimal stub for interface generation
    stub_c = tmp / "stub.c"
    stub_c.write_text(
        """
#include <stdint.h>
#include <doca_dpa_dev.h>

/* Only an RPC is needed; match converted IR function name and signature. */
__dpa_rpc__ uint64_t bench_loop(uint64_t iterations) {
  return iterations;
}
"""
    )

    # 2) Generate device/host interface code from stub
    # Run ifgen in the tmp directory so -source-file and relative includes resolve correctly
    ifgen_cmd = (
        f"cd {shlex.quote(str(tmp))} && /opt/mellanox/doca/tools/ifgen stub.c "
        f"-devicecc-options=\"-Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-implicit-function-declaration -I{DOCA_INC} -isystem {FLEXIO_INC} -isystem {DOCA_INC} -isystem {DPA_LLVM_CLANG_INC} -Wno-pedantic \" "
        f"-output-path=\"{shlex.quote(str(tmp))}/\" -source-file \"stub.c\" --"
    )
    run(ifgen_cmd)

    # 3) Compile converted device IR to object
    dev_obj = tmp / f"{bench_name}.bf3.o"
    run(
        f"{DPA_CLANG} -Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ "
        f"-Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-unused-command-line-argument -Wno-gnu-line-marker "
        f"-c {shlex.quote(str(ll_path))} -o {shlex.quote(str(dev_obj))}"
    )

    # 4) Compile device interface to object
    dev_if_c = tmp / "stub.dpa.device.c"
    dev_if_obj = tmp / f"{bench_name}.bf3.dpa.device.o"
    run(
        f"{DPA_CLANG} -Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ "
        f"-Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-pedantic -Wno-unused-parameter -Wno-unused-command-line-argument "
        f"-I{DOCA_INC} -isystem {FLEXIO_INC} -c {shlex.quote(str(dev_if_c))} -o {shlex.quote(str(dev_if_obj))}"
    )

    # 5) Link device objects
    join_obj = tmp / f"{bench_name}.bf3.dpa.join.o"
    run(f"{DPA_CLANG} -r -nostdlib -mcpu=nv-dpa-bf3 {shlex.quote(str(dev_obj))} {shlex.quote(str(dev_if_obj))} -o {shlex.quote(str(join_obj))}")

    # 6) Build device exec and fatbin
    device_exec = tmp / "device_exec.bf3"
    run(
        f"{DPA_CLANG} -fPIE -nostdlib -z nognustack -z norelro -Wl,--no-rosegment -mcpu=nv-dpa-bf3 -static {shlex.quote(str(join_obj))} "
        f"-T /opt/mellanox/doca/tools/dpa_llvm/ldscripts/dpa_linker.ld -Wl,-whole-archive -L/opt/mellanox/doca/tools/dpa_llvm/../ -ldoca_dpa_dev -ldoca_dpa_dev_comm "
        f"-Wl,-no-whole-archive -L/opt/mellanox/flexio/lib/bf3 -Wl,--start-group -Wl,-whole-archive -lflexio_dev -Wl,-no-whole-archive -lflexio-libc -Wl,--end-group -lclang_rt.builtins-riscv64 -o {shlex.quote(str(device_exec))}"
    )
    fatbin = tmp / "device_exec.fatbin"
    run(f"{DPA_FATBIN} --create --arch-member=nv-dpa-bf3,{shlex.quote(str(device_exec))} -o {shlex.quote(str(fatbin))}")

    # 7) Emit exec stub
    exec_stub = tmp / "device_exec.stub.inc"
    run(f"{OBJPROC} -emit-as-stub -array-prefix {app_name} {shlex.quote(str(fatbin))} -o {shlex.quote(str(exec_stub))}")

    # 8) Generate meta stub referencing host interface
    host_if_o = tmp / "stub.dpa.o"
    # compile host interface using the exec stub
    host_if_c = tmp / "stub.dpa.host.c"
    meta_c = tmp / f"{app_name}.meta.c"
    run(
        f"gcc -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-attributes -Wno-pedantic "
        f"-Wno-unused-parameter -Wno-return-type -Wno-error=unused-parameter -Wno-error=return-type "
        f"-I{DOCA_INC} -I{FLEXIO_INC} -I {shlex.quote(str(tmp))} "
        f"-D__DPA_OBJ_STUB_FILE__='\"device_exec.stub.inc\"' "
        f"{shlex.quote(str(host_if_c))} -c -o {shlex.quote(str(host_if_o))}"
    )
    run(f"{OBJPROC} -gen-meta-stub -dpa-app-name {app_name} -L/opt/mellanox/doca/tools/dpa_llvm/../ -ldoca_dpa_dev -ldoca_dpa_dev_comm  -L/opt/mellanox/flexio/lib/bf3 -lflexio_dev {shlex.quote(str(host_if_o))} -o {shlex.quote(str(meta_c))}")

    # 9) Compile meta and link host stubs
    meta_o = tmp / f"{app_name}.meta.o"
    run(
        f"gcc -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-attributes -Wno-pedantic "
        f"-I{DOCA_INC} -I{FLEXIO_INC} -Wno-implicit-function-declaration -I {shlex.quote(str(tmp))} "
        f"-D__DPA_EXEC_STUB_FILE__='\"device_exec.stub.inc\"' "
        f"{shlex.quote(str(meta_c))} -c -o {shlex.quote(str(meta_o))}"
    )
    # Remove .dpa_obj then link -r
    run(f"objcopy --remove-section=.dpa_obj {shlex.quote(str(host_if_o))}")
    host_stubs = tmp / "hostStubs.o"
    run(f"gcc -r -nostdlib {shlex.quote(str(meta_o))} {shlex.quote(str(host_if_o))} -o {shlex.quote(str(host_stubs))}")

    # 10) Archive
    run(f"rm -f {shlex.quote(str(out_a))}")
    run(f"ar cr {shlex.quote(str(out_a))} {shlex.quote(str(host_stubs))}")
    (out_dir / f"{bench_name}.ok").write_text("ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


