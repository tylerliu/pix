// Create a template mbuf with proper packet data
struct rte_mbuf *template_mbuf = rte_pktmbuf_alloc(mbuf_pool);
if (template_mbuf == NULL) {
    rte_exit(EXIT_FAILURE, "Cannot allocate template mbuf\n");
}

// Set up a simple Ethernet + IPv4 + UDP header only packet (no payload)
char *data = rte_pktmbuf_mtod(template_mbuf, char *);
// Ethernet header (14 bytes)
data[0] = 0x00; data[1] = 0x11; data[2] = 0x22; data[3] = 0x33; data[4] = 0x44; data[5] = 0x55; // dst MAC
data[6] = 0x00; data[7] = 0x11; data[8] = 0x22; data[9] = 0x33; data[10] = 0x44; data[11] = 0x55; // src MAC
data[12] = 0x08; data[13] = 0x00; // EtherType (IPv4)

// IP header (20 bytes)
data[14] = 0x45; // Version 4, header length 5
data[15] = 0x00; // Type of Service
data[16] = 0x00; data[17] = 0x1C; // Total length = 28 bytes -> IP(20) + UDP(8) + payload(0)
data[18] = 0x00; data[19] = 0x00; // Identification
data[20] = 0x40; data[21] = 0x00; // Flags, Fragment offset
data[22] = 0x40; // Time to live
data[23] = 0x11; // Protocol (UDP)
data[24] = 0x00; data[25] = 0x00; // Checksum (will be calculated by rte_ipv4_cksum, not needed here)
data[26] = 0x0a; data[27] = 0x00; data[28] = 0x00; data[29] = 0x01; // Source IP
data[30] = 0x0a; data[31] = 0x00; data[32] = 0x00; data[33] = 0x02; // Destination IP

// UDP header (8 bytes)
data[34] = 0x00; data[35] = 0x35; // Source port (53)
data[36] = 0x00; data[37] = 0x35; // Destination port (53)
data[38] = 0x00; data[39] = 0x08; // Length = 8 (header only)
data[40] = 0x00; data[41] = 0x00; // Checksum (will be calculated elsewhere if needed)

// Minimal packet length: Ethernet (14) + IP (20) + UDP (8) = 42 bytes
template_mbuf->data_len = 42;
template_mbuf->pkt_len = 42;

// Use the template mbuf directly
bufs[0] = template_mbuf;
