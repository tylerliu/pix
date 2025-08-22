char *d = (char *)rte_pktmbuf_mtod(bufs[0], void *);
char *s = (char *)rte_pktmbuf_mtod(bufs[0], void *);
rte_memcpy(d, s, size);
// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'copy_size': %u, 'alignment': 'packet_aligned'}\n", size);
}

