// Allocate a source mbuf to clone from
if (rte_pktmbuf_alloc_bulk(mbuf_pool, bufs, 1) != 0) {
    rte_exit(EXIT_FAILURE, "Cannot allocate mbuf for cloning\n");
}
