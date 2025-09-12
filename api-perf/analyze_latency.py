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
from scipy.stats import linregress
import argparse

def fdr_bh(p_values, alpha=0.05):
    """Benjamini–Hochberg FDR control. Returns boolean array of discoveries."""
    p = np.asarray(p_values, dtype=float)
    if p.size == 0:
        return np.array([], dtype=bool)
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    thresholds = alpha * (np.arange(1, m + 1) / m)
    keep = ranked <= thresholds
    if not np.any(keep):
        return np.zeros_like(p, dtype=bool)
    k = np.max(np.where(keep)[0]) + 1
    cutoff = ranked[k - 1]
    return p <= cutoff

def partial_correlation(x, y, controls):
    """Compute partial correlation r(x,y | controls) using residualization.
    x,y: (n,) arrays; controls: (n,k) matrix (k can be 0). Returns (r, p, dof).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if controls is None or controls.size == 0:
        r, p = stats.pearsonr(x, y)
        dof = len(x) - 2
        return r, p, dof
    X = np.column_stack([np.ones(len(x)), controls])
    try:
        beta_x, *_ = np.linalg.lstsq(X, x, rcond=None)
        beta_y, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan, 0
    rx = x - X @ beta_x
    ry = y - X @ beta_y
    # Guard against zero variance
    if np.allclose(np.std(rx), 0) or np.allclose(np.std(ry), 0):
        return np.nan, np.nan, 0
    r, _ = stats.pearsonr(rx, ry)
    k = X.shape[1] - 1  # number of control variables
    dof = len(x) - k - 2
    if dof <= 0 or np.isnan(r):
        return np.nan, np.nan, dof
    # Two-sided p-value from t-statistic
    t = r * np.sqrt((dof) / (1 - r * r + 1e-12))
    p = 2 * (1 - stats.t.cdf(abs(t), dof))
    return r, p, dof

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
    """Calculate per-call latency for each function, subtracting empty benchmark overhead"""
    df = df.copy()
    
    # First, calculate empty benchmark overhead per prefix
    empty_overhead = {}
    for _, row in df[df['function'] == 'empty'].iterrows():
        empty_overhead[row['prefix']] = row['total_cycles'] / row['iterations']
    
    # Subtract empty overhead from total cycles for non-empty functions
    def subtract_empty_overhead(row):
        if row['function'] == 'empty':
            return row['total_cycles']
        elif row['prefix'] in empty_overhead:
            overhead_per_iteration = empty_overhead[row['prefix']]
            total_overhead = overhead_per_iteration * row['iterations']
            return max(0, row['total_cycles'] - total_overhead)  # Don't go negative
        else:
            return row['total_cycles']
    
    df['net_cycles'] = df.apply(subtract_empty_overhead, axis=1)
    df['latency_cycles'] = df['net_cycles'] / df['iterations']
    
    # For functions with metadata, calculate per-operation latency
    def calculate_per_operation_latency(row):
        metadata = row['metadata_parsed']
        if not metadata:
            return row['latency_cycles']
        
        # Handle different metadata types
        if 'total_packets_received' in metadata:
            packets = metadata['total_packets_received']
            if packets > 0:
                return row['net_cycles'] / packets
        elif 'total_packets_sent' in metadata:
            packets = metadata['total_packets_sent']
            if packets > 0:
                return row['net_cycles'] / packets
        
        return row['latency_cycles']
    
    df['latency_per_operation'] = df.apply(calculate_per_operation_latency, axis=1)
    return df

def identify_parameter_types(df, exclude_polling=False):
    """Identify categorical (non-numerical) and numerical parameters in the dataset"""
    categorical_params = set()
    numerical_params = set()
    
    for _, row in df.iterrows():
        metadata = row['metadata_parsed']
        if not metadata:
            continue
            
        for key, value in metadata.items():
            # Exclude polling cycles from main function analysis
            if exclude_polling and key == 'total_poll_cycles':
                continue
                
            if isinstance(value, (int, float)) and not np.isnan(value):
                numerical_params.add(key)
            elif isinstance(value, str):
                categorical_params.add(key)
    
    return categorical_params, numerical_params

def get_categorical_combinations(group):
    """Get all unique combinations of categorical parameters for a function group"""
    if group.empty:
        return []
    
    categorical_params, _ = identify_parameter_types(group)
    if not categorical_params:
        return [{}]  # No categorical parameters, return empty combination
    
    # Get all unique combinations of categorical parameters
    combinations = set()
    for _, row in group.iterrows():
        metadata = row['metadata_parsed']
        if not metadata:
            continue
        
        combo = {}
        for param in categorical_params:
            if param in metadata:
                combo[param] = metadata[param]
        combinations.add(tuple(sorted(combo.items())))
    
    # Convert back to list of dictionaries
    return [dict(combo) for combo in combinations]

def create_case_name(combo):
    """Create a human-readable case name from categorical parameter combination"""
    return ", ".join([f"{k}={v}" for k, v in sorted(combo.items())])

def filter_group_by_categorical_combo(group, combo):
    """Filter a group by categorical parameter combination"""
    if not combo:
        return group
    
    combo_mask = group.apply(lambda row: all(
        row['metadata_parsed'].get(param) == value 
        for param, value in combo.items()
    ), axis=1)
    return group[combo_mask]

def analyze_numerical_parameters(group, numerical_params, *, alpha=0.05, min_unique_values=3, use_fdr=True):
    """Analyze numerical parameters using slopes/intercepts and partial-correlation only.
    Returns all tested parameters with fields:
      - coefficient (slope), intercept, n_samples
      - partial_correlation, partial_p_value, significant
    """
    correlations = {}

    # 1) Collect univariate slopes/intercepts for parameters with sufficient variation
    candidate_params = []
    for param in numerical_params:
        if group['metadata_parsed'].iloc[0] and param in group['metadata_parsed'].iloc[0]:
            param_values = group['metadata_parsed'].apply(lambda x: x.get(param, np.nan))
            valid_mask = ~param_values.isna()
            if valid_mask.sum() > 1:
                x_values = param_values[valid_mask]
                if len(set(x_values)) >= min_unique_values:
                    x_vals = param_values[valid_mask].to_numpy()
                    y_vals = group.loc[valid_mask, 'latency_per_operation'].to_numpy()
                    slope, intercept, _, _, _ = linregress(x_vals, y_vals)
                    correlations[param] = {
                        'coefficient': float(slope),
                        'intercept': float(intercept),
                        'n_samples': int(valid_mask.sum())
                    }
                    candidate_params.append(param)

    # If <2 candidates, partial correlation is not defined; fall back to regular correlation
    if len(candidate_params) < 2:
        for p in candidate_params:
            # For single parameter, use regular correlation and p-value
            x_vals = group['metadata_parsed'].apply(lambda x: x.get(p, np.nan))
            valid_mask = ~x_vals.isna()
            if valid_mask.sum() > 1:
                x_vals = x_vals[valid_mask].to_numpy()
                y_vals = group.loc[valid_mask, 'latency_per_operation'].to_numpy()
                _, _, r_value, p_value, _ = linregress(x_vals, y_vals)
                correlations[p]['partial_correlation'] = float(r_value)
                correlations[p]['partial_p_value'] = float(p_value)
                correlations[p]['significant'] = bool(p_value < alpha)
            else:
                correlations[p]['partial_correlation'] = None
                correlations[p]['partial_p_value'] = None
                correlations[p]['significant'] = False
        return correlations

    # 2) Build matrix and compute partial correlation per variable controlling others
    X_all = []
    y_all = []
    for _, row in group.iterrows():
        meta = row['metadata_parsed']
        if all((k in meta) and pd.notna(meta[k]) for k in candidate_params):
            X_all.append([meta[k] for k in candidate_params])
            y_all.append(row['latency_per_operation'])
    if not X_all:
        for p in candidate_params:
            correlations[p]['partial_correlation'] = None
            correlations[p]['partial_p_value'] = None
            correlations[p]['significant'] = False
        return correlations

    X_all = np.asarray(X_all, dtype=float)
    y_all = np.asarray(y_all, dtype=float)

    partial_ps = []
    for idx, name in enumerate(candidate_params):
        controls_idx = [j for j in range(len(candidate_params)) if j != idx]
        controls = X_all[:, controls_idx]
        r_par, p_par, _ = partial_correlation(X_all[:, idx], y_all, controls)
        correlations[name]['partial_correlation'] = float(r_par) if not np.isnan(r_par) else None
        correlations[name]['partial_p_value'] = float(p_par) if not np.isnan(p_par) else None
        partial_ps.append(p_par if not np.isnan(p_par) else 1.0)

    # 3) BH-FDR on partial p-values to set significance flags
    if use_fdr:
        keep_mask = fdr_bh(partial_ps, alpha=alpha)
        for i, name in enumerate(candidate_params):
            correlations[name]['significant'] = bool(keep_mask[i])
    else:
        for i, name in enumerate(candidate_params):
            correlations[name]['significant'] = bool(partial_ps[i] < alpha)

    return correlations

def analyze_correlations(df, exclude_polling=False):
    """Analyze linear regression coefficients between metadata and performance"""
    correlations = {}
    categorical_params, numerical_params = identify_parameter_types(df, exclude_polling=exclude_polling)
    
    # Group by function
    for function, group in df.groupby('function'):
        func_correlations = {}
        
        # Get categorical parameter combinations for this function
        categorical_combinations = get_categorical_combinations(group)
        
        if categorical_combinations and categorical_combinations != [{}]:
            # Handle categorical parameters by splitting into separate cases
            for combo in categorical_combinations:
                combo_group = filter_group_by_categorical_combo(group, combo)
                
                if len(combo_group) < 2:
                    continue
                
                # Analyze numerical parameters for this categorical case
                case_correlations = analyze_numerical_parameters(combo_group, numerical_params)
                
                if case_correlations:
                    case_name = create_case_name(combo)
                    func_correlations[case_name] = case_correlations
        else:
            # No categorical parameters, analyze all numerical parameters together
            case_correlations = analyze_numerical_parameters(group, numerical_params)
            if case_correlations:
                func_correlations = case_correlations
        
        if func_correlations:
            correlations[function] = func_correlations
    
    return correlations

def perform_multivariate_regression(group, significant_params):
    """Perform multivariate linear regression for significant parameters"""
    if not significant_params:
        return None, None

    # Build design matrix with UNcentered predictors so intercept = base at 0
    X = []
    y = group['latency_per_operation'].values
    for _, row in group.iterrows():
        metadata = row['metadata_parsed']
        x_row = [1.0]
        for param in significant_params:
            x_row.append(metadata.get(param, 0))
        X.append(x_row)
    X = np.array(X, dtype=float)

    if len(X) > 0 and X.shape[1] > 1:
        try:
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            param_coeffs = {}
            for i, param in enumerate(significant_params):
                param_coeffs[param] = round(coeffs[i + 1], 4)
            return param_coeffs, round(coeffs[0], 4)
        except np.linalg.LinAlgError:
            return None, None

    return None, None

def generate_function_latency_map(df, correlations):
    """Generate clean function-to-latency mapping with significant parameters"""
    function_map = {}
    
    for function, group in df.groupby('function'):
        # Get categorical parameter combinations for this function
        categorical_combinations = get_categorical_combinations(group)
        
        if categorical_combinations and categorical_combinations != [{}]:
            # Handle categorical parameters by creating separate cases
            function_data = {}
            
            for combo in categorical_combinations:
                combo_group = filter_group_by_categorical_combo(group, combo)
                
                case_name = create_case_name(combo)
                case_data = generate_case_data(combo_group, function, case_name, correlations)
                
                if case_data:
                    function_data[case_name] = case_data
            
            if function_data:
                function_map[function] = function_data
        else:
            # No categorical parameters, use simple case
            case_data = generate_case_data(group, function, None, correlations)
            if case_data:
                function_map[function] = case_data
    
    return function_map

def generate_case_data(group, function, case_name, correlations):
    """Generate latency data for a single case (categorical or non-categorical)"""
    # Calculate base latency
    base_latency = group['latency_per_operation'].mean()
    case_data = {
        "base_latency_cycles": round(base_latency, 4)
    }
    
    # Check for significant parameters
    if function in correlations:
        if case_name and case_name in correlations[function]:
            # Categorical case
            case_correlations = correlations[function][case_name]
        else:
            # Non-categorical case
            case_correlations = correlations[function]
        
        significant_params = [param for param, stats in case_correlations.items() 
                            if stats['significant']]
        
        if significant_params:
            # Try multivariate regression first
            param_coeffs, intercept = perform_multivariate_regression(group, significant_params)
            
            if param_coeffs is not None:
                case_data["parameters"] = param_coeffs
                case_data["base_latency_cycles"] = intercept
            else:
                # Fall back to individual coefficients
                param_coeffs = {}
                for param in significant_params:
                    param_coeffs[param] = round(case_correlations[param]['coefficient'], 4)
                case_data["parameters"] = param_coeffs
    
    return case_data

def generate_polling_analysis(df):
    """Generate polling/wait time analysis with regression coefficients"""
    # Create a modified dataframe with polling cycles as the main metric
    polling_df = df.copy()
    
    # Calculate empty benchmark overhead per prefix (same as in calculate_latency)
    empty_overhead = {}
    for _, row in df[df['function'] == 'empty'].iterrows():
        empty_overhead[row['prefix']] = row['total_cycles'] / row['iterations']
    
    # Calculate polling time per iteration for each row, subtracting empty overhead
    def calculate_polling_latency(row):
        metadata = row['metadata_parsed']
        if 'total_poll_cycles' in metadata:
            poll_cycles = metadata['total_poll_cycles']
            # Subtract empty overhead from polling cycles
            if row['prefix'] in empty_overhead:
                overhead_per_iteration = empty_overhead[row['prefix']]
                total_overhead = overhead_per_iteration * row['iterations']
                poll_cycles = max(0, poll_cycles - total_overhead)
            return poll_cycles / row['iterations']
        return np.nan
    
    polling_df['latency_per_operation'] = polling_df.apply(calculate_polling_latency, axis=1)
    
    # Filter out rows without polling data
    polling_df = polling_df.dropna(subset=['latency_per_operation'])
    
    if polling_df.empty:
        return {}, {}
    
    # Use the same analysis logic as the main function latency map
    # But exclude total_poll_cycles from being a parameter since it's the dependent variable
    polling_correlations = analyze_correlations(polling_df, exclude_polling=True)
    polling_data = generate_function_latency_map(polling_df, polling_correlations)
    
    # Rename the base latency field to be more specific for polling and fix zero values
    for function, data in polling_data.items():
        function_group = polling_df[polling_df['function'] == function]
        
        if isinstance(data, dict) and any(isinstance(v, dict) and 'base_latency_cycles' in v for v in data.values()):
            # Categorical cases
            for case_name, case_data in data.items():
                if isinstance(case_data, dict) and 'base_latency_cycles' in case_data:
                    base_latency = case_data.pop('base_latency_cycles')
                    
                    # If base latency is essentially zero or negative, calculate mean for this case
                    if abs(base_latency) < 1e-6 or base_latency < 0:
                        case_polling_data = function_group[function_group.apply(lambda row: 
                            all(row['metadata_parsed'].get(param) == value 
                                for param, value in dict([item.split('=') for item in case_name.split(', ') if '=' in item]).items()
                            ), axis=1)]['latency_per_operation']
                        base_latency = np.mean(case_polling_data)
                    
                    case_data['base_poll_cycles_per_iteration'] = round(base_latency, 4)
        elif isinstance(data, dict) and 'base_latency_cycles' in data:
            # Non-categorical case
            base_latency = data.pop('base_latency_cycles')
            
            # If base latency is essentially zero or negative, calculate mean
            if abs(base_latency) < 1e-6 or base_latency < 0:
                base_latency = np.mean(function_group['latency_per_operation'])
            
            data['base_poll_cycles_per_iteration'] = round(base_latency, 4)
    
    return polling_correlations, polling_data

def main():
    parser = argparse.ArgumentParser(description='Analyze API performance benchmark results')
    parser.add_argument('--csv-dir', default='.', 
                       help='Directory containing CSV files (default: current directory)')
    parser.add_argument('--output', default='analysis-results/function_latency_map.json',
                       help='Output JSON file (default: analysis-results/function_latency_map.json)')
    parser.add_argument('--polling-map', default='analysis-results/polling_latency_map.json',
                       help='Output polling latency map JSON file (default: analysis-results/polling_latency_map.json)')
    parser.add_argument('--polling-correlations', default='analysis-results/polling_correlations.json',
                       help='Output polling correlations JSON file (default: analysis-results/polling_correlations.json)')
    parser.add_argument('--correlations', default='analysis-results/correlations.json',
                       help='Output correlations JSON file (default: analysis-results/correlations.json)')
    
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
    
    # Analyze correlations (exclude polling cycles from main analysis)
    print("Analyzing correlations...")
    correlations = analyze_correlations(df, exclude_polling=True)
    
    # Generate function latency map
    print("Generating function latency map...")
    function_map = generate_function_latency_map(df, correlations)
    
    # Generate polling analysis
    print("Generating polling analysis...")
    polling_correlations, polling_data = generate_polling_analysis(df)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Save results
    print(f"Saving function latency map to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(function_map, f, indent=2)
    
    print(f"Saving polling latency map to {args.polling_map}...")
    with open(args.polling_map, 'w') as f:
        json.dump(polling_data, f, indent=2)
    
    print(f"Saving polling correlations to {args.polling_correlations}...")
    with open(args.polling_correlations, 'w') as f:
        json.dump(polling_correlations, f, indent=2)
    
    print(f"Saving correlations to {args.correlations}...")
    with open(args.correlations, 'w') as f:
        json.dump(correlations, f, indent=2)
    
    # Print summary
    print("\n=== LATENCY ANALYSIS SUMMARY ===")
    print(f"Analyzed {len(function_map)} functions across {df['condition'].nunique()} conditions")
    
    print(f"\nFunctions with significant parameters:")
    for func, data in function_map.items():
        if isinstance(data, dict):
            # Check if this function has categorical parameter cases (nested structure)
            has_categorical_cases = any(
                isinstance(v, dict) and 'base_latency_cycles' in v 
                for v in data.values()
            )
            
            if has_categorical_cases:
                # This function has categorical parameter cases
                print(f"  {func}:")
                for case_name, case_data in data.items():
                    if isinstance(case_data, dict) and 'base_latency_cycles' in case_data:
                        if 'parameters' in case_data:
                            params_str = ", ".join([f"{k}: {v}" for k, v in case_data['parameters'].items()])
                            print(f"    {case_name}: base={case_data['base_latency_cycles']} cycles, params=[{params_str}]")
                        else:
                            print(f"    {case_name}: base={case_data['base_latency_cycles']} cycles")
            elif 'parameters' in data:
                # This function has no categorical parameters but has significant numerical parameters
                params_str = ", ".join([f"{k}: {v}" for k, v in data['parameters'].items()])
                print(f"  {func}: base={data['base_latency_cycles']} cycles, params=[{params_str}]")
        else:
            print(f"  {func}: base={data['base_latency_cycles']} cycles")
    
    print(f"\nResults saved to:")
    print(f"  - Function latency map: {args.output}")
    print(f"  - Polling latency map: {args.polling_map}")
    print(f"  - Correlations: {args.correlations}")
    print(f"  - Polling correlations: {args.polling_correlations}")

if __name__ == '__main__':
    main()
