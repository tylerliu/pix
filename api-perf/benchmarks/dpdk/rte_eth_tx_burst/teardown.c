// Free the allocated mbufs
for (unsigned int i = 0; i < g_burst_size; i++) {
    if (bufs[i] != NULL) {
        rte_pktmbuf_free(bufs[i]);
        bufs[i] = NULL;
    }
}
