volatile uint16_t sum = rte_raw_cksum(rte_pktmbuf_mtod(bufs[0], void *), pkt_size);
// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'checksum_size': %u, 'checksum_result': %u}\n", pkt_size, sum);
}

