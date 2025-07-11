// used with VeriFast, no pragma
#ifndef RTE_IP_H
#define RTE_IP_H

#include <klee/klee.h>
#include <stdint.h>
#include <rte_byteorder.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define IPV4_HDR_IHL_MASK 0x0F
#define IPV4_IHL_MULTIPLIER 4

/**
 * IPv4 Header
 */
 struct rte_ipv4_hdr {
  __extension__
  union {
          uint8_t version_ihl;    /**< version and header length */
          struct {
#if RTE_BYTE_ORDER == RTE_LITTLE_ENDIAN
                  uint8_t ihl:4;     /**< header length */
                  uint8_t version:4; /**< version */
#elif RTE_BYTE_ORDER == RTE_BIG_ENDIAN
                  uint8_t version:4; /**< version */
                  uint8_t ihl:4;     /**< header length */
#endif
          };
  };
  uint8_t  type_of_service;       /**< type of service */
  rte_be16_t total_length;        /**< length of packet */
  rte_be16_t packet_id;           /**< packet ID */
  rte_be16_t fragment_offset;     /**< fragmentation offset */
  uint8_t  time_to_live;          /**< time to live */
  uint8_t  next_proto_id;         /**< protocol ID */
  rte_be16_t hdr_checksum;        /**< header checksum */
  rte_be32_t src_addr;            /**< source address */
  rte_be32_t dst_addr;            /**< destination address */
} __attribute__((packed));

__attribute__((noinline)) static uint16_t
rte_ipv4_icmp_cksum(const struct rte_ipv4_hdr *ipv4_hdr, const void *l4_hdr) {
  return klee_int("ICMP_cksum");
}

__attribute__((noinline)) static uint16_t
rte_ipv4_udptcp_cksum(const struct rte_ipv4_hdr *ipv4_hdr, const void *l4_hdr) {
  return klee_int("UDP_TCP_cksum");
}

__attribute__((noinline)) static uint16_t
rte_ipv4_cksum(const struct rte_ipv4_hdr *ipv4_hdr) {
  return klee_int("IPV4_cksum"); // TODO?
}

#endif
