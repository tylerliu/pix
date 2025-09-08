project('api-benchmark', 'c')

cc = meson.get_compiler('c')

dpdk_dep = dependency('libdpdk', required: true)

benchmark_driver_src = files('driver/benchmark_driver.c')

output_dir = meson.current_build_dir() / 'generated_benchmarks'

run_command('mkdir', '-p', output_dir)

python3 = find_program('python3', required: true)

gen_script = files('generate_benchmark.py')

# Run the generation script
benchmark_configs = {
    'dpdk': [
        'rte_eth_tx_burst',
        'rte_eth_rx_burst',
        'rte_prefetch0',
        'rte_pktmbuf_clone',
        'rte_memcpy',
        'rte_ether_addr_copy',
        'rte_bswap16',
        'rte_bswap32',
        'rte_bswap64',
        'rte_raw_cksum',
        'rte_ipv4_phdr_cksum',
        'rte_ipv4_cksum',
        'rte_ipv4_udptcp_cksum',
        'empty'
    ],
    'cryptodev': [
        'empty',
        'rte_cryptodev_sym_session_create_free',
        'rte_crypto_op_bulk_alloc_free',
        'rte_crypto_op_attach_sym_session',
        'rte_cryptodev_enqueue_dequeue_burst_encrypt',
        'rte_cryptodev_enqueue_dequeue_burst_decrypt'
    ],
    'compressdev': [
        'empty',
        'rte_compressdev_private_xform_create_free',
        'rte_comp_op_bulk_alloc_free',
        'rte_compressdev_enqueue_dequeue_burst_compress',
        'rte_compressdev_enqueue_dequeue_burst_decompress'
    ]
}
generated_sources = []

foreach type, functions : benchmark_configs
    foreach func : functions
        output_file = output_dir / (type + '_' + func + '.c')
        run_result = run_command(python3, gen_script, '-o', output_file, '-b', meson.current_source_dir() / 'benchmarks', '-t', type, func)

        if run_result.returncode() != 0
            error('Benchmark generation failed for ' + type + '/' + func + ': \n' + run_result.stderr())
        endif
        generated_sources += output_file
    endforeach
endforeach

if generated_sources.length() == 0
    error('No benchmark files were generated.')
endif


foreach gen_src : generated_sources
    exe_name = gen_src.split('/')[-1].split('.')[0]
    executable(exe_name,
        sources: [benchmark_driver_src, gen_src],
        dependencies: [dpdk_dep],
        include_directories: include_directories('.'),
        install: true,
        install_dir: 'bin/api_benchmarks')
endforeach
