#!/usr/bin/env python3
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
import sys
import re

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))
# Add tools dir to path
sys.path.append(str(Path(__file__).parent))

from retrieval_benchmark_lib import (
    RetrievalDataset, RetrievalCase, RetrievalContext
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RetrievalDataExtractor:
    def __init__(self, ranked_targets_path: str, benchmarks_root: str):
        self.ranked_targets_path = Path(ranked_targets_path)
        self.benchmarks_root = Path(benchmarks_root)
        self.targets_index: Dict[str, Dict[str, Any]] = {} 
        self.name_to_fqn: Dict[str, List[str]] = {} 
        self.all_fqns: List[str] = []
        self.dataset = RetrievalDataset(cases=[])

    def load_ranked_targets(self):
        """Loads ranked_targets.yaml into an efficient index."""
        if not self.ranked_targets_path.exists():
            raise FileNotFoundError(f"Ranked targets not found at {self.ranked_targets_path}")
        
        logger.info(f"Loading targets from {self.ranked_targets_path}...")
        with open(self.ranked_targets_path, 'r') as f:
            targets = yaml.safe_load(f)
        
        if not isinstance(targets, list):
            targets = targets.get('targets', [])
        
        for t in targets:
            fqn = t.get('id')
            name = t.get('name')
            if fqn:
                self.targets_index[fqn] = t
                self.all_fqns.append(fqn)
                if name:
                    if name not in self.name_to_fqn:
                        self.name_to_fqn[name] = []
                    self.name_to_fqn[name].append(fqn)
        logger.info(f"Loaded {len(self.targets_index)} targets.")

    def extract_multiple_choice(self, file_path: Path):
        """Extracts queries from multiple choice benchmarks."""
        if not file_path.exists():
            logger.warning(f"Benchmark file not found: {file_path}")
            return

        logger.info(f"Processing MC: {file_path}...")
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        benchmarks = data.get('benchmarks', [])
        for b in benchmarks:
            if b.get('benchmark_type') != 'multiple_choice':
                continue
                
            qid = b.get('id')
            query = b.get('question')
            
            # Heuristic Gold Mining from explanation and options
            text_to_search = (b.get('explanation', '') or '') + " " + " ".join(b.get('options', {}).values())
            gold_fqns = self._mine_fqns_from_text(text_to_search)
            
            positive_ctxs = []
            for fqn in gold_fqns:
                target = self.targets_index.get(fqn)
                if target:
                    positive_ctxs.append(RetrievalContext(
                        fqn=fqn,
                        text=target.get('docstring', 'No docstring available.'),
                        type="gold_mined"
                    ))
            
            # For MC, we still want to evaluate retrieval even if we don't find gold context statically.
            # But the validator will need context to answer. 
            # We'll rely on the dynamic retriever in the validator to find the "real" gold.
            
            self.dataset.cases.append(RetrievalCase(
                id=qid,
                query=query,
                positive_ctxs=positive_ctxs,
                source="multiple_choice",
                metadata={"options": b.get("options")},
                ground_truth={
                    "correct_answer": b.get("correct_answer"),
                    "options": b.get("options"),
                    "explanation": b.get("explanation"),
                    "benchmark_type": "multiple_choice"
                }
            ))

    def _mine_fqns_from_text(self, text: str) -> List[str]:
        """Attempts to find ADK class names or FQNs in text."""
        fqns = set()
        # Look for things that look like FQNs
        matches = re.findall(r'google\.adk\.[a-zA-Z0-9_\.]+', text)
        for m in matches:
            fqns.add(m.rstrip('.'))
            
        # Look for things in backticks that might be class names
        matches = re.findall(r'`([A-Z][a-zA-Z0-9]+)`', text)
        for name in matches:
            if name in self.name_to_fqn:
                fqns.add(self.name_to_fqn[name][0])
                
        return list(fqns)

    def save_dataset(self, output_path: str):
        logger.info(f"Saving {len(self.dataset.cases)} cases to {output_path}...")
        data = self.dataset.model_dump(by_alias=True)
        with open(output_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)

if __name__ == "__main__":
    extractor = RetrievalDataExtractor(
        ranked_targets_path="benchmarks/benchmark_generator/data/ranked_targets.yaml",
        benchmarks_root="benchmarks"
    )
    extractor.load_ranked_targets()
    
    # Restrict to MC files
    mc_files = [
        "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
        "benchmarks/benchmark_definitions/diagnose_setup_errors_mc/benchmark.yaml",
        "benchmarks/benchmark_definitions/predict_runtime_behavior_mc/benchmark.yaml"
    ]
    
    for f in mc_files:
        extractor.extract_multiple_choice(Path(f))
        
    extractor.save_dataset("retrieval_dataset.yaml")