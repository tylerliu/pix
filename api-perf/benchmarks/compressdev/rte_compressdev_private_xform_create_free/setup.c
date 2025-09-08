// Parse algorithm/checksum and initialize global decompression xform
const char* algorithm_str = get_benchmark_param("algorithm");
const char* checksum_str = get_benchmark_param("checksum");

const char* algorithm = algorithm_str ? algorithm_str : "deflate";
const char* checksum = checksum_str ? checksum_str : "none";

g_decomp_xform.type = RTE_COMP_DECOMPRESS;

if (strcmp(algorithm, "deflate") == 0) {
    g_decomp_xform.decompress.algo = RTE_COMP_ALGO_DEFLATE;
} else if (strcmp(algorithm, "lz4") == 0) {
    g_decomp_xform.decompress.algo = RTE_COMP_ALGO_LZ4;
} else if (strcmp(algorithm, "null") == 0) {
    g_decomp_xform.decompress.algo = RTE_COMP_ALGO_NULL;
} else {
    rte_exit(EXIT_FAILURE, "Unsupported algorithm: %s", algorithm);
}

if (strcmp(checksum, "crc32") == 0) {
    g_decomp_xform.decompress.chksum = RTE_COMP_CHECKSUM_CRC32;
} else if (strcmp(checksum, "adler32") == 0) {
    g_decomp_xform.decompress.chksum = RTE_COMP_CHECKSUM_ADLER32;
} else if (strcmp(checksum, "xxhash32") == 0) {
    g_decomp_xform.decompress.chksum = RTE_COMP_CHECKSUM_XXHASH32;
} else if (strcmp(checksum, "combined") == 0) {
    g_decomp_xform.decompress.chksum = RTE_COMP_CHECKSUM_CRC32_ADLER32;
} else {
    g_decomp_xform.decompress.chksum = RTE_COMP_CHECKSUM_NONE;
}
