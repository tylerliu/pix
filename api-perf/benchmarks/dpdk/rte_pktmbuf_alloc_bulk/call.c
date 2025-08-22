unsigned int burst_size = (unsigned int)strtoul(get_benchmark_param("burst_size"), NULL, 10);
// Allocate mbufs
if (rte_pktmbuf_alloc_bulk(mbuf_pool, bufs, burst_size) != 0) {
    rte_exit(EXIT_FAILURE, "Cannot allocate mbufs in alloc_bulk benchmark\n");
}

// Free the allocated mbufs immediately to measure just the allocation cost
for (unsigned int j = 0; j < burst_size; j++) {
    rte_pktmbuf_free(bufs[j]);
    bufs[j] = NULL;
}
