#!/usr/bin/env python3
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RetrievalContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fqn: str = Field(..., description="Fully qualified name of the target.")
    text: str = Field(..., description="The docstring or content of the context.")
    context_type: Literal["gold", "gold_inferred", "negative"] = Field(..., alias="type")

class RetrievalCase(BaseModel):
    id: str = Field(..., description="Unique identifier for the retrieval case.")
    query: str = Field(..., description="The natural language query or question.")
    positive_ctxs: List[RetrievalContext] = Field(default_factory=list)
    negative_ctxs: List[RetrievalContext] = Field(default_factory=list)
    source: str = Field(..., description="The benchmark suite source.")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ground_truth: Dict[str, Any] = Field(default_factory=dict, description="Data required for empirical validation.")

class RetrievalDataset(BaseModel):
    cases: List[RetrievalCase] = Field(default_factory=list)

class RetrievalDataExtractor:
    def __init__(self, ranked_targets_path: str, benchmarks_root: str):
        self.ranked_targets_path = Path(ranked_targets_path)
        self.benchmarks_root = Path(benchmarks_root)
        self.targets_index: Dict[str, Dict[str, Any]] = {} # FQN -> Target Raw Data
        self.name_to_fqn: Dict[str, List[str]] = {} # Class Name -> List[FQN]
        self.all_fqns: List[str] = []
        self.dataset = RetrievalDataset()

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

    def _sample_negatives(self, exclude_fqns: List[str], count: int = 5) -> List[RetrievalContext]:
        """Samples random negative contexts."""
        import random
        negatives = []
        attempts = 0
        while len(negatives) < count and attempts < 100:
            attempts += 1
            candidate_fqn = random.choice(self.all_fqns)
            if candidate_fqn not in exclude_fqns:
                target = self.targets_index[candidate_fqn]
                negatives.append(RetrievalContext(
                    fqn=candidate_fqn,
                    text=target.get('docstring', 'No docstring available.'),
                    type="negative"
                ))
        return negatives

    def extract_api_understanding(self):
        """Extracts queries from api_understanding benchmarks."""
        bm_path = self.benchmarks_root / "benchmark_definitions/api_understanding/benchmark.yaml"
        if not bm_path.exists():
            logger.warning(f"Benchmark file not found: {bm_path}")
            return

        logger.info(f"Processing {bm_path}...")
        with open(bm_path, 'r') as f:
            data = yaml.safe_load(f)
        
        benchmarks = data.get('benchmarks', [])
        for b in benchmarks:
            qid = b.get('id')
            query = b.get('question')
            answers = b.get('answers', [])
            
            gold_fqns = []
            for ans in answers:
                fqns = ans.get('fully_qualified_class_name', [])
                if isinstance(fqns, str): fqns = [fqns]
                gold_fqns.extend(fqns)
            
            positive_ctxs = []
            valid_gold_fqns = []
            for fqn in gold_fqns:
                target = self.targets_index.get(fqn)
                if target:
                    positive_ctxs.append(RetrievalContext(
                        fqn=fqn,
                        text=target.get('docstring', 'No docstring available.'),
                        type="gold"
                    ))
                    valid_gold_fqns.append(fqn)
            
            if positive_ctxs:
                negatives = self._sample_negatives(valid_gold_fqns)
                self.dataset.cases.append(RetrievalCase(
                    id=qid,
                    query=query,
                    positive_ctxs=positive_ctxs,
                    negative_ctxs=negatives,
                    source="api_understanding",
                    metadata={"category": b.get("category")},
                    ground_truth={"answers": b.get("answers"), "template": b.get("template")}
                ))

    def extract_fix_errors(self):
        """Extracts queries from fix_error benchmarks."""
        bm_path = self.benchmarks_root / "benchmark_definitions/fix_errors/benchmark.yaml"
        if not bm_path.exists():
            logger.warning(f"Benchmark file not found: {bm_path}")
            return

        logger.info(f"Processing {bm_path}...")
        with open(bm_path, 'r') as f:
            data = yaml.safe_load(f)
        
        benchmarks = data.get('benchmarks', [])
        for b in benchmarks:
            qid = b.get('id')
            query = b.get('description') or b.get('name')
            fixed_file_rel = b.get('fixed_file')
            
            if not fixed_file_rel: continue
                
            fixed_path = self.benchmarks_root.parent / fixed_file_rel
            if not fixed_path.exists(): continue
            
            gold_fqns = self._extract_adk_imports(fixed_path)
            positive_ctxs = []
            valid_gold_fqns = []
            for import_str in gold_fqns:
                # 1. Try exact match
                target = self.targets_index.get(import_str)
                
                # 2. Try by Class Name (e.g., LlmAgent)
                if not target:
                    short_name = import_str.split('.')[-1]
                    candidates = self.name_to_fqn.get(short_name)
                    if candidates:
                        target = self.targets_index.get(candidates[0])
                        import_str = candidates[0] # Update valid FQN

                if target:
                    positive_ctxs.append(RetrievalContext(
                        fqn=import_str,
                        text=target.get('docstring', 'No docstring available.'),
                        type="gold_inferred"
                    ))
                    valid_gold_fqns.append(import_str)
            
            if positive_ctxs:
                negatives = self._sample_negatives(valid_gold_fqns)
                self.dataset.cases.append(RetrievalCase(
                    id=qid,
                    query=query,
                    positive_ctxs=positive_ctxs,
                    negative_ctxs=negatives,
                    source="fix_errors",
                    metadata={"test_file": b.get("test_file")},
                    ground_truth={
                        "test_file": b.get("test_file"),
                        "unfixed_file": b.get("unfixed_file"),
                        "fixed_file": b.get("fixed_file"),
                        "requirements": b.get("requirements"),
                        "error_output": b.get("error_output"),
                        "name": b.get("name"),
                        "description": b.get("description")
                    }
                ))

    def _extract_adk_imports(self, file_path: Path) -> List[str]:
        """Parses a python file and returns a list of google.adk FQNs imported."""
        import ast
        fqns = set()
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("google.adk") or alias.name.startswith("google.genai"):
                            fqns.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module.startswith("google.adk") or node.module.startswith("google.genai")):
                        for alias in node.names:
                            fqns.add(f"{node.module}.{alias.name}")
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
        return list(fqns)

    def save_dataset(self, output_path: str):
        logger.info(f"Saving {len(self.dataset.cases)} pairs to {output_path}...")
        data = self.dataset.model_dump(by_alias=True)
        with open(output_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)

if __name__ == "__main__":
    extractor = RetrievalDataExtractor(
        ranked_targets_path="benchmarks/benchmark_generator/data/ranked_targets.yaml",
        benchmarks_root="benchmarks"
    )
    extractor.load_ranked_targets()
    extractor.extract_api_understanding()
    extractor.extract_fix_errors()
    extractor.save_dataset("retrieval_dataset.yaml")