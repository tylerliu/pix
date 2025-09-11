#include <stdio.h>
#include <stdlib.h>
#include <rte_eal.h>
#include <rte_regexdev.h>

#include "driver/benchmark_driver.h"

// {{DPDK_HEADERS}}

static uint64_t total_poll_cycles = 0;

static uint8_t rdev_id = 0;

static void setup_regexdev() {
    int count = rte_regexdev_count();
    if (count <= 0) {
        rte_exit(EXIT_FAILURE, "No regex devices available\n");
    }

    struct rte_regexdev_info info;
    rte_regexdev_info_get(rdev_id, &info);

    struct rte_regexdev_config dev_conf = {
        .nb_queue_pairs = 1,
        .nb_max_matches = 1,
        .rule_db_len = 0,
        .rule_db = NULL,
    };
    if (rte_regexdev_configure(rdev_id, &dev_conf) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to configure regexdev %u\n", rdev_id);
    }

    struct rte_regexdev_qp_conf qp_conf = {
        .nb_desc = 128,
        .qp_conf_flags = 0,
    };
    if (rte_regexdev_queue_pair_setup(rdev_id, 0, &qp_conf) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to setup regex queue pair\n");
    }

    if (rte_regexdev_start(rdev_id) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to start regex device\n");
    }
}

void setup_benchmark() {
    // {{BENCHMARK_SETUP}}
}

void run_benchmark(void) {
    uint64_t start, end;
    total_poll_cycles = 0;  // Reset for this benchmark run

    start = rte_rdtsc();
    for (unsigned long long i = 0; i < g_iterations; ++i) {
        // {{BENCHMARK_LOOP}}
        uint64_t start_rdtsc = rte_rdtsc();
        rte_pause(); // a pause to not overload the core. 
        total_poll_cycles += rte_rdtsc() - start_rdtsc;
    }
    end = rte_rdtsc();

    uint64_t total_cycles = end - start - total_poll_cycles;
    printf("Total cycles: %lu\n", (unsigned long)total_cycles);
}

void teardown_benchmark() {
    // {{BENCHMARK_TEARDOWN}}
}

static void teardown_regexdev() {
    rte_regexdev_stop(rdev_id);
    rte_regexdev_close(rdev_id);
}

int main(int argc, char **argv) {
    init_dpdk(argc, argv);
    setup_regexdev();
    setup_benchmark();
    run_benchmark();
    teardown_benchmark();
    teardown_regexdev();
    cleanup_dpdk();
    return 0;
}


