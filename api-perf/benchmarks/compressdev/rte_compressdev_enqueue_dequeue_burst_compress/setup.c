const char* burst_size_str = get_benchmark_param("burst_size");
burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

// Optional parameter: data size per operation
const char* data_size_str = get_benchmark_param("data_size");
unsigned int data_size = data_size_str ? (unsigned int)strtoul(data_size_str, NULL, 10) : 1024;
if (data_size > MBUF_DATA_SIZE) {
    rte_exit(EXIT_FAILURE, "data_size (%u) exceeds MBUF_DATA_SIZE (%u)", data_size, (unsigned)MBUF_DATA_SIZE);
}

// Algorithm parameter: deflate, lz4, null
const char* algorithm_str = get_benchmark_param("algorithm");
algorithm = algorithm_str ? algorithm_str : "deflate";

// Checksum parameter: none, crc32, adler32, xxhash32
const char* checksum_str = get_benchmark_param("checksum");
checksum = checksum_str ? checksum_str : "none";

// Huffman parameter for DEFLATE: fixed, dynamic
const char* huffman_str = get_benchmark_param("huffman");
const char* huffman = huffman_str ? huffman_str : "dynamic";

// Window size parameter: 1024, 2048, 4096, 8192, 16384, 32768
const char* window_size_str = get_benchmark_param("window_size");
unsigned int window_size = window_size_str ? (unsigned int)strtoul(window_size_str, NULL, 10) : 32768;

// Configure compression xform based on parameters
struct rte_comp_xform comp_xform = {
    .type = RTE_COMP_COMPRESS,
};

// Set algorithm and algorithm-specific parameters
if (strcmp(algorithm, "deflate") == 0) {
    comp_xform.compress.algo = RTE_COMP_ALGO_DEFLATE;
    comp_xform.compress.deflate.huffman = (strcmp(huffman, "fixed") == 0) ? 
        RTE_COMP_HUFFMAN_FIXED : RTE_COMP_HUFFMAN_DYNAMIC;
    comp_xform.compress.window_size = window_size;
} else if (strcmp(algorithm, "lz4") == 0) {
    comp_xform.compress.algo = RTE_COMP_ALGO_LZ4;
    comp_xform.compress.window_size = window_size;
} else if (strcmp(algorithm, "null") == 0) {
    comp_xform.compress.algo = RTE_COMP_ALGO_NULL;
} else {
    rte_exit(EXIT_FAILURE, "Unsupported algorithm: %s", algorithm);
}

// Set checksum type
if (strcmp(checksum, "crc32") == 0) {
    comp_xform.compress.chksum = RTE_COMP_CHECKSUM_CRC32;
} else if (strcmp(checksum, "adler32") == 0) {
    comp_xform.compress.chksum = RTE_COMP_CHECKSUM_ADLER32;
} else if (strcmp(checksum, "xxhash32") == 0) {
    comp_xform.compress.chksum = RTE_COMP_CHECKSUM_XXHASH32;
} else {
    comp_xform.compress.chksum = RTE_COMP_CHECKSUM_NONE;
}

// Create new private xform for this specific configuration
if (rte_compressdev_private_xform_create(cdev_id, &comp_xform, &new_comp_private_xform) < 0) {
    rte_exit(EXIT_FAILURE, "Failed to create compression private xform for algorithm %s", algorithm);
}

// Use the comp_op_pool created by the template
if (rte_comp_op_bulk_alloc(comp_op_pool, ops, burst_size) < 0) {
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

// Initialize mbufs with test data
for (unsigned int i = 0; i < burst_size; i++) {
    rte_pktmbuf_reset(mbufs[i]);
    rte_pktmbuf_append(mbufs[i], data_size);
    
    // Fill with test data
    uint8_t *data = rte_pktmbuf_mtod(mbufs[i], uint8_t *);
    for (unsigned int j = 0; j < data_size; j++) {
        data[j] = (uint8_t)(i + j);
    }
}

// Setup compression operations
for (unsigned int i = 0; i < burst_size; i++) {
    struct rte_comp_op *op = ops[i];
    op->m_src = mbufs[i];
    op->m_dst = NULL; // Will be allocated by the device
    
    op->src.offset = 0;
    op->src.length = data_size;
    op->dst.offset = 0;
    // Note: dst.length will be set by the device after compression
    
    // Set private xform in the operation
    op->private_xform = new_comp_private_xform;
}


