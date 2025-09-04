// Validate that all enqueued operations were dequeued
if (in_flight_ops != 0) {
    rte_exit(EXIT_FAILURE, "ERROR: %llu operations still in-flight at teardown. Enqueue/dequeue mismatch detected!", in_flight_ops);
}

// Free allocated crypto operations
for (unsigned int i = 0; i < burst_size; i++) {
    if (ops[i] != NULL) {
        rte_crypto_op_free(ops[i]);
        ops[i] = NULL;
    }
    if (mbufs[i] != NULL) {
        rte_pktmbuf_free(mbufs[i]);
        mbufs[i] = NULL;
    }
    if (dst_mbufs[i] != NULL) {
        rte_pktmbuf_free(dst_mbufs[i]);
        dst_mbufs[i] = NULL;
    }
}
