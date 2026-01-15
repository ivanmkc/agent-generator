import sqlite3
import json
import pandas as pd
from collections import Counter, defaultdict

DB_PATH = "benchmarks/analysis_cache.db"

def analyze_tool_failures():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Target specific failures
    query = """
    SELECT benchmark_name, llm_root_cause, llm_analysis 
    FROM failures 
    WHERE suite='api_understanding' 
      AND (llm_root_cause LIKE '%Hallucination%' OR llm_root_cause LIKE '%Context Starvation%')
      AND llm_analysis IS NOT NULL
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    tool_usage_stats = defaultdict(int)
    context_quality_stats = defaultdict(int)
    tool_narratives = []

    print(f"Analyzing {len(rows)} failures for Tool Usage patterns...\n")

    for row in rows:
        try:
            analysis = json.loads(row['llm_analysis'])
            
            # Extract Tool Audit
            tool_audit = analysis.get('tool_audit', {})
            # If tool_audit is missing (older analysis), try to infer or skip
            if not isinstance(tool_audit, dict):
                # Attempt to parse if it's a string representation
                continue
            
            # 1. Which tools were attempted?
            tools = tool_audit.get('attempted_tools', [])
            if not tools:
                tool_usage_stats['No Tools Called'] += 1
            else:
                for tool in tools:
                    tool_usage_stats[tool] += 1
            
            # 2. Context Quality
            ctx_quality = tool_audit.get('context_quality', 'Unknown')
            context_quality_stats[ctx_quality] += 1
            
            # 3. Narrative Snippet (Evidence)
            explanation = analysis.get('explanation', '')
            
            # Categorize the failure mode based on explanation keywords
            failure_mode = "Unknown"
            lower_exp = explanation.lower()
            
            if "empty" in lower_exp and ("docstring" in lower_exp or "result" in lower_exp):
                failure_mode = "Empty Output (Bad Query?)"
            elif "not find" in lower_exp or "failed to locate" in lower_exp:
                failure_mode = "Search Failed"
            elif "ignored" in lower_exp:
                failure_mode = "Ignored Context"
            elif "hallucinated" in lower_exp:
                failure_mode = "Hallucination"
            
            tool_narratives.append({
                "benchmark": row['benchmark_name'],
                "tools": tools,
                "quality": ctx_quality,
                "mode": failure_mode,
                "snippet": explanation[:150] + "..."
            })
            
        except json.JSONDecodeError:
            continue

    # --- Report ---
    print("=== Tool Usage Stats ===")
    for tool, count in sorted(tool_usage_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"{tool}: {count}")
    
    print("\n=== Context Quality (as perceived by LLM) ===")
    for status, count in context_quality_stats.items():
        print(f"{status}: {count}")

    print("\n=== Failure Mode Analysis ===")
    modes = Counter([n['mode'] for n in tool_narratives])
    for mode, count in modes.most_common():
        print(f"{mode}: {count}")

    print("\n=== Detailed Examples ===")
    # Group by mode for examples
    df = pd.DataFrame(tool_narratives)
    if not df.empty:
        for mode in modes.keys():
            print(f"\n-- {mode} --")
            examples = df[df['mode'] == mode].head(3)
            for _, ex in examples.iterrows():
                print(f"Case: {ex['benchmark'][:60]}...")
                print(f"Tools: {ex['tools']}")
                print(f"Explanation: {ex['snippet']}")
                print("-" * 20)

if __name__ == "__main__":
    analyze_tool_failures()
