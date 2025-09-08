// Create compression xform
struct rte_comp_xform comp_xform = {
    .type = RTE_COMP_COMPRESS,
    .compress = {
        .algo = RTE_COMP_ALGO_DEFLATE,
        .deflate.huffman = RTE_COMP_HUFFMAN_DEFAULT,
        .level = 6,
        .window_size = 15,
        .chksum = RTE_COMP_CHECKSUM_NONE,
    }
};

void *inside_private_xform;
int ret = rte_compressdev_private_xform_create(cdev_id, &comp_xform, &inside_private_xform);
if (ret == 0 && inside_private_xform != NULL) {
    rte_compressdev_private_xform_free(cdev_id, inside_private_xform);
}


