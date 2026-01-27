import json
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Rank targets by Conditional Probability")
    parser.add_argument("--context", type=str, default="google.adk.agents", help="The module you are already testing")
    parser.add_argument("--data", type=str, default="benchmarks/adk_cooccurrence.json", help="Path to association data")
    parser.add_argument("--top", type=int, default=20, help="Show top N")
    
    args = parser.parse_args()
    
    if not Path(args.data).exists():
        print(f"Data file not found: {args.data}. Run tools/cooccurrence_indexer.py first.")
        sys.exit(1)
        
    with open(args.data, "r") as f:
        data = json.load(f)
        
    associations = data.get("associations", [])
    
    # Filter for target modules given our context
    related = [r for r in associations if r["context"] == args.context]
    
    if not related:
        # Fallback: maybe the context itself is the target? Search for it as target
        inverse = [r for r in associations if r["target"] == args.context]
        if inverse:
             print(f"Warning: No explicit data for P(Target | {args.context}). Showing inverse P({args.context} | Context):")
             related = inverse
             # Swap target/context for display
             for r in related:
                 r["context"], r["target"] = r["target"], r["context"]
        else:
             print(f"No associations found for module: {args.context}")
             sys.exit(0)

    # Sort by Probability
    related.sort(key=lambda x: (x["probability"], x["support"]),
                 reverse=True)
    
    print(f"\nASSOCIATION RANKING: Given usage of '{args.context}'")
    print(f"{ 'Rank':<5} | { 'Prob':<6} | { 'Target Module':<50} | { 'Support (Count)'}")
    print("-" * 100)
    
    for i, r in enumerate(related[:args.top]):
        print(f"{i+1:<5} | {r['probability']:<6.2f} | {r['target']:<50} | {r['support']}")

if __name__ == "__main__":
    main()
