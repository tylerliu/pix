#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_compressdev.h>
#include <rte_vdev.h>

#include "driver/benchmark_driver.h"

// {{DPDK_HEADERS}}

static uint8_t cdev_id = 0;
static void *comp_private_xform;
static void *decomp_private_xform;
static struct rte_mempool *comp_op_pool;
static uint64_t total_poll_cycles = 0;
static bool vdev_initialized = false;

// Compression constants
#define MAX_COMPRESSED_SIZE 2048
#define COMPRESS_LEVEL 6
#define COMPRESS_WINDOW_SIZE 15

// Global xform used by benchmarks (device supports decompression only)
struct rte_comp_xform comp_xform = {
	.type = RTE_COMP_DECOMPRESS,
	.decompress = {
		.algo = RTE_COMP_ALGO_DEFLATE,
		.chksum = RTE_COMP_CHECKSUM_CRC32,
	}
};

void setup_compressdev() {
    // Check if compression devices are already available
    int num_comp_devices = rte_compressdev_count();
    
    // If no compression devices are available, initialize compress_zlib virtual device
    if (num_comp_devices < 1) {
        printf("No compression devices found, initializing compress_zlib virtual device...\n");
        if (rte_vdev_init("compress_zlib", NULL) < 0) {
            rte_exit(EXIT_FAILURE, "Failed to initialize compress_zlib virtual device\n");
        }
        vdev_initialized = true;
        
        // Check again after initialization
        num_comp_devices = rte_compressdev_count();
        if (num_comp_devices < 1) {
            rte_exit(EXIT_FAILURE, "No compression devices available even after initializing virtual device\n");
        }
    } else {
        printf("Found %d existing compression device(s), using existing devices\n", num_comp_devices);
    }

    // Get compression device info
    struct rte_compressdev_info cdev_info;
    rte_compressdev_info_get(cdev_id, &cdev_info);

    // Create compression operation pool
    comp_op_pool = rte_comp_op_pool_create("comp_op_pool", 
                                         8192, 128, 0, rte_socket_id());
    if (comp_op_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create compression operation pool\n");
    }

    // Note: Private xforms are allocated directly by the device, no separate pool needed

    // Configure compression device
    struct rte_compressdev_config config = {
        .nb_queue_pairs = 1,
        .socket_id = rte_socket_id(),
    };
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
    if (rte_compressdev_configure(cdev_id, &config) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to configure compressdev %u\n", cdev_id);
    }
#pragma GCC diagnostic pop

    // Setup queue pair with maximum inflight operations
    if (rte_compressdev_queue_pair_setup(cdev_id, 0, 128, rte_socket_id()) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to setup queue pair\n");
    }

    // Start compression device
    if (rte_compressdev_start(cdev_id) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to start compression device\n");
    }

    // Create private xforms
    if (rte_compressdev_private_xform_create(cdev_id, &comp_xform, &decomp_private_xform) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to create decompression private xform\n");
    }
}

void setup_benchmark() {
    // {{BENCHMARK_SETUP}}
}

void run_benchmark() {
    uint64_t start, end;
    total_poll_cycles = 0;  // Reset for this benchmark run
    volatile uint64_t result = 0;

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

void teardown_compressdev() {
    // Free private xforms
    if (comp_private_xform != NULL) {
        rte_compressdev_private_xform_free(cdev_id, comp_private_xform);
        comp_private_xform = NULL;
    }
    if (decomp_private_xform != NULL) {
        rte_compressdev_private_xform_free(cdev_id, decomp_private_xform);
        decomp_private_xform = NULL;
    }
    
    // Stop and close compression device
    rte_compressdev_stop(cdev_id);
    rte_compressdev_close(cdev_id);

    // Free compression operation pool
    if (comp_op_pool != NULL) {
        rte_mempool_free(comp_op_pool);
        comp_op_pool = NULL;
    }
    
    // Uninitialize virtual device only if we initialized it
    if (vdev_initialized) {
        rte_vdev_uninit("compress_zlib");
        vdev_initialized = false;
    }
}

int main(int argc, char **argv) {
    init_dpdk(argc, argv);
    setup_compressdev();
    setup_benchmark();
    run_benchmark();
    teardown_benchmark();
    teardown_compressdev();
    cleanup_dpdk();
    return 0;
}
