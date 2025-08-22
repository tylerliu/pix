// Free the allocated mbufs
for (unsigned int i = 0; i < burst_size; i++) {
    rte_pktmbuf_free(bufs[i]);
}

