struct rte_mbuf *clone = rte_pktmbuf_clone(bufs[0], mbuf_pool);
rte_pktmbuf_free(clone);

