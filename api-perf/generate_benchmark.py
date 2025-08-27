import argparse
import os

def get_snippet_content(snippet_path):
    if os.path.exists(snippet_path):
        with open(snippet_path, 'r') as f:
            return f.read().strip()
    return ''

def generate_benchmark(function_name, output_file, template_base_dir, benchmark_type):
    benchmark_dir = os.path.join(template_base_dir, benchmark_type)
    template_file = os.path.join(benchmark_dir, 'template.c')
    with open(template_file, 'r') as f:
        template = f.read()

    snippet_path = os.path.join(benchmark_dir, function_name)
    
    call_file = os.path.join(snippet_path, 'call.c')
    setup_file = os.path.join(snippet_path, 'setup.c')
    headers_file = os.path.join(snippet_path, 'headers.c')
    teardown_file = os.path.join(snippet_path, 'teardown.c')

    if not os.path.exists(call_file):
        raise ValueError(f"Snippet file not found for function: {function_name}")

    call = get_snippet_content(call_file)
    benchmark_setup = get_snippet_content(setup_file)
    dpdk_headers = get_snippet_content(headers_file)
    benchmark_teardown = get_snippet_content(teardown_file)

    if function_name == "empty":
        benchmark_loop = '// No-op'
        code = template.replace('// {{BENCHMARK_LOOP}}', benchmark_loop)
        # No need to replace the printf statement for empty benchmarks since it's already correct
    else:
        benchmark_loop = f'        {call}'
        code = template.replace('// {{BENCHMARK_LOOP}}', benchmark_loop)
        # No need to replace the printf statement since it's already correct


    code = code.replace('// {{BENCHMARK_SETUP}}', benchmark_setup)
    code = code.replace('// {{DPDK_HEADERS}}', dpdk_headers)
    code = code.replace('// {{BENCHMARK_TEARDOWN}}', benchmark_teardown)
    code = code.replace('void run_benchmark()', 'void run_benchmark(void)')


    with open(output_file, 'w') as f:
        f.write(code)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate API benchmark source code.')
    parser.add_argument('function', help='The function to benchmark.')
    parser.add_argument('-o', '--output', required=True, help='Output C file.')
    parser.add_argument('-b', '--template_base_dir', required=True, help='Path to the base directory containing benchmark templates (e.g., benchmarks/).')
    parser.add_argument('-t', '--benchmark_type', required=True, help='Type of benchmark (e.g., dpdk, doca).')
    args = parser.parse_args()

    generate_benchmark(args.function, args.output, args.template_base_dir, args.benchmark_type)
    print(f"Successfully generated {args.output} for function {args.function} of type {args.benchmark_type}.")
