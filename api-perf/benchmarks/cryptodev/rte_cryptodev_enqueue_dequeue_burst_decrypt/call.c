const char* burst_size_str = get_benchmark_param("burst_size");
unsigned int burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

rte_cryptodev_enqueue_burst(cdev_id, 0, ops, burst_size);
struct rte_crypto_op *dequeued_ops[burst_size];
rte_cryptodev_dequeue_burst(cdev_id, 0, dequeued_ops, burst_size);

