# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Target Ranker module.
Orchestrates the scanning, ranking, and formatting of benchmark targets.
"""

import json
import yaml
import os
import re
import asyncio
import inspect
import textwrap
import logging
import subprocess
from pathlib import Path
from collections import defaultdict
from typing import Optional

from benchmarks.benchmark_generator.tools import scan_repository
from benchmarks.benchmark_generator.models import RankedTarget, MemberInfo
from google.adk.tools import ToolContext
from google.adk.sessions.session import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Configuration
EXEMPTION_PHRASES = [
    "This method is only for use by Agent Development Kit.",
]

# Fields to exclude from reconstructed constructor signatures
CONSTRUCTOR_EXCLUDED_FIELDS = {
    "model_config",      # Universal Pydantic V2 internal; configures model behavior and is never a constructor arg.
    "config_type",       # Universal ADK Agent pattern; a ClassVar used for schema lookups, not instance data.
    "parent_agent",      # Universal framework field for hierarchy management; set automatically when adding sub-agents.
    "last_update_time",  # Universal metadata pattern for stateful objects; tracking is managed by the system/persistence layer.
    "invocation_id",     # Universal framework ID for event correlation; system-generated to ensure uniqueness across the run.
}

class MockAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if False: yield None

class TargetRanker:
    def __init__(self, repo_path: str, namespace: str = "google.adk", stats_file: str = "benchmarks/adk_stats_samples.yaml"):
        self.repo_path = repo_path
        self.namespace = namespace
        self.stats_file = stats_file
        
        # Define external dependencies to scan
        # (path, namespace_prefix)
        self.external_deps = [
            ("env/lib/python3.13/site-packages/google/genai", "google.genai"),
            ("env/lib/python3.13/site-packages/vertexai", "vertexai"),
        ]

    def clean_text(self, text):
        if not text: return None
        try:
            text = inspect.cleandoc(text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text
        except:
            return text.strip()

    def should_include(self, item_entry):
        doc = item_entry.get("docstring")
        if not doc: return True
        for phrase in EXEMPTION_PHRASES:
            if phrase in doc:
                return False
        return True

    async def generate(self, output_yaml_path: str = "benchmarks/benchmark_generator/data/ranked_targets.yaml", output_md_path: str = "benchmarks/benchmark_generator/data/ranked_targets.md"):
        # Ensure output directory exists
        Path(output_yaml_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Setup Context
        session_service = InMemorySessionService()
        session = await session_service.create_session(session_id="gen_rank", user_id="ranker", app_name="ranker")
        
        session.state["repo_path"] = self.repo_path
        session.state["target_namespace"] = self.namespace
        session.state["stats_file_path"] = self.stats_file
        
        inv_context = InvocationContext(
            invocation_id="rank_inv",
            agent=MockAgent(name="ranker_agent"),
            session=session,
            session_service=session_service
        )
        
        context = ToolContext(
            invocation_context=inv_context,
            function_call_id="rank_call",
            event_actions=None,
            tool_confirmation=None
        )
        
        # --- Multi-pass Scanning ---
        all_targets = []
        all_structure = {}
        
        # 1. Scan ADK Repo (Main)
        logger.info(f"Scanning ADK repo: {self.repo_path}...")
        scan_repository(repo_path=self.repo_path, tool_context=context, namespace=self.namespace)
        if "scanned_targets" in session.state:
            all_targets.extend(session.state["scanned_targets"])
        if "structure_map" in session.state:
            all_structure.update(session.state["structure_map"])
            
        # 2. Scan External Dependencies
        for dep_path, dep_ns in self.external_deps:
            if os.path.exists(dep_path):
                logger.info(f"Scanning external dependency: {dep_ns} at {dep_path}...")
                # Clear previous scan results from state to avoid confusion (scan_repository overwrites)
                session.state["scanned_targets"] = []
                session.state["structure_map"] = {}
                
                scan_repository(
                    repo_path=dep_path, 
                    tool_context=context, 
                    namespace=dep_ns,
                    root_namespace_prefix=dep_ns
                )
                
                # Fix paths to be relative to project root
                if "scanned_targets" in session.state and isinstance(session.state["scanned_targets"], list):
                    for t in session.state["scanned_targets"]:
                        if t.get("file_path"):
                            t["file_path"] = os.path.join(dep_path, t["file_path"])
                
                if "scanned_targets" in session.state:
                    all_targets.extend(session.state["scanned_targets"])
                if "structure_map" in session.state:
                    all_structure.update(session.state["structure_map"])
            else:
                logger.warning(f"External dependency path not found: {dep_path}")

        # Restore aggregated data to session state
        session.state["scanned_targets"] = all_targets
        session.state["structure_map"] = all_structure
        
        targets_data = all_targets
        structure_map = all_structure
        
        logger.info(f"Total targets scanned: {len(targets_data)}")
        
        # Inheritance Resolution
        logger.info("Resolving inheritance...")
        adk_inheritance = defaultdict(list)
        external_bases = defaultdict(list)
        
        class_fqns = [k for k, v in structure_map.items() if v["type"] == "Class"]
        
        for cls_fqn in class_fqns:
            bases = structure_map[cls_fqn].get("bases", [])
            for base in bases:
                match = None
                if base in structure_map: match = base
                
                if not match:
                    candidates = [k for k in class_fqns if k.endswith(f".{base}")]
                    if len(candidates) == 1:
                        match = candidates[0]
                    elif len(candidates) > 1:
                        candidates.sort(key=lambda x: len(os.path.commonprefix([x, cls_fqn])), reverse=True)
                        match = candidates[0]
                
                if match:
                    adk_inheritance[cls_fqn].append(match)
                else:
                    external_bases[cls_fqn].append(base)

        # Ranking
        cooccurrence_path = Path("benchmarks/adk_cooccurrence.json")
        entity_map = {t["id"]: t for t in targets_data}
        
        # Load co-occurrence if exists
        associations = []
        if cooccurrence_path.exists():
            with open(cooccurrence_path, "r") as f:
                cooccurrence_data = json.load(f)
                associations = cooccurrence_data.get("associations", [])

        graph = defaultdict(list)
        for a in associations:
            if a["context"] in entity_map and a["target"] in entity_map:
                graph[a["context"]].append(a["target"])
                
        seeds = [t for t in targets_data if t.get("usage_score", 0) > 0]
        seeds.sort(key=lambda t: t.get("usage_score", 0), reverse=True)
        
        ordered_ids = []
        visited = set()
        target_groups = {}
        
        for s in seeds:
            if s["id"] not in visited:
                visited.add(s["id"])
                ordered_ids.append(s["id"])
                target_groups[s["id"]] = "Seed"
                
        idx = 0
        while idx < len(ordered_ids):
            curr_id = ordered_ids[idx]
            idx += 1
            for dep_id in graph.get(curr_id, []):
                if dep_id not in visited:
                    visited.add(dep_id)
                    ordered_ids.append(dep_id)
                    target_groups[dep_id] = "Dependency"
                    
        orphans = [t for t in targets_data if t["id"] not in visited]
        orphans.sort(key=lambda t: t.get("id"))
        
        for o in orphans:
            ordered_ids.append(o["id"])
            target_groups[o["id"]] = "Orphan"

    def _get_methods_for_class(self, cls_fqn, structure_map, entity_map):
        methods = []
        struct = structure_map.get(cls_fqn)
        if not struct: return []
        
        children = struct.get("children", [])
        for child_fqn in children:
            child_name = child_fqn.split(".")[-1]
            if not child_name.startswith("_") or child_name == "_run_async_impl":
                child_struct = structure_map.get(child_fqn)
                if child_struct and child_struct.get("type") != "Method":
                    continue 

                child_entity = entity_map.get(child_fqn)
                sig = child_entity.get("signature_full") if child_entity else None
                if not sig and child_struct:
                        sig = child_struct.get("signature")
                if not sig:
                    sig = f"def {child_name}(...):"
                
                m_doc = child_entity.get("docstring") if child_entity else None
                if not m_doc and child_struct:
                        m_doc = child_struct.get("docstring")
                
                method_entry = {"signature": sig}
                if m_doc:
                    method_entry["docstring"] = self.clean_text(m_doc)
                
                if self.should_include(method_entry):
                    methods.append(MemberInfo(**method_entry))
        return methods

    def _get_properties_for_class(self, cls_fqn, structure_map):
        properties = []
        struct = structure_map.get(cls_fqn)
        if not struct: return []
        
        props = struct.get("props", [])
        for p in props:
            sig = f"{p['name']}: {p['type']}"
            p_doc = p.get("docstring")
            
            prop_entry = {"signature": sig}
            if p_doc:
                prop_entry["docstring"] = self.clean_text(p_doc)
            
            if self.should_include(prop_entry):
                properties.append(MemberInfo(**prop_entry))
        return properties

    def reconstruct_constructor_signature(self, cls_fqn, structure_map, entity_map, adk_inheritance):
        """
        Deterministic reconstruction of constructor signature for classes without explicit __init__.
        Handles Pydantic models by aggregating fields from the MRO.
        """
        struct = structure_map.get(cls_fqn)
        if not struct:
            return None

        # 1. Check for explicit __init__
        children = struct.get("children", [])
        has_init = any(c.split(".")[-1] == "__init__" for c in children)
        if has_init:
            return None # Already has explicit init

        # 2. Analyze MRO to detect Pydantic models, Dataclasses, or inherit parent __init__
        # This uses BFS to gather the hierarchy. 
        # Note: A proper MRO linearization would be better but BFS is a decent proxy for gathering members.
        queue = [cls_fqn]
        visited = {cls_fqn}
        hierarchy = [] 
        
        is_generated_init = False
        first_init_sig = None

        while queue:
            curr = queue.pop(0)
            hierarchy.append(curr)
            
            curr_struct = structure_map.get(curr)
            if not curr_struct: continue
            
            # Check bases for Pydantic marker
            bases = curr_struct.get("bases", [])
            for b in bases:
                if "BaseModel" in b or "pydantic" in b.lower():
                    is_generated_init = True
            
            # Check decorators for Dataclass marker
            decorators = curr_struct.get("decorators", [])
            for d in decorators:
                if "dataclass" in d:
                    is_generated_init = True

            # Check for inherited __init__ (if we haven't found one yet)
            if not first_init_sig and curr != cls_fqn:
                 curr_children = curr_struct.get("children", [])
                 for c in curr_children:
                     if c.endswith(".__init__"):
                         # Found the first parent __init__
                         m_entity = entity_map.get(c)
                         if m_entity:
                             first_init_sig = m_entity.get("signature_full")
            
            # Add parents to queue
            parents = adk_inheritance.get(curr, [])
            for p in parents:
                if p not in visited:
                    visited.add(p)
                    queue.append(p)
        
        if is_generated_init:
            # For Pydantic/Dataclasses, collect all properties (fields) from the hierarchy
            fields = []
            seen_fields = set()
            
            # Traverse roughly base-to-child to emulate init kwarg order (though Pydantic is flexible)
            for ancestor in reversed(hierarchy):
                # Access raw structure map to get 'init_excluded' flag
                struct = structure_map.get(ancestor)
                if not struct: continue
                
                for p in struct.get("props", []):
                    name = p["name"]
                    
                    # DEBUG
                    # if name == "speech_config" or name == "max_llm_calls":
                    #    print(f"[DEBUG] Prop {name}: {p}")

                    # 1. Check init_excluded flag (from ClassVar or Field(init=False))
                    if p.get("init_excluded"):
                        continue
                        
                    # 2. Check blacklist and duplicates
                    if name not in seen_fields and name not in CONSTRUCTOR_EXCLUDED_FIELDS:
                        seen_fields.add(name)
                        # Reconstruct signature part
                        sig = f"{name}: {p['type']}"
                        if p.get("default_value") is not None:
                            sig += f" = {p['default_value']}"
                        fields.append(sig)
            
            if fields:
                return f"def __init__(self, *, {', '.join(fields)}):"
        
        # Fallback: if not Pydantic but we found a parent __init__, use that
        if first_init_sig:
            return first_init_sig

        return None

    async def generate(self, output_yaml_path: str = "benchmarks/benchmark_generator/data/ranked_targets.yaml", output_md_path: str = "benchmarks/benchmark_generator/data/ranked_targets.md"):
        # Ensure output directory exists
        Path(output_yaml_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Setup Context
        session_service = InMemorySessionService()
        session = await session_service.create_session(session_id="gen_rank", user_id="ranker", app_name="ranker")
        
        session.state["repo_path"] = self.repo_path
        session.state["target_namespace"] = self.namespace
        session.state["stats_file_path"] = self.stats_file
        
        inv_context = InvocationContext(
            invocation_id="rank_inv",
            agent=MockAgent(name="ranker_agent"),
            session=session,
            session_service=session_service
        )
        
        context = ToolContext(
            invocation_context=inv_context,
            function_call_id="rank_call",
            event_actions=None,
            tool_confirmation=None
        )
        
        # --- Multi-pass Scanning ---
        all_targets = []
        all_structure = {}
        
        # 1. Scan ADK Repo (Main)
        logger.info(f"Scanning ADK repo: {self.repo_path}...")
        scan_repository(repo_path=self.repo_path, tool_context=context, namespace=self.namespace)
        if "scanned_targets" in session.state:
            all_targets.extend(session.state["scanned_targets"])
        if "structure_map" in session.state:
            all_structure.update(session.state["structure_map"])
            
        # 2. Scan External Dependencies
        for dep_path, dep_ns in self.external_deps:
            if os.path.exists(dep_path):
                logger.info(f"Scanning external dependency: {dep_ns} at {dep_path}...")
                # Clear previous scan results from state to avoid confusion (scan_repository overwrites)
                session.state["scanned_targets"] = []
                session.state["structure_map"] = {}
                
                scan_repository(
                    repo_path=dep_path, 
                    tool_context=context, 
                    namespace=dep_ns,
                    root_namespace_prefix=dep_ns
                )
                
                # Fix paths to be relative to project root
                if "scanned_targets" in session.state and isinstance(session.state["scanned_targets"], list):
                    for t in session.state["scanned_targets"]:
                        if t.get("file_path"):
                            t["file_path"] = os.path.join(dep_path, t["file_path"])
                
                if "scanned_targets" in session.state:
                    all_targets.extend(session.state["scanned_targets"])
                if "structure_map" in session.state:
                    all_structure.update(session.state["structure_map"])
            else:
                logger.warning(f"External dependency path not found: {dep_path}")

        # Restore aggregated data to session state
        session.state["scanned_targets"] = all_targets
        session.state["structure_map"] = all_structure
        
        targets_data = all_targets
        structure_map = all_structure
        
        logger.info(f"Total targets scanned: {len(targets_data)}")
        
        # Inheritance Resolution
        logger.info("Resolving inheritance...")
        adk_inheritance = defaultdict(list)
        external_bases = defaultdict(list)
        
        class_fqns = [k for k, v in structure_map.items() if v["type"] == "Class"]
        
        for cls_fqn in class_fqns:
            bases = structure_map[cls_fqn].get("bases", [])
            for base in bases:
                match = None
                if base in structure_map: match = base
                
                if not match:
                    candidates = [k for k in class_fqns if k.endswith(f".{base}")]
                    if len(candidates) == 1:
                        match = candidates[0]
                    elif len(candidates) > 1:
                        candidates.sort(key=lambda x: len(os.path.commonprefix([x, cls_fqn])), reverse=True)
                        match = candidates[0]
                
                if match:
                    adk_inheritance[cls_fqn].append(match)
                else:
                    external_bases[cls_fqn].append(base)

        # Ranking
        cooccurrence_path = Path("benchmarks/adk_cooccurrence.json")
        entity_map = {t["id"]: t for t in targets_data}
        
        # Load co-occurrence if exists
        associations = []
        if cooccurrence_path.exists():
            with open(cooccurrence_path, "r") as f:
                cooccurrence_data = json.load(f)
                associations = cooccurrence_data.get("associations", [])

        graph = defaultdict(list)
        for a in associations:
            if a["context"] in entity_map and a["target"] in entity_map:
                graph[a["context"]].append(a["target"])
                
        seeds = [t for t in targets_data if t.get("usage_score", 0) > 0]
        seeds.sort(key=lambda t: t.get("usage_score", 0), reverse=True)
        
        ordered_ids = []
        visited = set()
        target_groups = {}
        
        for s in seeds:
            if s["id"] not in visited:
                visited.add(s["id"])
                ordered_ids.append(s["id"])
                target_groups[s["id"]] = "Seed"
                
        idx = 0
        while idx < len(ordered_ids):
            curr_id = ordered_ids[idx]
            idx += 1
            for dep_id in graph.get(curr_id, []):
                if dep_id not in visited:
                    visited.add(dep_id)
                    ordered_ids.append(dep_id)
                    target_groups[dep_id] = "Dependency"
                    
        orphans = [t for t in targets_data if t["id"] not in visited]
        orphans.sort(key=lambda t: t.get("id"))
        
        for o in orphans:
            ordered_ids.append(o["id"])
            target_groups[o["id"]] = "Orphan"

        logger.info(f"Writing detailed YAML to {output_yaml_path}...")
        
        yaml_data = []
        for rank, tid in enumerate(ordered_ids, 1):
            t = entity_map[tid]
            
            raw_type = t.get("type")
            type_name = raw_type.name if hasattr(raw_type, "name") else str(raw_type).split(".")[-1]
            
            target_model = RankedTarget(
                rank=rank,
                id=tid,
                name=t.get("name"),
                file_path=t.get("file_path"),
                type=type_name,
                group=target_groups.get(tid, "Unknown"),
                usage_score=t.get("usage_score", 0),
                docstring=self.clean_text(t.get("docstring"))
            )
            
            if tid in structure_map:
                # Constructor Reconstruction
                reconstructed_init = self.reconstruct_constructor_signature(tid, structure_map, entity_map, adk_inheritance)
                if reconstructed_init:
                     target_model.constructor_signature = reconstructed_init

                # Own Members
                own_methods = self._get_methods_for_class(tid, structure_map, entity_map)
                if own_methods:
                    target_model.methods = own_methods
                    
                own_props = self._get_properties_for_class(tid, structure_map)
                if own_props:
                    target_model.properties = own_props
                    
                # Inherited Members (ADK)
                ancestors = []
                queue = [tid]
                seen_ancestors = {tid}
                
                while queue:
                    curr = queue.pop(0)
                    parents = adk_inheritance.get(curr, [])
                    for p in parents:
                        if p not in seen_ancestors:
                            seen_ancestors.add(p)
                            ancestors.append(p)
                            queue.append(p)
                
                if ancestors:
                    inherited_methods_dict = {}
                    inherited_props_dict = {}
                    
                    for anc_fqn in ancestors:
                        anc_name = structure_map[anc_fqn]["name"]
                        
                        anc_methods = self._get_methods_for_class(anc_fqn, structure_map, entity_map)
                        if anc_methods:
                            inherited_methods_dict[anc_name] = anc_methods
                        
                        anc_props = self._get_properties_for_class(anc_fqn, structure_map)
                        if anc_props:
                            inherited_props_dict[anc_name] = anc_props
                    
                    if inherited_methods_dict:
                        target_model.inherited_methods = inherited_methods_dict
                    if inherited_props_dict:
                        target_model.inherited_properties = inherited_props_dict
                        
                # Omitted Bases
                omitted = set()
                chain = [tid] + ancestors
                for c in chain:
                    exts = external_bases.get(c, [])
                    for e in exts:
                        omitted.add(e)
                
                if omitted:
                    target_model.omitted_inherited_members_from = list(omitted)
                    note = f"[Note: Inherited members from {', '.join(sorted(omitted))} are omitted.]"
                    if target_model.docstring:
                        target_model.docstring += f"\n\n{note}"
                    else:
                        target_model.docstring = note
                    
            yaml_data.append(target_model.model_dump(exclude_none=True))
            
        with open(output_yaml_path, "w") as f:
            yaml.dump(yaml_data, f, sort_keys=False, width=1000)

        logger.info(f"Writing ranked list to {output_md_path}...")
        with open(output_md_path, "w") as f:
            f.write("# Ranked Target List\n\n")
            f.write(f"**Total Targets:** {len(ordered_ids)}\n")
            f.write(f"**Seeds:** {len(seeds)}\n")
            f.write(f"**Reachable:** {len(visited) - len(seeds)}\n\n")
            f.write("| Rank | ID | Type | Usage | Group |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            for rank, tid in enumerate(ordered_ids[:100], 1): # Top 100 in MD
                t = entity_map[tid]
                group = target_groups.get(tid, "Unknown")
                f.write(f"| {rank} | `{tid}` | {t.get('type')} | {t.get('usage_score', 0)} | {group} |\n")

        logger.info("Running integrity verification...")
        try:
            # 1. Structural Integrity
            result = subprocess.run(
                ["python3", "-m", "pytest", "benchmarks/tests/test_ranked_targets.py"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # 2. Tool Logic Verification (Integration Test)
            result_tools = subprocess.run(
                ["python3", "-m", "pytest", "tools/adk-knowledge-ext/tests/test_integration.py"],
                capture_output=True,
                text=True,
                check=False
            )
            
            passed = True
            
            if result.returncode == 0:
                logger.info("✅ Structural integrity check passed.")
            else:
                passed = False
                logger.error("❌ Structural integrity check failed!")
                logger.error(result.stdout)
                logger.error(result.stderr)
                
            if result_tools.returncode == 0:
                logger.info("✅ Tool logic verification passed.")
            else:
                passed = False
                logger.error("❌ Tool logic verification failed!")
                logger.error(result_tools.stdout)
                logger.error(result_tools.stderr)
                
        except Exception as e:
            logger.error(f"Failed to run integrity check: {e}")

        logger.info("Done.")

if __name__ == "__main__":
    # Example usage for standalone run
    logging.basicConfig(level=logging.INFO)
    ranker = TargetRanker(repo_path="repos/adk-python", stats_file="benchmarks/adk_stats_samples.yaml")
    asyncio.run(ranker.generate())
