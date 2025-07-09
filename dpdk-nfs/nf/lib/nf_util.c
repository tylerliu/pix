#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include <netinet/in.h>

#include <rte_byteorder.h>
#include <rte_string_fns.h>
#include <rte_common.h>
#include <rte_ether.h>
#include <rte_ip.h>
#include <rte_mbuf.h>
#include <rte_mbuf_ptype.h>
#include <rte_tcp.h>
#include <rte_udp.h>
#include <rte_arp.h>
#include <rte_icmp.h>

#include "nf_util.h"

// Stub for missing rte_ipv4_icmp_cksum function
uint16_t rte_ipv4_icmp_cksum(struct rte_ipv4_hdr *ip_hdr, struct rte_icmp_hdr *icmp_hdr);

struct rte_ether_hdr *nf_get_mbuf_ether_header(struct rte_mbuf *mbuf) {
  return rte_pktmbuf_mtod(mbuf, struct rte_ether_hdr *);
}

// TODO for consistency it'd be nice if this took an ether_hdr as argument, or
// if they all took rte_mbuf
struct rte_ipv4_hdr *nf_get_mbuf_ipv4_header(struct rte_mbuf *mbuf) {
  struct rte_ether_hdr *ether_header = nf_get_mbuf_ether_header(mbuf);
  if (ether_header->ether_type != rte_cpu_to_be_16(RTE_ETHER_TYPE_IPV4)) {
    return NULL;
  }

  return rte_pktmbuf_mtod_offset(mbuf, struct rte_ipv4_hdr *,
                                 sizeof(struct rte_ether_hdr));
}

struct arp_hdr *nf_get_mbuf_arp_header(struct rte_mbuf *mbuf){
  struct rte_ether_hdr *ether_header = nf_get_mbuf_ether_header(mbuf);
  if (ether_header->ether_type != rte_cpu_to_be_16(RTE_ETHER_TYPE_ARP)) {
    return NULL;
  }
  return rte_pktmbuf_mtod_offset(mbuf, struct arp_hdr *,
                                 sizeof(struct rte_ether_hdr));
}

struct tcpudp_hdr *nf_get_ipv4_tcpudp_header(struct rte_ipv4_hdr *header) {
  if (header->next_proto_id != IPPROTO_TCP &&
      header->next_proto_id != IPPROTO_UDP) {
    return NULL;
  }

  uint8_t offset = header->ihl;
  return (struct tcpudp_hdr *)((unsigned char *)header + offset);
}

struct rte_icmp_hdr *nf_get_ipv4_icmp_header(struct rte_ipv4_hdr *header) {
  if (header->next_proto_id != IPPROTO_ICMP) {
    return NULL;
  }

  uint8_t offset = header->ihl;
  return (struct rte_icmp_hdr *)((unsigned char *)header + offset);
}

__attribute__((noinline)) void nf_set_ipv4_checksum(struct rte_ipv4_hdr *header) {

  #ifdef KLEE_VERIFICATION
    klee_trace_ret();
  #endif 
  // TODO: See if can be offloaded to hardware
  header->hdr_checksum = 0;

  if (header->next_proto_id == IPPROTO_TCP) {
    struct rte_tcp_hdr *tcp_header = (struct rte_tcp_hdr *)(header + 1);
    tcp_header->cksum = 0;
    tcp_header->cksum = rte_ipv4_udptcp_cksum(header, tcp_header);
  } else if (header->next_proto_id == IPPROTO_UDP) {
    struct rte_udp_hdr *udp_header = (struct rte_udp_hdr *)(header + 1);
    udp_header->dgram_cksum = 0;
    udp_header->dgram_cksum = rte_ipv4_udptcp_cksum(header, udp_header);
  } else if (header->next_proto_id == IPPROTO_ICMP) {
    struct rte_icmp_hdr* icmp_header = (struct rte_icmp_hdr *)(header+1);
    icmp_header->icmp_cksum = 0;
#ifdef KLEE_VERIFICATION
    icmp_header->icmp_cksum = rte_ipv4_icmp_cksum(header, icmp_header); //HACK
#else
    icmp_header->icmp_cksum = ~rte_raw_cksum(icmp_header,rte_be_to_cpu_16(header->total_length) - sizeof(*header)); 
#endif
  }
  header->hdr_checksum = rte_ipv4_cksum(header);
}

uintmax_t nf_util_parse_int(const char *str, const char *name, int base,
                            char next) {
  char *temp;
  intmax_t result = strtoimax(str, &temp, base);

  // There's also a weird failure case with overflows, but let's not care
  if (temp == str || *temp != next) {
    rte_exit(EXIT_FAILURE, "Error while parsing '%s': %s\n", name, str);
  }

  return result;
}

char *nf_mac_to_str(struct rte_ether_addr *addr) {
  // format is xx:xx:xx:xx:xx:xx\0
  uint16_t buffer_size = 6 * 2 + 5 + 1;
  char *buffer = (char *)calloc(buffer_size, sizeof(char));
  if (buffer == NULL) {
    rte_exit(EXIT_FAILURE, "Out of memory in nf_mac_to_str!");
  }

  rte_ether_format_addr(buffer, buffer_size, addr);
  return buffer;
}

char *nf_ipv4_to_str(uint32_t addr) {
  // format is xxx.xxx.xxx.xxx\0
  uint16_t buffer_size = 4 * 3 + 3 + 1;
  char *buffer = (char *)calloc(buffer_size, sizeof(char));
  if (buffer == NULL) {
    rte_exit(EXIT_FAILURE, "Out of memory in nf_ipv4_to_str!");
  }

  snprintf(buffer, buffer_size, "%" PRIu8 ".%" PRIu8 ".%" PRIu8 ".%" PRIu8,
           addr & 0xFF, (addr >> 8) & 0xFF, (addr >> 16) & 0xFF,
           (addr >> 24) & 0xFF);
  return buffer;
}
