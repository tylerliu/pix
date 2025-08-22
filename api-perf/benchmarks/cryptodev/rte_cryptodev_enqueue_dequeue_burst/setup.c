const char* burst_size_str = get_benchmark_param("burst_size");
burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

// Use the crypto_op_pool created by the template
if (rte_crypto_op_bulk_alloc(crypto_op_pool, RTE_CRYPTO_OP_TYPE_SYMMETRIC, ops, burst_size) < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate ops");
}

// Use the session created by the template
for (unsigned int i = 0; i < burst_size; i++) {
    rte_crypto_op_attach_sym_session(ops[i], session);
}