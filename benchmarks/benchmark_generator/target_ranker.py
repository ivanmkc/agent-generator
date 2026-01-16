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
from pathlib import Path
from collections import defaultdict
from typing import Optional

from benchmarks.benchmark_generator.tools import scan_repository
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

class MockAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if False: yield None

class TargetRanker:
    def __init__(self, repo_path: str, namespace: str = "google.adk", stats_file: str = "benchmarks/adk_stats_samples.yaml"):
        self.repo_path = repo_path
        self.namespace = namespace
        self.stats_file = stats_file

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
        
        logger.info("Running scan_repository...")
        scan_repository(repo_path=self.repo_path, tool_context=context)
        
        targets_data = session.state["scanned_targets"]
        structure_map = session.state["structure_map"]
        
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

        # Helpers for Retrieval
        def get_methods_for_class(cls_fqn):
            methods = []
            struct = structure_map.get(cls_fqn)
            if not struct: return []
            
            children = struct.get("children", [])
            for child_fqn in children:
                child_name = child_fqn.split(".")[-1]
                if not child_name.startswith("_"):
                    child_struct = structure_map.get(child_fqn)
                    if child_struct and child_struct.get("type") != "Method":
                        continue 

                    child_entity = entity_map.get(child_fqn)
                    sig = child_entity.get("signature_full") if child_entity else None
                    if not sig and child_struct:
                         sig = child_struct.get("signature")
                    if not sig:
                        sig = f"def {child_name}(...):"
                    
                    method_entry = {"signature": sig}
                    
                    m_doc = child_entity.get("docstring") if child_entity else None
                    if not m_doc and child_struct:
                         m_doc = child_struct.get("docstring")

                    if m_doc:
                        method_entry["docstring"] = self.clean_text(m_doc)
                    
                    if self.should_include(method_entry):
                        methods.append(method_entry)
            return methods

        def get_properties_for_class(cls_fqn):
            properties = []
            struct = structure_map.get(cls_fqn)
            if not struct: return []
            
            props = struct.get("props", [])
            for p in props:
                sig = f"{p['name']}: {p['type']}"
                prop_entry = {"signature": sig}
                if p.get("docstring"):
                    prop_entry["docstring"] = self.clean_text(p["docstring"])
                
                if self.should_include(prop_entry):
                    properties.append(prop_entry)
            return properties

        logger.info(f"Writing detailed YAML to {output_yaml_path}...")
        
        yaml_data = []
        for rank, tid in enumerate(ordered_ids, 1):
            t = entity_map[tid]
            
            raw_type = t.get("type")
            type_name = raw_type.name if hasattr(raw_type, "name") else str(raw_type).split(".")[-1]
            
            entry = {
                "rank": rank,
                "id": tid,
                "name": t.get("name"),
                "type": type_name,
                "group": target_groups.get(tid, "Unknown"),
                "usage_score": t.get("usage_score", 0),
                "docstring": self.clean_text(t.get("docstring")),
            }
            
            if tid in structure_map:
                # Own Members
                own_methods = get_methods_for_class(tid)
                if own_methods:
                    entry["methods"] = own_methods
                    
                own_props = get_properties_for_class(tid)
                if own_props:
                    entry["properties"] = own_props
                    
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
                        
                        anc_methods = get_methods_for_class(anc_fqn)
                        if anc_methods:
                            inherited_methods_dict[anc_name] = anc_methods
                        
                        anc_props = get_properties_for_class(anc_fqn)
                        if anc_props:
                            inherited_props_dict[anc_name] = anc_props
                    
                    if inherited_methods_dict:
                        entry["inherited_methods"] = inherited_methods_dict
                    if inherited_props_dict:
                        entry["inherited_properties"] = inherited_props_dict
                        
                # Omitted Bases
                omitted = set()
                chain = [tid] + ancestors
                for c in chain:
                    exts = external_bases.get(c, [])
                    for e in exts:
                        omitted.add(e)
                
                if omitted:
                    entry["omitted_inherited_members_from"] = list(omitted)
                    note = f"[Note: Inherited members from {', '.join(sorted(omitted))} are omitted.]"
                    if entry["docstring"]:
                        entry["docstring"] += f"\n\n{note}"
                    else:
                        entry["docstring"] = note
                    
            yaml_data.append(entry)
            
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

        logger.info("Done.")

if __name__ == "__main__":
    # Example usage for standalone run
    logging.basicConfig(level=logging.INFO)
    ranker = TargetRanker(repo_path="../adk-python", stats_file="benchmarks/adk_stats_samples.yaml")
    asyncio.run(ranker.generate())
