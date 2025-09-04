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
}

// Print metadata
printf("metadata: {'burst_size': %u, 'total_poll_cycles': %lu}\n", burst_size, (unsigned long)total_poll_cycles);