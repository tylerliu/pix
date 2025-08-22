// Create a template mbuf with proper packet data
struct rte_mbuf *template_mbuf = rte_pktmbuf_alloc(mbuf_pool);
if (template_mbuf == NULL) {
    rte_exit(EXIT_FAILURE, "Cannot allocate template mbuf\n");
}

// Set up a simple Ethernet packet - only IP header matters for rte_ipv4_cksum
char *data = rte_pktmbuf_mtod(template_mbuf, char *);
// Ethernet header (14 bytes)
data[0] = 0x00; data[1] = 0x11; data[2] = 0x22; data[3] = 0x33; data[4] = 0x44; data[5] = 0x55; // dst MAC
data[6] = 0x00; data[7] = 0x11; data[8] = 0x22; data[9] = 0x33; data[10] = 0x44; data[11] = 0x55; // src MAC
data[12] = 0x08; data[13] = 0x00; // EtherType (IPv4)

// IP header (20 bytes) - checksum will be calculated by the benchmark
data[14] = 0x45; // Version 4, header length 5
data[15] = 0x00; // Type of Service
data[16] = 0x00; data[17] = 0x22; // Total length (34 bytes)
data[18] = 0x00; data[19] = 0x00; // Identification
data[20] = 0x40; data[21] = 0x00; // Flags, Fragment offset
data[22] = 0x40; // Time to live
data[23] = 0x11; // Protocol (UDP)
data[24] = 0x00; data[25] = 0x00; // Checksum (will be calculated)
data[26] = 0x0a; data[27] = 0x00; data[28] = 0x00; data[29] = 0x01; // Source IP
data[30] = 0x0a; data[31] = 0x00; data[32] = 0x00; data[33] = 0x02; // Destination IP

// Minimal payload (just enough to make it a valid packet)
template_mbuf->data_len = 34; // Ethernet (14) + IP header (20)
template_mbuf->pkt_len = 34;

// Use the template mbuf directly
bufs[0] = template_mbuf;
