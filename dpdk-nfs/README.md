# Organization

Subdirectories have their own README files.

* `nf` - contains the set of NFs written using DPDK that we extracted performance interfaces for.
* `perf-contracts` - contains the manually extracted contracts for the common data structures used by all NFs.

# Usage

## Compile dependcies
Follow the root README for build script. 

## get dependency environment variables
```bash
. ~/paths.sh
```

## Compiling performance contract library
In `perf-contracts` folder, run `make`:
```bash
make
```

## Run klee on NFs. 
