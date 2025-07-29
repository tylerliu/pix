#include <stdio.h>
#include <stdlib.h>

extern void bench_loop(long N);

void sink(long x) {
    volatile long y = x;
    (void)y;
}

int main(int argc, char** argv) {
  long N = (argc>1 ? atol(argv[1]) : 100000000LL);
  bench_loop(N);
  return 0;
}