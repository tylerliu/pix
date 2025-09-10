// Define constants
#define MBUF_DATA_SIZE 32768  // Large mbuf size for compression data
#define MBUF_POOL_SIZE 8192
#define MBUF_CACHE_SIZE 128

// Declare variables
static unsigned int burst_size;
struct rte_comp_op *ops[32];  // Max burst size
struct rte_mbuf *mbufs[32];   // Max burst size
struct rte_mbuf *dst_mbufs[32]; // Max burst size for destination
static struct rte_mempool *mbuf_pool = NULL;

// Variables for teardown and metadata
static void *new_decomp_private_xform = NULL;
static const char *algorithm = NULL;
static const char *checksum = NULL;
static unsigned long total_failed_ops = 0;
