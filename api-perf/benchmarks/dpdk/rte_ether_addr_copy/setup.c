// Create a template mbuf with proper Ethernet header
struct rte_mbuf *template_mbuf = rte_pktmbuf_alloc(mbuf_pool);
if (template_mbuf == NULL) {
    rte_exit(EXIT_FAILURE, "Cannot allocate template mbuf\n");
}

// Set up a simple Ethernet packet
char *data = rte_pktmbuf_mtod(template_mbuf, char *);
// Ethernet header (14 bytes)
data[0] = 0x00; data[1] = 0x11; data[2] = 0x22; data[3] = 0x33; data[4] = 0x44; data[5] = 0x55; // dst MAC
data[6] = 0xAA; data[7] = 0xBB; data[8] = 0xCC; data[9] = 0xDD; data[10] = 0xEE; data[11] = 0xFF; // src MAC
data[12] = 0x08; data[13] = 0x00; // EtherType (IPv4)

template_mbuf->data_len = 14; // Ethernet header only
template_mbuf->pkt_len = 14;

// Use the template mbuf directly
bufs[0] = template_mbuf;
