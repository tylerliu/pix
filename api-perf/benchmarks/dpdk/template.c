#include <stdio.h>
#include <stdlib.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>

#include "driver/benchmark_driver.h"

// {{DPDK_HEADERS}}

void setup_benchmark() {
    if (rte_pktmbuf_alloc_bulk(mbuf_pool, bufs, g_burst_size) != 0) {
        rte_exit(EXIT_FAILURE, "Cannot allocate mbufs\n");
    }
    // {{BENCHMARK_SETUP}}
}

void run_benchmark() {
    uint64_t start, end;
    volatile uint64_t result = 0;

    start = rte_rdtsc();
    for (unsigned long long i = 0; i < g_iterations; ++i) {
        // {{BENCHMARK_LOOP}}
    }
    end = rte_rdtsc();

    printf("Cycles per call: %f\n", (double)(end - start) / (double)g_iterations);
}

void teardown_benchmark() {
    // {{BENCHMARK_TEARDOWN}}
}

int main(int argc, char **argv) {
    init_dpdk(argc, argv);
    setup_benchmark();
    run_benchmark();
    teardown_benchmark();
    cleanup_dpdk();
    return 0;
}
