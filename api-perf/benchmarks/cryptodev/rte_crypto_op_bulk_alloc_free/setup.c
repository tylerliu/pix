const char* bulk_size_str = get_benchmark_param("bulk_size");
bulk_size = bulk_size_str ? (unsigned int)strtoul(bulk_size_str, NULL, 10) : 32;

// Use the crypto_op_pool created by the template