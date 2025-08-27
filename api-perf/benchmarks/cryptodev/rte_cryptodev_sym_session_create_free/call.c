struct rte_cryptodev_sym_session *inside_session = rte_cryptodev_sym_session_create(cdev_id, &aead_xform, session_pool);
if (inside_session != NULL) {
    rte_cryptodev_sym_session_free(cdev_id, inside_session);
}