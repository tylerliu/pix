// Free allocated crypto operations
for (unsigned int i = 0; i < 32; i++) {
    if (ops[i] != NULL) {
        rte_crypto_op_free(ops[i]);
        ops[i] = NULL;
    }
}
