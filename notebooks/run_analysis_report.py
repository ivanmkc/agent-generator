#!/usr/bin/env python3
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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
        # Access lists safely
        pos = case.get('positive_ctxs', []) or []
        neg = case.get('negative_ctxs', []) or []
        
        candidates = pos + neg
        for ctx in candidates:
            meta = ctx.get('metadata', {})
            records.append({
                'case_id': case['id'],
                'query': case['query'],
                'fqn': ctx['fqn'],
                'source_type': ctx['type'], # gold, retrieved, negative
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
    
    # 1. Relevance Distribution
    print("\n--- Relevance Distribution by Source ---")
    relevance_counts = df.groupby(['source_type', 'empirical_relevance']).size().unstack(fill_value=0)
    print(relevance_counts)
    
    plt.figure()
    relevance_counts.plot(kind='bar', stacked=True, colormap='viridis')
    plt.title('Empirical Relevance by Source Type')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("notebooks/report/relevance_distribution.png")
    print("Saved notebooks/report/relevance_distribution.png")

    # 2. Impact Score Distribution
    print("\n--- Impact Score (Delta P) Distribution ---")
    plt.figure()
    sns.histplot(data=df, x='delta_p', hue='empirical_relevance', bins=20, multiple="stack")
    plt.title('Distribution of Impact Scores (Delta P)')
    plt.xlabel('Delta P (P_in - P_out)')
    plt.tight_layout()
    plt.savefig("notebooks/report/impact_score_dist.png")
    print("Saved notebooks/report/impact_score_dist.png")

    # 3. High Impact Contexts
    print("\n--- Top 10 High Impact Contexts ---")
    top_impact = df[df['empirical_relevance'] == 'YES'].sort_values('delta_p', ascending=False).head(10)
    if not top_impact.empty:
        print(top_impact[['fqn', 'delta_p', 'source_type', 'n_in']].to_markdown(index=False))
    else:
        print("No YES relevance contexts found.")

if __name__ == "__main__":
    analyze_report()
