void *inside_private_xform;
int ret = rte_compressdev_private_xform_create(cdev_id, &g_decomp_xform, &inside_private_xform);
if (ret == 0 && inside_private_xform != NULL) {
    rte_compressdev_private_xform_free(cdev_id, inside_private_xform);
}


