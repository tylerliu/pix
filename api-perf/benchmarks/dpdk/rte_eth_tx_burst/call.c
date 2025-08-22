uint16_t tx_count = rte_eth_tx_burst(0, 0, bufs, g_burst_size);
result += tx_count;

// Re-clone the bufs that were sent (consumed by tx_burst)
for (unsigned int j = 0; j < tx_count; j++) {
    bufs[j] = rte_pktmbuf_clone(bufs[j], mbuf_pool);
    if (bufs[j] == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot re-clone mbuf %u\n", j);
    }
}

// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'burst_size': %u, 'total_packets_sent': %lu}\n", g_burst_size, result);
}