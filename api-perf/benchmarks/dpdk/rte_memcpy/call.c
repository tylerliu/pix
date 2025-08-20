char *d = (char *)rte_pktmbuf_mtod(bufs[0], void *);
char *s = (char *)rte_pktmbuf_mtod(bufs[0], void *);
rte_memcpy(d, s, 64);
// Print metadata after the loop
if (i == g_iterations - 1) {
    printf("metadata: {'copy_size': 64, 'alignment': 'packet_aligned'}\n");
}

