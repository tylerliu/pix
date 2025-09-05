/* Build-time header detection to avoid linter errors when DOCA headers
 * are not present in the workspace. */
#ifndef __has_include
#  define __has_include(x) 0
#endif
#if __has_include(<doca_dpa.h>) && __has_include(<doca_dev.h>) && __has_include(<doca_sync_event.h>)
#  define HAVE_DOCA 1
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef HAVE_DOCA
#include <doca_dpa.h>
#include <doca_dev.h>
#include <doca_error.h>
#include <doca_sync_event.h>

/* Auto-generated index provides:
 *   struct bench_entry { const char *name; doca_dpa_func_t *func; };
 *   extern const struct bench_entry g_bench_index[];
 *   extern const size_t g_bench_index_len;
 */
extern struct bench_entry { const char *name; doca_dpa_func_t *func; } g_bench_index[];
extern size_t g_bench_index_len;

/* Provided by dpacc meta stub based on --app-name.
 * Allow overriding the symbol name via -DAPP_SYM=... at compile time. */
#ifdef APP_SYM
extern struct doca_dpa_app *APP_SYM;
#define dpa_ir_bench_app APP_SYM
#else
extern struct doca_dpa_app *dpa_ir_bench_app;
#endif

static struct bench_entry* find_bench(const char* name) {
    for (size_t i = 0; i < g_bench_index_len; ++i) {
        if (strcmp(g_bench_index[i].name, name) == 0) return &g_bench_index[i];
    }
    return NULL;
}

static void usage(const char* prog) {
    fprintf(stderr, "Usage: %s --bench <name>\n", prog);
}

int main(int argc, char** argv) {
    const char* bench_name = NULL;
    if (argc >= 3 && strcmp(argv[1], "--bench") == 0) {
        bench_name = argv[2];
    } else {
        usage(argv[0]);
        return 1;
    }

    struct bench_entry* entry = find_bench(bench_name);
    if (entry == NULL) {
        fprintf(stderr, "Bench not found: %s\n", bench_name);
        return 1;
    }

    struct doca_dev* dev = NULL; /* In a minimal setup, rely on default selection (omitted) */
    struct doca_dpa* dpa = NULL;
    struct doca_sync_event* se = NULL;
    doca_dpa_dev_sync_event_t se_handle = 0;
    struct doca_dpa_thread* thr = NULL;

    /* Device selection is omitted for brevity; assuming default device works.
     * For production, enumerate and select a device matching CLI params. */

    doca_error_t rc;

    rc = doca_dpa_create(dev, &dpa); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_dpa_set_app(dpa, dpa_ir_bench_app); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_dpa_start(dpa); if (rc != DOCA_SUCCESS) goto fail;

    rc = doca_sync_event_create(&se); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_sync_event_add_publisher_location_dpa(se, dpa); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_sync_event_add_subscriber_location_cpu(se, dev); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_sync_event_start(se); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_sync_event_get_dpa_handle(se, dpa, &se_handle); if (rc != DOCA_SUCCESS) goto fail;

    rc = doca_dpa_thread_create(dpa, &thr); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_dpa_thread_set_func_arg(thr, entry->func, se_handle); if (rc != DOCA_SUCCESS) goto fail;
    rc = doca_dpa_thread_start(thr); if (rc != DOCA_SUCCESS) goto fail;

    /* Wait for signal */
    rc = doca_sync_event_wait_gt(se, 0, 0xFFFFFFFFFFFFFFFFULL); if (rc != DOCA_SUCCESS) goto fail;

    /* Teardown */
    doca_dpa_thread_destroy(thr);
    doca_sync_event_destroy(se);
    doca_dpa_destroy(dpa);
    doca_dev_close(dev);
    return 0;

fail:
    fprintf(stderr, "DPA run failed\n");
    if (thr) doca_dpa_thread_destroy(thr);
    if (se) doca_sync_event_destroy(se);
    if (dpa) doca_dpa_destroy(dpa);
    if (dev) doca_dev_close(dev);
    return 1;
}

#else /* !HAVE_DOCA */

static void usage(const char* prog) {
    (void)prog;
}

int main(int argc, char** argv) {
    (void)argc; (void)argv;
    fprintf(stderr, "DOCA headers not available at build time.\n");
    return 1;
}

#endif /* HAVE_DOCA */


