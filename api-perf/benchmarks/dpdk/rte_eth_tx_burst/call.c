const char* burst_size_str = get_benchmark_param("burst_size");
unsigned int burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

uint16_t tx_count = rte_eth_tx_burst(0, 0, bufs, burst_size);
result += tx_count;

// Re-clone the bufs that were sent (consumed by tx_burst)
for (unsigned int j = 0; j < tx_count; j++) {
    bufs[j] = rte_pktmbuf_clone(bufs[j], mbuf_pool);
    if (bufs[j] == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot re-clone mbuf %u\n", j);
    }
}