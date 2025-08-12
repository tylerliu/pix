#ifndef BENCHMARK_DRIVER_H
#define BENCHMARK_DRIVER_H

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mempool.h>

#define BURST_SIZE 32
#define ITERATIONS 1000000

extern struct rte_mempool *mbuf_pool;
extern struct rte_mbuf *bufs[BURST_SIZE];

void init_dpdk(int argc, char **argv);
void cleanup_dpdk(void);

#endif // BENCHMARK_DRIVER_H
