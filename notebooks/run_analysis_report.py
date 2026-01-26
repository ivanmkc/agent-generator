#!/usr/bin/env python3
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import sys

# Configure plotting
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

def analyze_report():
    dataset_path = Path("retrieval_dataset_verified.yaml")
    if not dataset_path.exists():
        print(f"File not found: {dataset_path}")
        return

    print(f"Loading {dataset_path}...")
    with open(dataset_path, 'r') as f:
        data = yaml.safe_load(f)
    
    cases = data.get('cases', [])
    print(f"Loaded {len(cases)} cases.")

    # Flatten Candidates into a DataFrame
    records = []
    for case in cases:
        candidates = case.get('candidates', [])
        for ctx in candidates:
            meta = ctx.get('metadata', {})
            records.append({
                'case_id': case['id'],
                'query': case['query'],
                'fqn': ctx['fqn'],
                'source_type': ctx['type'],
                'empirical_relevance': ctx.get('empirical_relevance', 'UNKNOWN'),
                'delta_p': meta.get('delta_p', 0.0),
                'p_in': meta.get('p_in', 0.0),
                'p_out': meta.get('p_out', 0.0),
                'n_in': meta.get('n_in', 0),
                'se_in': meta.get('se_in', 0.0)
            })

    if not records:
        print("No candidates found in dataset.")
        return

    df = pd.DataFrame(records)
    print(f"Total Candidates Analyzed: {len(df)}")
    
    # 1. Relevance Distribution (Using Delta P bins instead of binary)
    print("\n--- Impact Score (Delta P) Stats ---")
    print(df['delta_p'].describe())

    plt.figure()
    sns.histplot(data=df, x='delta_p', hue='source_type', multiple="stack", bins=20)
    plt.title('Impact Score Distribution by Source')
    plt.xlabel('Delta P')
    plt.tight_layout()
    plt.savefig("notebooks/report/impact_score_dist.png")
    print("Saved notebooks/report/impact_score_dist.png")

    # 2. Convergence Analysis
    print("\n--- Convergence Analysis ---")
    if not df[df['n_in'] > 0].empty:
        plt.figure()
        sns.scatterplot(data=df[df['n_in'] > 0], x='n_in', y='se_in', alpha=0.6)
        plt.title('Convergence: Standard Error vs Number of Samples')
        plt.xlabel('Number of Trials (Included)')
        plt.ylabel('Standard Error of p_in')
        
        # Theoretical curve
        x = np.linspace(1, df['n_in'].max(), 100)
        y = 0.5 / np.sqrt(x)
        plt.plot(x, y, 'r--', label='Theoretical 1/sqrt(n)')
        plt.legend()
        plt.tight_layout()
        plt.savefig("notebooks/report/convergence_plot.png")
        print("Saved notebooks/report/convergence_plot.png")

    # 3. High Impact Contexts
    print("\n--- Top 10 High Impact Contexts ---")
    top_impact = df.sort_values('delta_p', ascending=False).head(10)
    if not top_impact.empty:
        print(top_impact[['fqn', 'delta_p', 'se_in', 'source_type']])
    else:
        print("No high impact contexts found.")

if __name__ == "__main__":
    analyze_report()