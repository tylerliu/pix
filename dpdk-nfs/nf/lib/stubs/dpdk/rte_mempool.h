// used with VeriFast, can't use #pragma
#ifndef RTE_MEMPOOL_H
#define RTE_MEMPOOL_H

#include <stdint.h>

#define RTE_MEMZONE_NAMESIZE 32
#define RTE_MEMPOOL_MAX_OPS_IDX 16  /**< Max registered ops structs */

struct rte_mempool {
	char name[RTE_MEMZONE_NAMESIZE];
//	union {
//		void *pool_data;
		uint64_t pool_id;
//	};
	void *pool_config;
//	const struct rte_memzone *mz;
	unsigned int flags;
	int socket_id;
	uint32_t size;
	uint32_t cache_size;
	uint32_t elt_size;
	uint32_t header_size;
	uint32_t trailer_size;
	unsigned private_data_size;
	int32_t ops_index;
//	struct rte_mempool_cache *local_cache;
	uint32_t populated_size;
//	struct rte_mempool_objhdr_list elt_list;
	uint32_t nb_mem_chunks;
//	struct rte_mempool_memhdr_list mem_list;
};

/**
 * Structure storing the table of registered ops structs, each of which contain
 * the function pointers for the mempool ops functions.
 * Each process has its own storage for this ops struct array so that
 * the mempools can be shared across primary and secondary processes.
 * The indices used to access the array are valid across processes, whereas
 * any function pointers stored directly in the mempool struct would not be.
 * This results in us simply having "ops_index" in the mempool struct.
 */
 struct rte_mempool_ops_table {
	uint32_t num_ops;      /**< Number of used ops structs in the table. */
	/**
	 * Storage for all possible ops structs.
	 * TODO: this is a hack to make VeriFast happy, we should use a real array
	 */
	int ops[RTE_MEMPOOL_MAX_OPS_IDX];
}
#ifdef _NO_VERIFAST_
  __rte_cache_aligned;
#else//_NO_VERIFAST_
;
#endif//_NO_VERIFAST_

/* indirect jump table to support external memory pools. */
extern struct rte_mempool_ops_table rte_mempool_ops_table;

#endif
