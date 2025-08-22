#ifndef BENCHMARK_DRIVER_H
#define BENCHMARK_DRIVER_H

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mempool.h>

// Runtime-configurable parameters with sensible defaults
extern unsigned long long g_iterations; // iterations for the benchmark loop

extern struct rte_mempool *mbuf_pool;
extern struct rte_mbuf **bufs;

// Generic parameter retrieval
const char *get_benchmark_param(const char *key);

void init_dpdk(int argc, char **argv);
void cleanup_dpdk(void);

#endif // BENCHMARK_DRIVER_H
