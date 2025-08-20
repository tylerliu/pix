struct rte_ether_hdr *eth = rte_pktmbuf_mtod(bufs[0], struct rte_ether_hdr *);
struct rte_ether_addr tmp;
rte_ether_addr_copy(&eth->src_addr, &tmp);
rte_ether_addr_copy(&eth->dst_addr, &eth->src_addr);
rte_ether_addr_copy(&tmp, &eth->dst_addr);

