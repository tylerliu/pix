// Enqueue operations
unsigned int enqueued = rte_compressdev_enqueue_burst(cdev_id, 0, ops, burst_size);

// Poll for completion - only count cycles when we get results
struct rte_comp_op *dequeued_ops[burst_size];
unsigned int total_dequeued = 0;
uint64_t poll_start = rte_rdtsc();

while (total_dequeued < enqueued) {
    unsigned int dequeued = rte_compressdev_dequeue_burst(cdev_id, 0, &dequeued_ops[total_dequeued], enqueued - total_dequeued);
    if (dequeued > 0) {
        total_dequeued += dequeued;
    }
    // If dequeued == 0, we don't count those cycles (they're polling overhead)
}

uint64_t poll_end = rte_rdtsc();
uint64_t poll_cycles = poll_end - poll_start;

// Validate that all enqueued operations were dequeued
if (enqueued != total_dequeued) {
    rte_exit(EXIT_FAILURE, "ERROR: Enqueued %u but dequeued %u operations", enqueued, total_dequeued);
}

// Check for errors in dequeued operations
unsigned int failed_ops = 0;
for (unsigned int i = 0; i < total_dequeued; i++) {
    struct rte_comp_op *op = dequeued_ops[i];
    if (op->status != RTE_COMP_OP_STATUS_SUCCESS) {
        failed_ops++;
        printf("ERROR: Operation %u failed with status %d\n", i, op->status);
        
        // Print detailed error information based on status
        switch (op->status) {
            case RTE_COMP_OP_STATUS_NOT_PROCESSED:
                printf("  -> Operation not processed\n");
                break;
            case RTE_COMP_OP_STATUS_ERROR:
                printf("  -> General operation error\n");
                break;
            case RTE_COMP_OP_STATUS_INVALID_ARGS:
                printf("  -> Invalid arguments provided\n");
                break;
            case RTE_COMP_OP_STATUS_INVALID_STATE:
                printf("  -> Bad state error\n");
                break;
            case RTE_COMP_OP_STATUS_OUT_OF_SPACE_TERMINATED:
                printf("  -> Out of space - operation terminated\n");
                break;
            case RTE_COMP_OP_STATUS_OUT_OF_SPACE_RECOVERABLE:
                printf("  -> Out of space - operation recovered\n");
                break;
            default:
                printf("  -> Unknown error status: %d\n", op->status);
                break;
        }
    }
}

// Report error statistics
if (failed_ops > 0) {
    printf("WARNING: %u out of %u operations failed\n", failed_ops, total_dequeued);
    // Don't exit on errors, just report them for analysis
}

// Accumulate total failed operations for final reporting
total_failed_ops += failed_ops;

// Report poll time to be subtracted from cycle count
total_poll_cycles += poll_cycles;


