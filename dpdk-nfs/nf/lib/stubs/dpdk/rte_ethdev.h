#pragma once

#include <inttypes.h>
#include <stdbool.h>

#include "lib/stubs/core_stub.h"

#include <klee/klee.h>

// TX configuration default values 
#define IXGBE_DEFAULT_TX_FREE_THRESH  32
#define IXGBE_DEFAULT_TX_PTHRESH      32
#define IXGBE_DEFAULT_TX_HTHRESH      0
#define IXGBE_DEFAULT_TX_WTHRESH      0
#define IXGBE_DEFAULT_TX_RSBIT_THRESH 32

#define ETH_TXQ_FLAGS_NOMULTSEGS 0x0001 /**< nb_segs=1 for all mbufs */
#define ETH_TXQ_FLAGS_NOVLANOFFL 0x0100 /**< disable VLAN offload */
#define ETH_TXQ_FLAGS_NOXSUMSCTP 0x0200 /**< disable SCTP checksum offload */
#define ETH_TXQ_FLAGS_NOXSUMUDP  0x0400 /**< disable UDP checksum offload */
#define ETH_TXQ_FLAGS_NOXSUMTCP  0x0800 /**< disable TCP checksum offload */
#define ETH_TXQ_FLAGS_NOOFFLOADS \
		(ETH_TXQ_FLAGS_NOVLANOFFL | ETH_TXQ_FLAGS_NOXSUMSCTP | \
		 ETH_TXQ_FLAGS_NOXSUMUDP  | ETH_TXQ_FLAGS_NOXSUMTCP)

#ifdef STUB_DEVICES_COUNT
#define STUB_DPDK_DEVICES_COUNT STUB_DEVICES_COUNT
#else
#define STUB_DPDK_DEVICES_COUNT 2
#endif


struct rte_eth_link {
	uint32_t link_speed;
	uint16_t link_duplex  : 1;
	uint16_t link_autoneg : 1;
	uint16_t link_status  : 1;
};

/**
 * A structure used to configure the ring threshold registers of an RX/TX
 * queue for an Ethernet port.
 */
struct rte_eth_thresh {
	uint8_t pthresh; /**< Ring prefetch threshold. */
	uint8_t hthresh; /**< Ring host threshold. */
	uint8_t wthresh; /**< Ring writeback threshold. */
};

struct rte_eth_conf { /* Nothing */ };
struct rte_eth_rxconf {
	uint16_t rx_free_thresh;
	// we don't care about other members
};
/**
 * A structure used to configure a TX ring of an Ethernet port.
 */
struct rte_eth_txconf {
	struct rte_eth_thresh tx_thresh; /**< TX ring threshold registers. */
	uint16_t tx_rs_thresh; /**< Drives the setting of RS bit on TXDs. */
	uint16_t tx_free_thresh; /**< Start freeing TX buffers if there are
				      less free descriptors than this value. */

	uint32_t txq_flags; /**< Set flags for the Tx queue */
	uint8_t tx_deferred_start; /**< Do not start queue with rte_eth_dev_start(). */
	/**
	 * Per-queue Tx offloads to be set  using DEV_TX_OFFLOAD_* flags.
	 * Only offloads set on tx_queue_offload_capa or tx_offload_capa
	 * fields on rte_eth_dev_info structure are allowed to be set.
	 */
	uint64_t offloads;
};


// Sanity checks
// Documentation of rte_ethdev indicates the configure/tx/rx/started order
static bool devices_configured[STUB_DPDK_DEVICES_COUNT];
static bool devices_tx_setup[STUB_DPDK_DEVICES_COUNT];
static bool devices_rx_setup[STUB_DPDK_DEVICES_COUNT];
static bool devices_started[STUB_DPDK_DEVICES_COUNT];
static bool devices_promiscuous[STUB_DPDK_DEVICES_COUNT];

// To allocate mbufs
static struct rte_mempool* devices_rx_mempool[STUB_DPDK_DEVICES_COUNT];


uint16_t rte_eth_dev_count_avail(void);

int rte_eth_dev_configure(uint16_t port_id, uint16_t nb_rx_queue, uint16_t nb_tx_queue, const struct rte_eth_conf* eth_conf);

int rte_eth_tx_queue_setup(uint16_t port_id, uint16_t tx_queue_id,
			uint16_t nb_tx_desc, unsigned int socket_id,
			const struct rte_eth_txconf* tx_conf);

int rte_eth_rx_queue_setup(uint16_t port_id, uint16_t rx_queue_id, uint16_t nb_rx_desc,
			unsigned int socket_id, const struct rte_eth_rxconf *rx_conf,
			struct rte_mempool *mb_pool);

int rte_eth_dev_start(uint16_t port_id);

void rte_eth_promiscuous_enable(uint16_t port_id);

int rte_eth_promiscuous_get(uint16_t port_id);

int rte_eth_dev_socket_id(uint16_t port_id);

void rte_eth_macaddr_get(uint16_t port_id, struct rte_ether_addr *mac_addr);

uint16_t rte_eth_rx_burst(uint16_t port_id, uint16_t queue_id,
		 struct rte_mbuf **rx_pkts, const uint16_t nb_pkts);

uint16_t rte_eth_tx_burst(uint16_t port_id, uint16_t queue_id,
		 struct rte_mbuf **tx_pkts, uint16_t nb_pkts);
