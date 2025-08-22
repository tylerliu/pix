// Use the crypto_op_pool created by the template
if (rte_crypto_op_bulk_alloc(crypto_op_pool, RTE_CRYPTO_OP_TYPE_SYMMETRIC, ops, 32) < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate ops");
}

// Use the session created by the template