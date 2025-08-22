int ret = rte_crypto_op_bulk_alloc(crypto_op_pool, RTE_CRYPTO_OP_TYPE_SYMMETRIC, ops, bulk_size);
if (ret < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate ops");
}

for (unsigned int i = 0; i < bulk_size; i++) {
    if (ops[i] != NULL) {
        rte_crypto_op_free(ops[i]);
        ops[i] = NULL;
    }
}