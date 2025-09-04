const char* burst_size_str = get_benchmark_param("burst_size");
unsigned int burst_size = burst_size_str ? (unsigned int)strtoul(burst_size_str, NULL, 10) : 32;

// Enqueue operations and track them
unsigned int enqueued = rte_cryptodev_enqueue_burst(cdev_id, 0, ops, burst_size);
in_flight_ops += enqueued;

// Dequeue operations and track completion
struct rte_crypto_op *dequeued_ops[burst_size];
unsigned int dequeued = rte_cryptodev_dequeue_burst(cdev_id, 0, dequeued_ops, burst_size);
in_flight_ops -= dequeued;

