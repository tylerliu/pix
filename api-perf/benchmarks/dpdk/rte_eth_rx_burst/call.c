uint16_t rx_count = rte_eth_rx_burst(0, 0, bufs, g_burst_size);
result += rx_count;
// Free received packets back to the pool
for (int j = 0; j < rx_count; j++) {
    rte_pktmbuf_free(bufs[j]);
}
// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'burst_size': %u, 'total_packets_received': %lu}\n", g_burst_size, result);
}