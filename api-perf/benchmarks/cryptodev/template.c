#include <stdio.h>
#include <stdlib.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_crypto.h>
#include <rte_cryptodev.h>

#include "driver/benchmark_driver.h"

#define MAX_AES_GCM_IV_LENGTH 12

// {{DPDK_HEADERS}}

static uint8_t cdev_id = 0;
static struct rte_cryptodev_sym_session *enc_session;
static struct rte_cryptodev_sym_session *dec_session;
static struct rte_mempool *crypto_op_pool;
static struct rte_mempool *session_pool;

// Crypto constants
#define AES128_KEY_LENGTH 16
#define MAX_AES_GCM_IV_LENGTH 12
#define AES_GCM_TAG_LENGTH 16

void setup_cryptodev() {
    // Check that crypto device is available
    int num_crypto_devices = rte_cryptodev_count();
    if (num_crypto_devices < 1) {
        rte_exit(EXIT_FAILURE, "No crypto devices available\n");
    }

    // Get crypto device info
    struct rte_cryptodev_info cdev_info;
    rte_cryptodev_info_get(cdev_id, &cdev_info);

    // Create crypto operation pool
    crypto_op_pool = rte_crypto_op_pool_create("crypto_op_pool", 
                                              RTE_CRYPTO_OP_TYPE_SYMMETRIC, 
                                              8192, 128, MAX_AES_GCM_IV_LENGTH, rte_socket_id());
    if (crypto_op_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create crypto operation pool\n");
    }

    // Create session pool
    const uint32_t private_session_size = rte_cryptodev_sym_get_private_session_size(cdev_id);
    session_pool = rte_cryptodev_sym_session_pool_create("session_pool",
                                                        8192, 128, private_session_size, 0, rte_socket_id());
    if (session_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create session pool\n");
    }

    // Configure crypto device
    struct rte_cryptodev_config config = {
        .nb_queue_pairs = 1,
        .socket_id = rte_socket_id(),
        .ff_disable = RTE_CRYPTODEV_FF_ASYMMETRIC_CRYPTO | RTE_CRYPTODEV_FF_SECURITY,
    };
    if (rte_cryptodev_configure(cdev_id, &config) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to configure cryptodev %u\n", cdev_id);
    }

    // Setup queue pair
    struct rte_cryptodev_qp_conf qp_conf = {
        .nb_descriptors = 128
    };
    if (rte_cryptodev_queue_pair_setup(cdev_id, 0, &qp_conf, rte_socket_id()) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to setup queue pair\n");
    }

    // Start crypto device
    if (rte_cryptodev_start(cdev_id) < 0) {
        rte_exit(EXIT_FAILURE, "Failed to start crypto device\n");
    }

    // Create a sample key for the session
    uint8_t key[AES128_KEY_LENGTH];
    for (int i = 0; i < AES128_KEY_LENGTH; i++) {
        key[i] = i; // Simple key for testing
    }

    // Setup AEAD transforms (encrypt and decrypt)
    struct rte_crypto_sym_xform enc_xform = {
        .type = RTE_CRYPTO_SYM_XFORM_AEAD,
        .next = NULL,
        .aead = {
            .op = RTE_CRYPTO_AEAD_OP_ENCRYPT,
            .algo = RTE_CRYPTO_AEAD_AES_GCM,
            .key.data = key,
            .key.length = AES128_KEY_LENGTH,
            .iv.offset = sizeof(struct rte_crypto_op) + sizeof(struct rte_crypto_sym_op), 
            .iv.length = MAX_AES_GCM_IV_LENGTH,
            .aad_length = 0,
            .digest_length = AES_GCM_TAG_LENGTH,
        },
    };

    struct rte_crypto_sym_xform dec_xform = enc_xform;
    dec_xform.aead.op = RTE_CRYPTO_AEAD_OP_DECRYPT;

    // Create sessions
    enc_session = rte_cryptodev_sym_session_create(cdev_id, &enc_xform, session_pool);
    if (enc_session == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create encrypt session\n");
    }
    dec_session = rte_cryptodev_sym_session_create(cdev_id, &dec_xform, session_pool);
    if (dec_session == NULL) {
        rte_exit(EXIT_FAILURE, "Failed to create decrypt session\n");
    }
}

void setup_benchmark() {
    // {{BENCHMARK_SETUP}}
}

void run_benchmark() {
    uint64_t start, end;
    volatile uint64_t result = 0;

    start = rte_rdtsc();
    for (unsigned long long i = 0; i < g_iterations; ++i) {
        // {{BENCHMARK_LOOP}}
    }
    end = rte_rdtsc();

    uint64_t total_cycles = end - start;
    printf("Total cycles: %lu\n", (unsigned long)total_cycles);
    
    // Clean up any remaining in-flight packets (not counted in cycles)
    // {{CLEANUP_INFLIGHT}}
}

void teardown_benchmark() {
    // {{BENCHMARK_TEARDOWN}}
}

void teardown_cryptodev() {
    // Free sessions
    if (enc_session != NULL) {
        rte_cryptodev_sym_session_free(cdev_id, enc_session);
        enc_session = NULL;
    }
    if (dec_session != NULL) {
        rte_cryptodev_sym_session_free(cdev_id, dec_session);
        dec_session = NULL;
    }
    
    // Stop and close crypto device
    rte_cryptodev_stop(cdev_id);
    rte_cryptodev_close(cdev_id);

    // Free crypto operation pool
    if (crypto_op_pool != NULL) {
        rte_mempool_free(crypto_op_pool);
        crypto_op_pool = NULL;
    }

    // Free session pool
    if (session_pool != NULL) {
        rte_mempool_free(session_pool);
        session_pool = NULL;
    }
}

int main(int argc, char **argv) {
    init_dpdk(argc, argv);
    setup_cryptodev();
    setup_benchmark();
    run_benchmark();
    teardown_benchmark();
    teardown_cryptodev();
    cleanup_dpdk();
    return 0;
}
