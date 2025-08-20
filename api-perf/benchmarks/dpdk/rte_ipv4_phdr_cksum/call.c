struct rte_ipv4_hdr *ip = rte_pktmbuf_mtod_offset(bufs[0], struct rte_ipv4_hdr *, sizeof(struct rte_ether_hdr));
volatile uint16_t ph = rte_ipv4_phdr_cksum(ip, 0);

