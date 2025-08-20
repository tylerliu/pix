uint16_t tx_count = rte_eth_tx_burst(0, 0, bufs, g_burst_size);
result += tx_count;
// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'burst_size': %u, 'total_packets_sent': %lu}\n", g_burst_size, result);
}