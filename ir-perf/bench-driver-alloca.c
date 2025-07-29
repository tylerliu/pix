#include <stdio.h>
#include <stdlib.h>

extern void bench_loop(long N);

void sink(long x) {
    volatile long y = x;
    (void)y;
}

int main(int argc, char** argv) {
  long N = (argc>1 ? atol(argv[1]) : 1000LL);  // Much smaller default for alloca
  bench_loop(N);
  return 0;
} 