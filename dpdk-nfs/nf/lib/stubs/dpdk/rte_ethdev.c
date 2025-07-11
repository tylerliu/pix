#include "rte_ethdev.h"

uint16_t rte_eth_dev_count_avail(void)
{
    return STUB_DPDK_DEVICES_COUNT;
}

int rte_eth_dev_configure(uint16_t port_id, uint16_t nb_rx_queue, uint16_t nb_tx_queue, const struct rte_eth_conf* eth_conf)
{
    klee_assert(port_id < STUB_DPDK_DEVICES_COUNT);
    klee_assert(!devices_configured[port_id]);
    klee_assert(nb_rx_queue == 1); // we only support that
    klee_assert(nb_tx_queue == 1); // same
	// TODO somehow semantically check eth_conf?

    devices_configured[port_id] = true;
    return 0;
}

int rte_eth_tx_queue_setup(uint16_t port_id, uint16_t tx_queue_id,
            uint16_t nb_tx_desc, unsigned int socket_id,
            const struct rte_eth_txconf* tx_conf)
{
    klee_assert(devices_configured[port_id]);
    klee_assert(!devices_tx_setup[port_id]);
    klee_assert(tx_queue_id == 0); // we only support that
    klee_assert(socket_id == 0); // same
    if (tx_conf != NULL ) {
        klee_assert(tx_conf->tx_thresh.pthresh == IXGBE_DEFAULT_TX_PTHRESH);
        klee_assert(tx_conf->tx_thresh.hthresh == IXGBE_DEFAULT_TX_HTHRESH);
        klee_assert(tx_conf->tx_thresh.wthresh == IXGBE_DEFAULT_TX_WTHRESH);
        klee_assert(tx_conf->tx_free_thresh == 1);
        klee_assert(tx_conf->tx_rs_thresh == 1);
        klee_assert(tx_conf->txq_flags == 
                            (ETH_TXQ_FLAGS_NOMULTSEGS | ETH_TXQ_FLAGS_NOOFFLOADS));
    }

    devices_tx_setup[port_id] = true;
    return 0;
}

int rte_eth_rx_queue_setup(uint16_t port_id, uint16_t rx_queue_id, uint16_t nb_rx_desc,
            unsigned int socket_id, const struct rte_eth_rxconf *rx_conf,
            struct rte_mempool *mb_pool)
{
    klee_assert(devices_tx_setup[port_id]);
    klee_assert(!devices_rx_setup[port_id]);
    klee_assert(rx_queue_id == 0); // we only support that
    klee_assert(socket_id == 0); // same
    klee_assert(mb_pool != NULL);
    // TODO semantic checks for rx_conf? since we need it for the hardware verif

    devices_rx_setup[port_id] = true;
    devices_rx_mempool[port_id] = mb_pool;
    return 0;
}

int rte_eth_dev_start(uint16_t port_id)
{
    klee_assert(devices_rx_setup[port_id]);
    klee_assert(!devices_started[port_id]);

    devices_started[port_id] = true;
    return 0;
}

void rte_eth_promiscuous_enable(uint16_t port_id)
{
    klee_assert(!devices_promiscuous[port_id]);
    devices_promiscuous[port_id] = true;
}

int rte_eth_promiscuous_get(uint16_t port_id)
{
    return devices_promiscuous[port_id] ? 1 : 0;
}

int rte_eth_dev_socket_id(uint16_t port_id)
{
    klee_assert(port_id < STUB_DPDK_DEVICES_COUNT);

    return 0;
}

void rte_eth_macaddr_get(uint16_t port_id, struct rte_ether_addr *mac_addr)
{
    // return all-zero mac address
    mac_addr->addr_bytes[0] = 0;
    mac_addr->addr_bytes[1] = 0;
    mac_addr->addr_bytes[2] = 0;
    mac_addr->addr_bytes[3] = 0;
    mac_addr->addr_bytes[4] = 0;
    mac_addr->addr_bytes[5] = 0;
}

uint16_t rte_eth_rx_burst(uint16_t port_id, uint16_t queue_id,
         struct rte_mbuf **rx_pkts, const uint16_t nb_pkts)
{
    klee_assert(devices_started[port_id]);
    klee_assert(queue_id == 0); // we only support that
    klee_assert(nb_pkts == 1); // same

    if (klee_int("received") == 0) {
        return 0;
    }

    struct rte_mempool* pool = devices_rx_mempool[port_id];
    stub_core_mbuf_create(port_id, pool, rx_pkts);
    stub_core_trace_rx(rx_pkts);

    return 1;
}

uint16_t rte_eth_tx_burst(uint16_t port_id, uint16_t queue_id,
         struct rte_mbuf **tx_pkts, uint16_t nb_pkts)
{
    klee_assert(devices_started[port_id]);
    klee_assert(queue_id == 0); // we only support that
    klee_assert(nb_pkts == 1); // same

    uint8_t ret = stub_core_trace_tx(*tx_pkts, port_id);
    if (ret == 0) {
        return 0;
    }

    stub_core_mbuf_free(*tx_pkts);
    return 1;
} 