// Clean up any remaining in-flight packets
struct rte_crypto_op *cleanup_ops[256];
while (in_flight_ops > 0) {
    unsigned int dequeued = rte_cryptodev_dequeue_burst(cdev_id, 0, cleanup_ops, 256);
    if (dequeued > 0) {
        in_flight_ops -= dequeued;
    } else {
        // No more packets to dequeue
        break;
    }
}
