/* SPDX-License-Identifier: BSD-3-Clause
 * Copyright(c) 1982, 1986, 1990, 1993
 *      The Regents of the University of California.
 * Copyright(c) 2010-2014 Intel Corporation.
 * All rights reserved.
 */

#ifndef _RTE_UDP_H_
#define _RTE_UDP_H_

/**
 * @file
 *
 * UDP-related defines
 */

#include <stdint.h>

#include <rte_byteorder.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * UDP Header
 */
struct rte_udp_hdr {
	rte_be16_t src_port;    /**< UDP source port. */
	rte_be16_t dst_port;    /**< UDP destination port. */
	rte_be16_t dgram_len;   /**< UDP datagram length */
	rte_be16_t dgram_cksum; /**< UDP datagram checksum */
} __attribute__((packed));

#ifdef __cplusplus
}
#endif

#endif /* RTE_UDP_H_ */
