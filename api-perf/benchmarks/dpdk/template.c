#include <stdio.h>
#include <stdlib.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>

#include "driver/benchmark_driver.h"

// {{DPDK_HEADERS}}

static uint16_t port_id = 0;

struct rte_mempool *mbuf_pool;
struct rte_mbuf **bufs;

void setup_ethernet_device() {
    if (rte_eth_dev_count_avail() == 0)
        rte_exit(EXIT_FAILURE, "No available Ethernet devices\n");

    // Create mbuf pool for Ethernet RX/TX
    if (mbuf_pool == NULL) {
        mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", 8192, 256, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
        if (mbuf_pool == NULL)
            rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");
    }

    // Allocate bufs with a default size. Benchmarks that need a different size can re-allocate it.
    bufs = calloc(32, sizeof(struct rte_mbuf *));
    if (bufs == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot allocate bufs array for default burst size 32\n");
    }

    struct rte_eth_conf port_conf = {
        .rxmode = {
            .mq_mode = RTE_ETH_MQ_RX_NONE,
            .mtu = 1518,
        },
        .txmode = {
            .mq_mode = RTE_ETH_MQ_TX_NONE,
        },
    };

    int ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot configure device: err=%d, port=%u\n", ret, port_id);
    }

    ret = rte_eth_rx_queue_setup(port_id, 0, 1024, rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "rte_eth_rx_queue_setup: err=%d, port=%u\n", ret, port_id);
    }

    ret = rte_eth_tx_queue_setup(port_id, 0, 1024, rte_eth_dev_socket_id(port_id), NULL);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "rte_eth_tx_queue_setup: err=%d, port=%u\n", ret, port_id);
    }

    ret = rte_eth_dev_start(port_id);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "rte_eth_dev_start: err=%d, port=%u\n", ret, port_id);
    }
}

void setup_benchmark() {
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

    uint64_t total_cycles = end - start;
    printf("Total cycles: %lu\n", (unsigned long)total_cycles);
}

void teardown_benchmark() {
    // {{BENCHMARK_TEARDOWN}}
}

void teardown_ethernet_device() {
    if (bufs) {
        free(bufs);
        bufs = NULL;
    }

    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
}

int main(int argc, char **argv) {
    init_dpdk(argc, argv);
    setup_ethernet_device();
    setup_benchmark();
    run_benchmark();
    teardown_benchmark();
    teardown_ethernet_device();
    cleanup_dpdk();
    return 0;
}
