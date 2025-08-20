struct rte_ipv4_hdr *ip = rte_pktmbuf_mtod_offset(bufs[0], struct rte_ipv4_hdr *, sizeof(struct rte_ether_hdr));
struct rte_udp_hdr *udp = rte_pktmbuf_mtod_offset(bufs[0], struct rte_udp_hdr *, sizeof(struct rte_ether_hdr) + sizeof(struct rte_ipv4_hdr));
volatile uint16_t uh = rte_ipv4_udptcp_cksum(ip, udp);

