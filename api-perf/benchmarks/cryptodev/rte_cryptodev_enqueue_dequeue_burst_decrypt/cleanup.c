// Clean up any remaining in-flight packets
while (in_flight_ops > 0) {
    struct rte_crypto_op *dequeued_ops[burst_size];
    unsigned int dequeued = rte_cryptodev_dequeue_burst(cdev_id, 0, dequeued_ops, burst_size);
    in_flight_ops -= dequeued;
}
