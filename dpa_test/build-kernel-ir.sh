mkdir -p /tmp/dpacc_hAhezN
/opt/mellanox/doca/tools/dpa-clang -Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-unused-command-line-argument -Wno-gnu-line-marker -c kernel.ll -o /tmp/dpacc_hAhezN/kernel.bf3.o

# make a stub kernel.c for interface building
/opt/mellanox/doca/tools/ifgen kernel.c -devicecc-options="-Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ -Wno-deprecated-declarations -Werror -Wall -Wextra -W -I/opt/mellanox/doca/include/ -isystem /opt/mellanox/flexio/include -isystem /opt/mellanox/doca/include -isystem /opt/mellanox/doca/lib/x86_64-linux-gnu/dpa_llvm/lib/clang/18/include -Wno-pedantic " -output-path="/tmp/dpacc_hAhezN/" -source-file "kernel.c" --
/opt/mellanox/doca/tools/dpa-clang -Wno-attributes -ffreestanding -mcmodel=medany -mcpu=nv-dpa-bf3 -D__linux__ -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-pedantic -Wno-unused-parameter -Wno-unused-command-line-argument -I/opt/mellanox/doca/include/ -isystem /opt/mellanox/flexio/include -c /tmp/dpacc_hAhezN/kernel.dpa.device.c -o /tmp/dpacc_hAhezN/kernel.bf3.dpa.device.o
/opt/mellanox/doca/tools/dpa-clang -r -nostdlib -mcpu=nv-dpa-bf3 /tmp/dpacc_hAhezN/kernel.bf3.o /tmp/dpacc_hAhezN/kernel.bf3.dpa.device.o -o /tmp/dpacc_hAhezN/kernel.bf3.dpa.join.o
/opt/mellanox/doca/tools/dpa-fatbin --create --arch-member=nv-dpa-bf3,/tmp/dpacc_hAhezN/kernel.bf3.dpa.join.o -o /tmp/dpacc_hAhezN/kernel.fatobj.o
/opt/mellanox/doca/tools/objproc -emit-as-stub -array-prefix kernel -embed-as-obj /tmp/dpacc_hAhezN/kernel.fatobj.o -o /tmp/dpacc_hAhezN/kernel.stub.inc
gcc -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-attributes -Wno-pedantic -I/opt/mellanox/doca/include/ -I/opt/mellanox/flexio/include -Wno-unused-parameter -Wno-return-type -I /tmp/dpacc_hAhezN -D__DPA_OBJ_STUB_FILE__="\"kernel.stub.inc\"" /tmp/dpacc_hAhezN/kernel.dpa.host.c -c -o /tmp/dpacc_hAhezN/kernel.dpa.o
/opt/mellanox/doca/tools/objproc -extract-dev-obj /tmp/dpacc_hAhezN/kernel.dpa.o -out-dir=/tmp/dpacc_hAhezN
/opt/mellanox/doca/tools/dpa-clang -fPIE -nostdlib -z nognustack -z norelro -Wl,--no-rosegment -mcpu=nv-dpa-bf3 -static /tmp/dpacc_hAhezN/kernel.dpa.join.o  -T /opt/mellanox/doca/tools/dpa_llvm/ldscripts/dpa_linker.ld -Wl,-whole-archive -L/opt/mellanox/doca/tools/dpa_llvm/../ -ldoca_dpa_dev -ldoca_dpa_dev_comm -Wl,-no-whole-archive -L/opt/mellanox/flexio/lib/bf3 -Wl,--start-group -Wl,-whole-archive -lflexio_dev -Wl,-no-whole-archive -lflexio-libc -Wl,--end-group -lclang_rt.builtins-riscv64 -o /tmp/dpacc_hAhezN/device_exec.bf3
/opt/mellanox/doca/tools/dpa-fatbin --create --arch-member=nv-dpa-bf3,/tmp/dpacc_hAhezN/device_exec.bf3 -o /tmp/dpacc_hAhezN/device_exec.fatbin
/opt/mellanox/doca/tools/objproc -emit-as-stub -array-prefix dpa_hello_world_app /tmp/dpacc_hAhezN/device_exec.fatbin -o /tmp/dpacc_hAhezN/device_exec.stub.inc
/opt/mellanox/doca/tools/objproc -gen-meta-stub -dpa-app-name dpa_hello_world_app -L/opt/mellanox/doca/tools/dpa_llvm/../ -ldoca_dpa_dev -ldoca_dpa_dev_comm  -L/opt/mellanox/flexio/lib/bf3 -lflexio_dev /tmp/dpacc_hAhezN/kernel.dpa.o -o /tmp/dpacc_hAhezN/dpa_hello_world_app.meta.c
gcc -Wno-deprecated-declarations -Werror -Wall -Wextra -W -Wno-attributes -Wno-pedantic -I/opt/mellanox/doca/include/ -I/opt/mellanox/flexio/include -Wno-implicit-function-declaration -I /tmp/dpacc_hAhezN -D__DPA_EXEC_STUB_FILE__="\"device_exec.stub.inc\"" /tmp/dpacc_hAhezN/dpa_hello_world_app.meta.c -c -o /tmp/dpacc_hAhezN/dpa_hello_world_app.meta.o
objcopy --remove-section=.dpa_obj /tmp/dpacc_hAhezN/kernel.dpa.o 
gcc -r -nostdlib /tmp/dpacc_hAhezN/dpa_hello_world_app.meta.o /tmp/dpacc_hAhezN/kernel.dpa.o -o /tmp/dpacc_hAhezN/hostStubs.o
rm -f dpa_program.a
ar cr dpa_program.a /tmp/dpacc_hAhezN/hostStubs.o

