// Free the allocated mbuf
if (bufs[0] != NULL) {
    rte_pktmbuf_free(bufs[0]);
    bufs[0] = NULL;
}
