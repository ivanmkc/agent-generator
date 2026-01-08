"""
Tool for generating benchmark reports and managing run metadata.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import jinja2
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Metadata Models ---

class GeneratorMetadata(BaseModel):
    """Metadata about an answer generator configuration."""
    name: str
    model_name: Optional[str] = None
    description: Optional[str] = None
    image_name: Optional[str] = None # For Docker/Podman generators

class SuiteMetadata(BaseModel):
    """Metadata about a benchmark suite."""
    name: str
    path: str
    case_count: int
    description: Optional[str] = None

class RunMetadata(BaseModel):
    """Container for static metadata about a benchmark run."""
    run_id: str
    timestamp: str
    generators: List[GeneratorMetadata]
    suites: List[SuiteMetadata]

# --- Functions ---

def save_run_metadata(
    run_id: str,
    output_dir: Path,
    generators: List[Any], # List[AnswerGenerator]
    suites_paths: List[str]
) -> None:
    """
    Extracts metadata from generators and suites and saves it to run_metadata.json.
    
    Args:
        run_id: The unique ID of the run.
        output_dir: The directory where results are saved.
        generators: List of AnswerGenerator instances.
        suites_paths: List of paths to suite YAML files.
    """
    
    # Extract Generator Metadata
    gen_meta_list = []
    for g in generators:
        # Try to extract common attributes safely
        model_name = getattr(g, "model_name", "Unknown")
        desc = getattr(g, "description", None)
        image_name = getattr(g, "image_name", None)
        
        gen_meta_list.append(GeneratorMetadata(
            name=g.name,
            model_name=model_name,
            description=desc,
            image_name=image_name
        ))

    # Extract Suite Metadata
    suite_meta_list = []
    for s_path in suites_paths:
        path_obj = Path(s_path)
        name = path_obj.parent.name # e.g. "fix_errors" from ".../fix_errors/benchmark.yaml"
        
        # Simple count estimation (reading file)
        count = 0
        try:
            import yaml
            with open(path_obj, 'r') as f:
                data = yaml.safe_load(f)
                count = len(data.get('benchmarks', []))
        except Exception as e:
            logger.warning(f"Failed to count cases in {s_path}: {e}")
            
        suite_meta_list.append(SuiteMetadata(
            name=name,
            path=s_path,
            case_count=count
        ))

    metadata = RunMetadata(
        run_id=run_id,
        timestamp=datetime.now().isoformat(),
        generators=gen_meta_list,
        suites=suite_meta_list
    )
    
    output_path = output_dir / "run_metadata.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))
        logger.info(f"Run metadata saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save run metadata: {e}")

def generate_report(run_dir: Path, template_path: Path = Path("benchmarks/templates/report_template.md")) -> Optional[Path]:
    """
    Generates a Markdown report for a specific run directory.
    
    Args:
        run_dir: The directory containing results.json and run_metadata.json.
        template_path: Path to the Jinja2 template file.
        
    Returns:
        Path to the generated report file, or None if failed.
    """
    results_path = run_dir / "results.json"
    metadata_path = run_dir / "run_metadata.json"
    
    if not results_path.exists():
        logger.error(f"results.json not found in {run_dir}")
        return None
        
    # Load Data
    try:
        with open(results_path, "r") as f:
            results_data = json.load(f)
            
        metadata = None
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            logger.warning(f"run_metadata.json not found in {run_dir}. Report will miss configuration details.")
            metadata = {
                "run_id": run_dir.name, 
                "timestamp": datetime.now().isoformat(),
                "generators": [], 
                "suites": []
            }
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return None

    # Calculate Statistics
    # Flatten results if needed (though results.json is usually a flat list)
    if isinstance(results_data, dict): # Handle wrapped JSON if applicable
        results_list = results_data.get("results", [])
    else:
        results_list = results_data

    total_benchmarks = len(results_list)
    total_passed = sum(1 for r in results_list if r.get("result") == 1)
    overall_pass_rate = total_passed / total_benchmarks if total_benchmarks > 0 else 0.0
    
    total_duration = sum(r.get("latency", 0) for r in results_list)
    total_tokens = sum(
        (r.get("usage_metadata") or {}).get("total_tokens") or 0 
        for r in results_list
    )

    # Per-Generator Stats
    gen_stats = {}
    for r in results_list:
        g_name = r.get("answer_generator", "Unknown")
        if g_name not in gen_stats:
            gen_stats[g_name] = {
                "name": g_name, "total": 0, "passed": 0, "total_latency": 0.0, "total_tokens": 0
            }
        
        stat = gen_stats[g_name]
        stat["total"] += 1
        if r.get("result") == 1:
            stat["passed"] += 1
        stat["total_latency"] += r.get("latency", 0)
        stat["total_tokens"] += (r.get("usage_metadata") or {}).get("total_tokens") or 0

    gen_stats_list = []
    for g_name, stat in gen_stats.items():
        stat["pass_rate"] = stat["passed"] / stat["total"] if stat["total"] > 0 else 0.0
        stat["avg_latency"] = stat["total_latency"] / stat["total"] if stat["total"] > 0 else 0.0
        gen_stats_list.append(stat)
    
    # Sort by pass rate desc
    gen_stats_list.sort(key=lambda x: x["pass_rate"], reverse=True)
    
    top_performer = gen_stats_list[0] if gen_stats_list else {"name": "N/A", "pass_rate": 0}
    
    # Identification of efficiency
    most_efficient = min(gen_stats_list, key=lambda x: x["total_tokens"]) if gen_stats_list else {"name": "N/A"}
    
    low_performers = [g["name"] for g in gen_stats_list if g["pass_rate"] < 0.5]

    # Failed Cases
    failed_cases = [r for r in results_list if r.get("result") != 1]

    # Render Template
    try:
        with open(template_path, "r") as f:
            template_content = f.read()
        
        template = jinja2.Template(template_content)
        
        report_content = template.render(
            run_id=metadata.get("run_id"),
            date=metadata.get("timestamp"),
            total_benchmarks=total_benchmarks,
            total_passed=total_passed,
            overall_pass_rate=overall_pass_rate,
            total_duration=total_duration,
            total_tokens=total_tokens,
            generators=metadata.get("generators", []),
            suites=metadata.get("suites", []),
            generator_stats=gen_stats_list,
            failed_cases=failed_cases,
            top_performer=top_performer,
            most_efficient=most_efficient,
            low_performers=low_performers
        )
        
        report_path = run_dir / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        logger.info(f"Report generated at {report_path}")
        return report_path
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate benchmark report.")
    parser.add_argument("run_dir", help="Path to the run directory containing results.json")
    parser.add_argument("--template", help="Path to custom template", default="benchmarks/templates/report_template.md")
    
    args = parser.parse_args()
    
    generate_report(Path(args.run_dir), Path(args.template))
