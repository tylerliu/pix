#ifndef BENCHMARK_DRIVER_H
#define BENCHMARK_DRIVER_H

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mempool.h>

// Runtime-configurable parameters with sensible defaults
extern unsigned int g_burst_size;     // number of packets per burst for rx/tx APIs
extern unsigned long long g_iterations; // iterations for the benchmark loop
extern unsigned int g_payload_size;   // payload size in bytes for packet generation

extern struct rte_mempool *mbuf_pool;
extern struct rte_mbuf **bufs; // allocated at runtime to size g_burst_size

void init_dpdk(int argc, char **argv);
void cleanup_dpdk(void);

#endif // BENCHMARK_DRIVER_H
