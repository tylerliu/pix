// Empty benchmark - measure time between consecutive rdtsc calls
uint64_t start_rdtsc = rte_rdtsc();
uint64_t end_rdtsc = rte_rdtsc();
uint64_t rdtsc_overhead = end_rdtsc - start_rdtsc;
total_poll_cycles += rdtsc_overhead;
