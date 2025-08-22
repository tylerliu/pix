// Crypto constants
#define AES128_KEY_LENGTH 16
#define MAX_AES_GCM_IV_LENGTH 12
#define AES_GCM_TAG_LENGTH 16

// Create a sample key for the session
uint8_t key[AES128_KEY_LENGTH] = {0};

// Setup AEAD transform
struct rte_crypto_sym_xform aead_xform = {
    .type = RTE_CRYPTO_SYM_XFORM_AEAD,
    .next = NULL,
    .aead = {
        .op = RTE_CRYPTO_AEAD_OP_DECRYPT,
        .algo = RTE_CRYPTO_AEAD_AES_GCM,
        .key.data = key,
        .key.length = AES128_KEY_LENGTH,
        .iv.offset = sizeof(struct rte_crypto_op) + sizeof(struct rte_crypto_sym_op), 
        .iv.length = MAX_AES_GCM_IV_LENGTH,
        .aad_length = 0,
        .digest_length = AES_GCM_TAG_LENGTH,
    },
};
