import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.target_ranker.ranker import TargetRanker
from tools.constants import RANKED_TARGETS_FILE, RANKED_TARGETS_MD

async def main():
    parser = argparse.ArgumentParser(description="Scan repository and generate ranked targets.")
    parser.add_argument("--repo-path", type=str, default="repos/adk-python", help="Path to the repository to scan.")
    parser.add_argument("--stats-file", type=str, default="ai/instructions/knowledge/adk_stats_samples.yaml", help="Path to the usage stats file.")
    parser.add_argument("--output-yaml", type=str, default=str(RANKED_TARGETS_FILE), help="Output YAML path.")
    parser.add_argument("--output-md", type=str, default=str(RANKED_TARGETS_MD), help="Output MD path.")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ranker = TargetRanker(repo_path=args.repo_path, stats_file=args.stats_file)
    await ranker.generate(output_yaml_path=args.output_yaml, output_md_path=args.output_md)

if __name__ == "__main__":
    asyncio.run(main())
