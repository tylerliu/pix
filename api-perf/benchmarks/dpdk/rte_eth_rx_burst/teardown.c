// Free the allocated mbufs
for (unsigned int i = 0; i < burst_size; i++) {
    rte_pktmbuf_free(bufs[i]);
}

// Print metadata
printf("metadata: {'burst_size': %u, 'total_packets_received': %lu}\n", burst_size, result);
