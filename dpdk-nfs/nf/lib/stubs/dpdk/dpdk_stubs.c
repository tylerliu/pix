#include <rte_mempool.h>
#include <rte_lcore.h>
#include <rte_per_lcore.h>
#include <rte_ethdev.h>
#include <rte_ether.h>
#include <rte_eal.h>
#include <rte_common.h>
#include <rte_config.h>
#include <klee/klee.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

// Define STUB_DPDK_DEVICES_COUNT if not already defined
#ifndef STUB_DPDK_DEVICES_COUNT
#define STUB_DPDK_DEVICES_COUNT 2
#endif

// Add missing global variables that KLEE needs
/* indirect jump table to support external memory pools. */
struct rte_mempool_ops_table rte_mempool_ops_table = {
	.num_ops = 0
};

// Add missing global variables
RTE_DEFINE_PER_LCORE(unsigned, _lcore_id);
RTE_DEFINE_PER_LCORE(int, _rte_errno);

unsigned rte_lcore_id(void) {
	return 0;
}

// Add missing function stubs
void __rte_panic(const char *funcname, const char *format, ...) {
    printf("__rte_panic: %s\n", funcname);
    klee_silent_exit(1);
}

int rte_eal_init(int argc, char *argv[]) 
{
	int index = 0;

	// Skip args until --
	while (strcmp("--", argv[index])) {
		index++;
	}

	return index;
}

void rte_ether_format_addr(char *buf, uint16_t size, const struct rte_ether_addr *eth_addr) {
    snprintf(buf, size, RTE_ETHER_ADDR_PRT_FMT,
        eth_addr->addr_bytes[0],
        eth_addr->addr_bytes[1],
        eth_addr->addr_bytes[2],
        eth_addr->addr_bytes[3],
        eth_addr->addr_bytes[4],
        eth_addr->addr_bytes[5]
    );
}

int rte_ether_unformat_addr(const char *str, struct rte_ether_addr *eth_addr) {
    int b0, b1, b2, b3, b4, b5;
    int ret = sscanf(str, RTE_ETHER_ADDR_PRT_FMT,
        &b0, &b1, &b2, &b3, &b4, &b5);
    eth_addr->addr_bytes[0] = (uint8_t)b0;
    eth_addr->addr_bytes[1] = (uint8_t)b1;
    eth_addr->addr_bytes[2] = (uint8_t)b2;
    eth_addr->addr_bytes[3] = (uint8_t)b3;
    eth_addr->addr_bytes[4] = (uint8_t)b4;
    eth_addr->addr_bytes[5] = (uint8_t)b5;
    return ret;
}

void rte_exit(int exit_code, const char *format, ...) {
    printf("rte_exit: %s\n", format);
    klee_silent_exit(exit_code);
}

struct rte_mempool *rte_pktmbuf_pool_create(const char *name, unsigned n,
                                            unsigned cache_size, uint16_t priv_size,
                                            uint16_t data_room_size, int socket_id) {
    return (struct rte_mempool*)0x12345678;
}

const char *rte_strerror(int errnum) {
    return "Unknown error";
}

// Additional missing functions

void rte_mbuf_sanity_check(const struct rte_mbuf* m, int is_header)
{
	klee_assert(m != NULL);
	klee_assert(is_header == 1);

	// TODO checks?
}