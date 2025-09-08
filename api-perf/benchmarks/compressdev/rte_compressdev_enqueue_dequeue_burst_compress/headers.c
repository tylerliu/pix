// Define constants
#define MBUF_DATA_SIZE 65536  // Large mbuf size for compression data
#define MBUF_POOL_SIZE 8192
#define MBUF_CACHE_SIZE 128

// Declare variables
static unsigned int burst_size;
struct rte_comp_op *ops[32];  // Max burst size
struct rte_mbuf *mbufs[32];   // Max burst size
static struct rte_mempool *mbuf_pool = NULL;

// Variables for teardown and metadata
static void *new_comp_private_xform = NULL;
static const char *algorithm = NULL;
static const char *checksum = NULL;
