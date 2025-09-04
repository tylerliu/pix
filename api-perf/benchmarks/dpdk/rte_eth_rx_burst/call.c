uint16_t rx_count = rte_eth_rx_burst(0, 0, bufs, burst_size);
result += rx_count;
// Free received packets back to the pool
for (int j = 0; j < rx_count; j++) {
    rte_pktmbuf_free(bufs[j]);
}