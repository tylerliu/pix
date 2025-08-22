#include "benchmark_driver.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>

// Defaults, override via command line args
unsigned int g_burst_size = 32;
unsigned long long g_iterations = 1000000ULL;
unsigned int g_payload_size = 64;  // Default payload size (64 bytes minimum)

struct rte_mempool *mbuf_pool;
struct rte_mbuf **bufs;

static void parse_command_line_args(int argc, char **argv) {
    // Find the separator '--' to split benchmark args from DPDK EAL args
    int separator_index = -1;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--") == 0) {
            separator_index = i;
            break;
        }
    }
    
    // Parse benchmark arguments (before '--')
    int benchmark_argc = (separator_index > 0) ? separator_index : argc;
    for (int i = 1; i < benchmark_argc; i++) {
        if (strcmp(argv[i], "-b") == 0 && i + 1 < benchmark_argc) {
            g_burst_size = (unsigned int)strtoul(argv[i + 1], NULL, 10);
            if (g_burst_size == 0 || g_burst_size > 65535) {
                g_burst_size = 32; // fallback to default
            }
            i++; // skip the value
        } else if (strcmp(argv[i], "-i") == 0 && i + 1 < benchmark_argc) {
            g_iterations = strtoull(argv[i + 1], NULL, 10);
            if (g_iterations == 0) {
                g_iterations = 1000000ULL; // fallback to default
            }
            i++; // skip the value
        } else if (strcmp(argv[i], "-p") == 0 && i + 1 < benchmark_argc) {
            g_payload_size = (unsigned int)strtoul(argv[i + 1], NULL, 10);
            if (g_payload_size < 8) {
                g_payload_size = 64; // fallback to default minimum
            }
            i++; // skip the value
        }
    }
    
    // If we found a separator, we need to adjust argc/argv for DPDK EAL
    // to only see the arguments after '--'
    if (separator_index > 0) {
        // Move DPDK EAL arguments to the beginning of argv
        int dpdk_argc = argc - separator_index - 1;
        char **dpdk_argv = &argv[separator_index + 1];
        
        // Call DPDK EAL with only the arguments after '--'
        int ret = rte_eal_init(dpdk_argc, dpdk_argv);
        if (ret < 0) {
            rte_exit(EXIT_FAILURE, "Error with EAL initialization\n");
        }
    } else {
        // No separator, pass all arguments to DPDK EAL
        int ret = rte_eal_init(argc, argv);
        if (ret < 0) {
            rte_exit(EXIT_FAILURE, "Error with EAL initialization\n");
        }
    }
}

void init_dpdk(int argc, char **argv) {
    // Parse command line arguments and initialize DPDK EAL
    parse_command_line_args(argc, argv);

    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", 8191, 250, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    if (mbuf_pool == NULL)
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");

    uint16_t port_id = 0;
    if (rte_eth_dev_count_avail() == 0)
        rte_exit(EXIT_FAILURE, "No available Ethernet devices\n");

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

    // Allocate per-burst mbuf array based on g_burst_size
    bufs = calloc(g_burst_size, sizeof(struct rte_mbuf *));
    if (bufs == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot allocate bufs array for burst size %u\n", g_burst_size);
    }
}

void cleanup_dpdk(void) {
    if (bufs) {
        free(bufs);
        bufs = NULL;
    }
    rte_eal_cleanup();
}
