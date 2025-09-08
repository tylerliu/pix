struct rte_comp_op *ops[bulk_size];
int ret = rte_comp_op_bulk_alloc(comp_op_pool, ops, bulk_size);
if (ret < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate ops");
}

for (unsigned int i = 0; i < bulk_size; i++) {
    if (ops[i] != NULL) {
        rte_comp_op_free(ops[i]);
        ops[i] = NULL;
    }
}


