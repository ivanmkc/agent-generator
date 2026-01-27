"""
Script to generate benchmarks/generator_internals.md from the current code definitions.
This script aggregates generators into 'Archetypes' (grouping by configuration/image, ignoring model parameters)
to create a static reference document for report generation.
"""

import sys
import os
import re
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliPodmanAnswerGenerator

def get_archetype_key(generator):
    """Determines the unique archetype key for a generator."""
    if isinstance(generator, GeminiCliPodmanAnswerGenerator):
        # For Podman, the image defines the archetype.
        return f"GeminiCliPodman: {generator.image_name}"
    else:
        # For ADK/Other, usually the name prefix (before the model param) defines it.
        # e.g. "ADK_Single_Agent_Generalist(gemini-2.5-flash)" -> "ADK_Single_Agent_Generalist"
        if "(" in generator.name:
            return generator.name.split("(")[0]
        return generator.name

def clean_description(desc):
    """Removes runtime-specific lines (like Model) from the description."""
    lines = desc.splitlines()
    cleaned_lines = []
    for line in lines:
        # Remove the Model line as it's a runtime parameter
        if line.strip().startswith("**Model:**"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()

def generate_docs():
    output_path = project_root / "ai/reports/generator_internals.md"
    
    content = ["# Generator Internals (Static Reference)\n"]
    content.append("> This file describes the static architectures of the available generators. Runtime parameters (like Model) are injected during execution.\n")
    
    seen_archetypes = set()
    
    for g in CANDIDATE_GENERATORS:
        key = get_archetype_key(g)
        
        if key in seen_archetypes:
            continue
        
        seen_archetypes.add(key)
        
        # Get description and clean it
        raw_desc = getattr(g, "description", "No description provided.")
        static_desc = clean_description(raw_desc)
        
        content.append(f"### {key}")
        # Add a placeholder note for the model
        content.append(f"- **Model:** `[Injected at Runtime]`")
        
        if isinstance(g, GeminiCliPodmanAnswerGenerator):
             content.append(f"- **Docker Image:** `{g.image_name}`")
        
        content.append(f"\n{static_desc}\n")
        content.append("---\n")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    
    print(f"Successfully generated {output_path}")
    print(f"Documented {len(seen_archetypes)} unique generator archetypes from {len(CANDIDATE_GENERATORS)} candidates.")

if __name__ == "__main__":
    generate_docs()