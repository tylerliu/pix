#pragma once
#include <stdint.h>

/*
 * The following types should be used when handling values according to a
 * specific byte ordering, which may differ from that of the host CPU.
 *
 * Libraries, public APIs and applications are encouraged to use them for
 * documentation purposes.
 */
 typedef uint16_t rte_be16_t; /**< 16-bit big-endian value. */
 typedef uint32_t rte_be32_t; /**< 32-bit big-endian value. */
 typedef uint64_t rte_be64_t; /**< 64-bit big-endian value. */
 typedef uint16_t rte_le16_t; /**< 16-bit little-endian value. */
 typedef uint32_t rte_le32_t; /**< 32-bit little-endian value. */
 typedef uint64_t rte_le64_t; /**< 64-bit little-endian value. */
 

static inline uint16_t
rte_cpu_to_be_16(uint16_t x)
{
	return __builtin_bswap16(x);
}

static inline uint32_t
rte_cpu_to_be_32(uint32_t x)
{
	return __builtin_bswap32(x);
}

static inline uint16_t
rte_be_to_cpu_16(uint16_t x)
{
	return __builtin_bswap16(x);
}

static inline uint32_t
rte_be_to_cpu_32(uint32_t x)
{
	return __builtin_bswap32(x);
}
