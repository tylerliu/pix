const char* burst_size_str = get_benchmark_param("burst_size");
burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

if (rte_pktmbuf_alloc_bulk(mbuf_pool, bufs, burst_size) != 0) {
    rte_exit(EXIT_FAILURE, "Cannot allocate mbufs\n");
}

// Initialize a variable to accumulate total packets received
unsigned long result = 0;