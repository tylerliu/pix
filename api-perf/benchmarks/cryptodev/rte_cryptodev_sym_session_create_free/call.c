session = rte_cryptodev_sym_session_create(cdev_id, &aead_xform, session_pool);
if (session != NULL) {
    rte_cryptodev_sym_session_free(cdev_id, session);
}