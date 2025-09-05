#!/usr/bin/env python3
"""
Simple Latency Analysis Script for API Performance Benchmarks
"""

import pandas as pd
import numpy as np
import json
import glob
import os
from scipy import stats
import argparse

def parse_metadata(metadata_str: str) -> dict:
    """Parse metadata string into dictionary"""
    if pd.isna(metadata_str) or metadata_str == '{}':
        return {}
    try:
        # Replace single quotes with double quotes for valid JSON
        json_str = metadata_str.replace("'", '"')
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        return {}

def load_benchmark_data(csv_files):
    """Load and combine all benchmark CSV files"""
    all_data = []
    
    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            print(f"Warning: File {csv_file} not found, skipping...")
            continue
            
        # Extract condition info from filename
        filename = os.path.basename(csv_file)
        condition = filename.replace('api_perf_results_', '').replace('.csv', '')
        
        df = pd.read_csv(csv_file)
        df['condition'] = condition
        df['source_file'] = filename
        
        # Parse metadata
        df['metadata_parsed'] = df['metadata'].apply(parse_metadata)
        
        all_data.append(df)
    
    if not all_data:
        raise ValueError("No valid CSV files found")
    
    return pd.concat(all_data, ignore_index=True)

def filter_invalid_rx_burst(df):
    """Remove rx_burst data where no packets were received (burst size too small)"""
    def is_valid_rx_burst(row):
        if row['function'] != 'rte_eth_rx_burst':
            return True
        
        metadata = row['metadata_parsed']
        packets_received = metadata.get('total_packets_received', 0)
        condition = row['condition']
        
        # For '0' condition (no network traffic), it's expected to have 0 packets
        if condition == '0':
            return True
        
        # For other conditions (with network traffic), remove if no packets received
        # This indicates burst size is too small for the network conditions
        return packets_received > 0
    
    print(f"Before filtering: {len(df)} rows")
    df_filtered = df[df.apply(is_valid_rx_burst, axis=1)]
    print(f"After filtering rx_burst with 0 packets (excluding '0' condition): {len(df_filtered)} rows")
    
    return df_filtered

def calculate_latency(df):
    """Calculate per-call latency for each function"""
    df = df.copy()
    df['latency_cycles'] = df['total_cycles'] / df['iterations']
    
    # For functions with metadata, calculate per-operation latency
    def calculate_per_operation_latency(row):
        metadata = row['metadata_parsed']
        if not metadata:
            return row['latency_cycles']
        
        # Handle different metadata types
        if 'total_packets_received' in metadata:
            packets = metadata['total_packets_received']
            if packets > 0:
                return row['total_cycles'] / packets
        elif 'total_packets_sent' in metadata:
            packets = metadata['total_packets_sent']
            if packets > 0:
                return row['total_cycles'] / packets
        elif 'total_poll_cycles' in metadata:
            # For cryptodev-wait benchmarks, total_cycles already has polling time subtracted
            # So we can use it directly
            return row['latency_cycles']
        
        return row['latency_cycles']
    
    df['latency_per_operation'] = df.apply(calculate_per_operation_latency, axis=1)
    return df

def analyze_correlations(df):
    """Analyze linear regression coefficients between metadata and performance"""
    from scipy.stats import linregress
    
    correlations = {}
    
    # Group by function
    for function, group in df.groupby('function'):
        func_correlations = {}
        
        # Analyze burst_size coefficient
        if group['metadata_parsed'].iloc[0] and 'burst_size' in group['metadata_parsed'].iloc[0]:
            burst_sizes = group['metadata_parsed'].apply(lambda x: x.get('burst_size', np.nan))
            valid_mask = ~burst_sizes.isna()
            
            if valid_mask.sum() > 1:
                slope, intercept, r_value, p_value, std_err = linregress(
                    burst_sizes[valid_mask], 
                    group.loc[valid_mask, 'latency_per_operation']
                )
                func_correlations['burst_size'] = {
                    'coefficient': float(slope),
                    'intercept': float(intercept),
                    'correlation': float(r_value),
                    'p_value': float(p_value),
                    'significant': bool(p_value < 0.05),
                    'n_samples': int(valid_mask.sum())
                }
        
        # Analyze packet size coefficient (for tx_burst)
        if group['metadata_parsed'].iloc[0] and 'pkt_size' in group['metadata_parsed'].iloc[0]:
            pkt_sizes = group['metadata_parsed'].apply(lambda x: x.get('pkt_size', np.nan))
            valid_mask = ~pkt_sizes.isna()
            
            if valid_mask.sum() > 1:
                slope, intercept, r_value, p_value, std_err = linregress(
                    pkt_sizes[valid_mask], 
                    group.loc[valid_mask, 'latency_per_operation']
                )
                func_correlations['pkt_size'] = {
                    'coefficient': float(slope),
                    'intercept': float(intercept),
                    'correlation': float(r_value),
                    'p_value': float(p_value),
                    'significant': bool(p_value < 0.05),
                    'n_samples': int(valid_mask.sum())
                }
        
        # Analyze data_size coefficient (for cryptodev)
        if group['metadata_parsed'].iloc[0] and 'data_size' in group['metadata_parsed'].iloc[0]:
            data_sizes = group['metadata_parsed'].apply(lambda x: x.get('data_size', np.nan))
            valid_mask = ~data_sizes.isna()
            
            if valid_mask.sum() > 1:
                slope, intercept, r_value, p_value, std_err = linregress(
                    data_sizes[valid_mask], 
                    group.loc[valid_mask, 'latency_per_operation']
                )
                func_correlations['data_size'] = {
                    'coefficient': float(slope),
                    'intercept': float(intercept),
                    'correlation': float(r_value),
                    'p_value': float(p_value),
                    'significant': bool(p_value < 0.05),
                    'n_samples': int(valid_mask.sum())
                }
        
        if func_correlations:
            correlations[function] = func_correlations
    
    return correlations

def generate_function_latency_map(df, correlations):
    """Generate clean function-to-latency mapping with significant parameters"""
    function_map = {}
    
    for function, group in df.groupby('function'):
        # Calculate base latency (mean across all measurements)
        base_latency = group['latency_per_operation'].mean()
        
        function_data = {
            "base_latency_cycles": round(base_latency, 2)
        }
        
        # Check if this function has significant parameters
        if function in correlations:
            significant_params = []
            for param, stats in correlations[function].items():
                if stats['significant']:
                    significant_params.append(param)
            
            if significant_params:
                # Do multivariate linear regression with all significant parameters
                X = []
                y = group['latency_per_operation'].values
                
                for _, row in group.iterrows():
                    metadata = row['metadata_parsed']
                    x_row = [1.0]  # Add intercept term
                    for param in significant_params:
                        value = metadata.get(param, 0)
                        x_row.append(value)
                    X.append(x_row)
                
                X = np.array(X)
                
                if len(X) > 0 and X.shape[1] > 1:
                    # Solve using normal equation: (X^T X)^-1 X^T y
                    try:
                        coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
                        
                        # Create parameter coefficients dict
                        param_coeffs = {}
                        for i, param in enumerate(significant_params):
                            param_coeffs[param] = round(coeffs[i + 1], 4)  # Skip intercept
                        
                        function_data["parameters"] = param_coeffs
                        # Update base latency to be the intercept
                        function_data["base_latency_cycles"] = round(coeffs[0], 2)
                    except np.linalg.LinAlgError:
                        # Fall back to individual coefficients if multivariate fails
                        param_coeffs = {}
                        for param in significant_params:
                            param_coeffs[param] = round(correlations[function][param]['coefficient'], 4)
                        function_data["parameters"] = param_coeffs
        
        function_map[function] = function_data
    
    return function_map

def generate_polling_analysis(df):
    """Generate polling/wait time analysis with regression coefficients"""
    from scipy.stats import linregress
    
    polling_data = {}
    
    for function, group in df.groupby('function'):
        # Check if this function has polling data
        has_polling = False
        for _, row in group.iterrows():
            metadata = row['metadata_parsed']
            if 'total_poll_cycles' in metadata:
                has_polling = True
                break
        
        if has_polling:
            # Calculate polling time per iteration
            poll_times = []
            burst_sizes = []
            data_sizes = []
            
            for _, row in group.iterrows():
                metadata = row['metadata_parsed']
                if 'total_poll_cycles' in metadata:
                    poll_cycles = metadata['total_poll_cycles']
                    poll_per_iteration = poll_cycles / row['iterations']
                    poll_times.append(poll_per_iteration)
                    
                    # Collect parameters for regression
                    burst_sizes.append(metadata.get('burst_size', 0))
                    data_sizes.append(metadata.get('data_size', 0))
            
            if poll_times:
                # Calculate base polling latency (mean)
                base_poll_latency = np.mean(poll_times)
                
                polling_info = {
                    "base_poll_cycles_per_iteration": round(base_poll_latency, 2)
                }
                
                # Analyze burst_size correlation with polling time
                if len(set(burst_sizes)) > 1:  # Multiple burst sizes
                    slope, intercept, r_value, p_value, std_err = linregress(burst_sizes, poll_times)
                    if "correlations" not in polling_info:
                        polling_info["correlations"] = {}
                    polling_info["correlations"]["burst_size"] = {
                        "coefficient": round(slope, 4),
                        "intercept": round(intercept, 2),
                        "correlation": round(r_value, 4),
                        "p_value": round(p_value, 6),
                        "significant": bool(p_value < 0.05),
                        "n_samples": len(poll_times)
                    }
                    if p_value < 0.05:  # Significant correlation
                        if "parameters" not in polling_info:
                            polling_info["parameters"] = {}
                        polling_info["parameters"]["burst_size"] = round(slope, 4)
                        # Update base to be intercept
                        polling_info["base_poll_cycles_per_iteration"] = round(intercept, 2)
                
                # Analyze data_size correlation with polling time (for cryptodev)
                if len(set(data_sizes)) > 1 and data_sizes[0] > 0:  # Multiple data sizes
                    slope, intercept, r_value, p_value, std_err = linregress(data_sizes, poll_times)
                    if "correlations" not in polling_info:
                        polling_info["correlations"] = {}
                    polling_info["correlations"]["data_size"] = {
                        "coefficient": round(slope, 4),
                        "intercept": round(intercept, 2),
                        "correlation": round(r_value, 4),
                        "p_value": round(p_value, 6),
                        "significant": bool(p_value < 0.05),
                        "n_samples": len(poll_times)
                    }
                    if p_value < 0.05:  # Significant correlation
                        if "parameters" not in polling_info:
                            polling_info["parameters"] = {}
                        polling_info["parameters"]["data_size"] = round(slope, 4)
                        # Update base to be intercept if this is the only significant parameter
                        if "burst_size" not in polling_info.get("parameters", {}):
                            polling_info["base_poll_cycles_per_iteration"] = round(intercept, 2)
                
                # Add basic statistics
                polling_info.update({
                    "std_poll_cycles_per_iteration": round(np.std(poll_times), 2),
                    "n_measurements": len(poll_times)
                })
                
                polling_data[function] = polling_info
    
    return polling_data

def main():
    parser = argparse.ArgumentParser(description='Analyze API performance benchmark results')
    parser.add_argument('--csv-dir', default='.', 
                       help='Directory containing CSV files (default: current directory)')
    parser.add_argument('--output', default='function_latency_map.json',
                       help='Output JSON file (default: function_latency_map.json)')
    parser.add_argument('--polling-output', default='polling_analysis.json',
                       help='Output polling analysis JSON file (default: polling_analysis.json)')
    parser.add_argument('--correlations', default='correlations.json',
                       help='Output correlations JSON file (default: correlations.json)')
    
    args = parser.parse_args()
    
    # Find all CSV files
    csv_pattern = os.path.join(args.csv_dir, 'api_perf_results_*.csv')
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print(f"No CSV files found matching pattern: {csv_pattern}")
        return
    
    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"  - {f}")
    
    # Load and process data
    print("\nLoading benchmark data...")
    df = load_benchmark_data(csv_files)
    print(f"Loaded {len(df)} benchmark results")
    
    # Filter invalid rx_burst data
    print("Filtering invalid rx_burst data...")
    df = filter_invalid_rx_burst(df)
    
    # Calculate latencies
    print("Calculating latencies...")
    df = calculate_latency(df)
    
    # Analyze correlations
    print("Analyzing correlations...")
    correlations = analyze_correlations(df)
    
    # Generate function latency map
    print("Generating function latency map...")
    function_map = generate_function_latency_map(df, correlations)
    
    # Generate polling analysis
    print("Generating polling analysis...")
    polling_data = generate_polling_analysis(df)
    
    # Save results
    print(f"Saving function latency map to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(function_map, f, indent=2)
    
    print(f"Saving polling analysis to {args.polling_output}...")
    with open(args.polling_output, 'w') as f:
        json.dump(polling_data, f, indent=2)
    
    print(f"Saving correlations to {args.correlations}...")
    with open(args.correlations, 'w') as f:
        json.dump(correlations, f, indent=2)
    
    # Print summary
    print("\n=== LATENCY ANALYSIS SUMMARY ===")
    print(f"Analyzed {len(function_map)} functions across {df['condition'].nunique()} conditions")
    
    print(f"\nFunctions with significant parameters:")
    for func, data in function_map.items():
        if 'parameters' in data:
            params_str = ", ".join([f"{k}: {v}" for k, v in data['parameters'].items()])
            print(f"  {func}: base={data['base_latency_cycles']} cycles, params=[{params_str}]")
        else:
            print(f"  {func}: base={data['base_latency_cycles']} cycles")
    
    print(f"\nResults saved to:")
    print(f"  - Function latency map: {args.output}")
    print(f"  - Polling analysis: {args.polling_output}")
    print(f"  - Correlations: {args.correlations}")

if __name__ == '__main__':
    main()
