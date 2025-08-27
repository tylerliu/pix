static unsigned int burst_size;
struct rte_crypto_op *ops[256];

// Mempool and mbufs used by this benchmark
static struct rte_mempool *mbuf_pool;
static struct rte_mbuf *mbufs[256];
static struct rte_mbuf *dst_mbufs[256];

// Tunables for mbuf pool and mbuf payload sizes
#define MBUF_POOL_SIZE 8192
#define MBUF_CACHE_SIZE 256
#define MBUF_DATA_SIZE RTE_MBUF_DEFAULT_BUF_SIZE

// Per-op inputs
static uint8_t ivs[256][MAX_AES_GCM_IV_LENGTH];

