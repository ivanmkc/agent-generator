import json
import glob
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from core.config import VERIFICATION_RUNS_DIR

def generate_report(run_id: str = None):
    # Find all runs
    report_files = glob.glob(str(VERIFICATION_RUNS_DIR / '*' / '*' / 'report.json'))
    runs = {}
    for r in report_files:
        run_dt = Path(r).parts[-3]
        runs.setdefault(run_dt, []).append(r)
    
    if not runs:
        print("No verification runs found.")
        return
        
    if not run_id:
        # Get latest run directory
        run_id = max(runs.keys())
        
    print(f"Generating Post-Run Report for run: {run_id}")
    
    cases = runs.get(run_id, [])
    
    verdict_counts = {"Valid": 0, "Incorrect": 0, "Ambiguous": 0, "Unknown": 0}
    detailed_findings = []
    
    for case_path in cases:
        with open(case_path, 'r') as f:
            try:
                data = json.load(f)
                verdict = data.get('verdict', 'Unknown')
                case_id = data.get('id', 'unknown_case')
                details = data.get('details', {}).get('details', '')

                claims_data = data.get('claims', [])
                
                # Extract new fields
                question = data.get('question', '')
                expected_answer = data.get('expected_answer', '')
                options = data.get('options', {})

                
                # Load verification summary if it exists
                case_dir = Path(case_path).parent
                summary_path = case_dir / "workspace_files" / "verification_summary.txt"
                verification_summary = ""
                if summary_path.exists():
                    with open(summary_path, 'r') as sf:
                        verification_summary = sf.read().strip()
                        
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
                
                detailed_findings.append({
                    "id": case_id,
                    "verdict": verdict,
                    "details": details,

                    "claims": claims_data,
                    "question": question,
                    "expected_answer": expected_answer,
                    "options": options,
                    "verification_summary": verification_summary,

                    "artifact_path": str(case_dir)
                })
            except Exception as e:
                print(f"Error parsing {case_path}: {e}")
                
    # Build Markdown Report
    report_content = [
        f"# Benchmark Multi-Choice Verification Post-Run Report",
        f"**Run ID:** `{run_id}`",
        f"**Total Cases Verified:** {len(cases)}\n",
        "## Summary",
        f"- **✅ Valid:** {verdict_counts.get('Valid', 0)}",
        f"- **❌ Incorrect:** {verdict_counts.get('Incorrect', 0)}",
        f"- **⚠️ Ambiguous:** {verdict_counts.get('Ambiguous', 0)}",
        f"- **❓ Unknown:** {verdict_counts.get('Unknown', 0)}\n",
        "## Detailed Findings"
    ]
    
    # Sort detailed_findings (Not Valid cases first)
    detailed_findings.sort(key=lambda x: 0 if x['verdict'] != 'Valid' else 1)
    
    for idx, finding in enumerate(detailed_findings, 1):
        icon = "✅" if finding['verdict'] == "Valid" else "❌" if finding['verdict'] == "Incorrect" else "⚠️" if finding['verdict'] == "Ambiguous" else "❓"
        report_content.append(f"### {idx}. {finding['id']}")
        report_content.append(f"**Verdict:** {icon} {finding['verdict']}\n")
        

        # Only print details if it's NOT valid (to keep report concise)
        if finding['verdict'] != 'Valid' and finding['details']:
            report_content.append(f"> **Reasoning:** {finding['details']}\n")
            
        if finding.get('question'):
            report_content.append("<details>")
            report_content.append("<summary><b>Original Question & Options</b></summary>\n")
            report_content.append(f"**Question:** {finding.get('question', '')}")
            for opt_key, opt_val in finding.get('options', {}).items():
                report_content.append(f"- **{opt_key}**: {opt_val}")
            report_content.append(f"\n**Expected Target:** Option {finding.get('expected_answer', '')}\n")
            report_content.append("</details>\n")

            
        if finding.get('claims', []) or finding.get('verification_summary', ''):
            report_content.append("<details>")
            report_content.append("<summary><b>Claim-by-Claim Breakdown</b></summary>\n")
            
            if finding.get('claims', []):
                report_content.append("#### Evaluated Claims:")
                for claim in finding.get('claims', []):
                    report_content.append(f"- **Option {claim.get('option')}**\n  - **Expectation**: {claim.get('hypothesis')}")
                report_content.append("")
                
            if finding.get('verification_summary', ''):
                report_content.append("#### Proof Engineer Execution Summary:")
                report_content.append("```text")
                report_content.append(finding.get('verification_summary', ''))
                report_content.append("```\n")
                
            report_content.append("</details>\n")
        
        report_content.append(f"*[View Artifacts]({finding['artifact_path']})*\n")
        report_content.append("---\n")
        
    out_path = Path("data") / "verification_reports" / f"quality_report_{run_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        f.write("\n".join(report_content))
        
    print(f"Post-run report successfully generated at: {out_path}")

if __name__ == "__main__":
    import sys
    run_target = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(run_target)
