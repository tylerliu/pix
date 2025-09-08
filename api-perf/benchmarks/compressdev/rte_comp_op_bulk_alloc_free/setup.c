// Parse burst_size parameter
const char* burst_size_str = get_benchmark_param("burst_size");
burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;
