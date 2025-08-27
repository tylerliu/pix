const char* burst_size_str = get_benchmark_param("burst_size");
burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

// Optional parameter: total data size per packet (includes tag)
const char* data_size_str = get_benchmark_param("data_size");
unsigned int data_size = data_size_str ? (unsigned int)strtoul(data_size_str, NULL, 10) : 1024;
if (data_size < AES_GCM_TAG_LENGTH) {
    rte_exit(EXIT_FAILURE, "data_size (%u) must be >= AES_GCM_TAG_LENGTH (%u)", data_size, (unsigned)AES_GCM_TAG_LENGTH);
}
if (data_size > MBUF_DATA_SIZE) {
    rte_exit(EXIT_FAILURE, "data_size (%u) exceeds MBUF_DATA_SIZE (%u)", data_size, (unsigned)MBUF_DATA_SIZE);
}

// Use the crypto_op_pool created by the template
if (rte_crypto_op_bulk_alloc(crypto_op_pool, RTE_CRYPTO_OP_TYPE_SYMMETRIC, ops, burst_size) < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate ops");
}

// Create mbuf pool on first use
if (mbuf_pool == NULL) {
    mbuf_pool = rte_pktmbuf_pool_create("mbuf_pool", MBUF_POOL_SIZE, MBUF_CACHE_SIZE, 0, MBUF_DATA_SIZE, rte_socket_id());
    if (mbuf_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create mbuf pool");
    }
}

// Allocate mbufs for this burst
if (rte_pktmbuf_alloc_bulk(mbuf_pool, mbufs, burst_size) < 0) {
    rte_exit(EXIT_FAILURE, "Failed to allocate mbufs");
}

// Initialize per-op buffers (IVs) and set lengths
for (unsigned int i = 0; i < burst_size; i++) {
    for (unsigned int j = 0; j < MAX_AES_GCM_IV_LENGTH; j++) {
        ivs[i][j] = (uint8_t)(i + j);
    }

    rte_pktmbuf_reset(mbufs[i]);
    rte_pktmbuf_append(mbufs[i], data_size);
}

// Attach encrypt session
for (unsigned int i = 0; i < burst_size; i++) {
    struct rte_crypto_op *op = ops[i];
    op->sym->m_src = mbufs[i];

    op->sym->aead.data.offset = 0;
    op->sym->aead.data.length = data_size - AES_GCM_TAG_LENGTH;

    op->sym->aead.digest.data = rte_pktmbuf_mtod_offset(mbufs[i], uint8_t *, data_size - AES_GCM_TAG_LENGTH);
    op->sym->aead.aad.data = rte_pktmbuf_mtod_offset(mbufs[i], uint8_t *, 0);

    rte_crypto_op_attach_sym_session(op, enc_session);
}

