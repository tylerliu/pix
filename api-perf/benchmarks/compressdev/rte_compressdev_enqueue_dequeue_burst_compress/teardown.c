// Free allocated compression operations
for (unsigned int i = 0; i < burst_size; i++) {
    if (ops[i] != NULL) {
        rte_comp_op_free(ops[i]);
        ops[i] = NULL;
    }
    if (mbufs[i] != NULL) {
        rte_pktmbuf_free(mbufs[i]);
        mbufs[i] = NULL;
    }
}

// Free the dynamically created private xform
if (new_comp_private_xform != NULL) {
    rte_compressdev_private_xform_free(cdev_id, new_comp_private_xform);
    new_comp_private_xform = NULL;
}

// Print metadata
printf("metadata: {'burst_size': %u, 'algorithm': '%s', 'checksum': '%s', 'total_poll_cycles': %lu}\n", 
       burst_size, algorithm, checksum, (unsigned long)total_poll_cycles);


