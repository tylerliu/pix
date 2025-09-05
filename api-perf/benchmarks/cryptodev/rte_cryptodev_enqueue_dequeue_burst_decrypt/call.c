// Enqueue operations
unsigned int enqueued = rte_cryptodev_enqueue_burst(cdev_id, 0, ops, burst_size);

// Poll for completion - only count cycles when we get results
struct rte_crypto_op *dequeued_ops[burst_size];
unsigned int total_dequeued = 0;
uint64_t poll_start = rte_rdtsc();
uint64_t poll_end = poll_start;

while (total_dequeued < enqueued) {
    unsigned int dequeued = rte_cryptodev_dequeue_burst(cdev_id, 0, &dequeued_ops[total_dequeued], enqueued - total_dequeued);
    if (dequeued > 0) {
        total_dequeued += dequeued;
        break;
    } else {
        poll_end = rte_rdtsc();
    }
    // If dequeued == 0, we don't count those cycles (they're polling overhead)
}
uint64_t poll_cycles = poll_end - poll_start;

// Validate that all enqueued operations were dequeued
if (enqueued != total_dequeued) {
    rte_exit(EXIT_FAILURE, "ERROR: Enqueued %u but dequeued %u operations", enqueued, total_dequeued);
}

// Report poll time to be subtracted from cycle count
total_poll_cycles += poll_cycles;