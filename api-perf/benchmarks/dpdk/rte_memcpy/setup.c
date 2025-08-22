const char* size_str = get_benchmark_param("size");
if (size_str) {
    size = (unsigned int)strtoul(size_str, NULL, 10);
} else {
    size = 64; // Default size
}

if (rte_pktmbuf_alloc_bulk(mbuf_pool, bufs, 1) != 0) {
    rte_exit(EXIT_FAILURE, "Cannot allocate mbufs\n");
}
