import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Add project root to sys.path to allow imports from benchmarks when running directly
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType

@dataclass
class LogNode:
    name: str
    start_time: float
    end_time: Optional[float] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    children: List["LogNode"] = field(default_factory=list)

    def to_text(self, depth: int = 0) -> str:
        indent = "  " * depth
        lines = [f"{indent}SECTION: {self.name}"]
        
        for event in self.events:
            # Format generic events
            ts = f"{event.get('timestamp', 0):.2f}"
            etype = event.get('event_type', 'unknown')
            data = event.get('data', {})
            
            if etype == 'message':
                msg = data.get('message', '')
                lines.append(f"{indent}  [{ts}] {msg}")
            elif etype == 'test_result':
                # Simplified test result logging
                bname = data.get('benchmark_name', 'unknown')
                res = data.get('result', 'unknown')
                err = data.get('validation_error')
                status_icon = "✅" if res == 'pass' else "❌"
                lines.append(f"{indent}  [{ts}] {status_icon} {bname}: {res}")
                if err:
                    lines.append(f"{indent}      Error: {err}")
            else:
                lines.append(f"{indent}  [{ts}] {etype}: {data}")

        for child in self.children:
            lines.append(child.to_text(depth + 1))
            
        return "\n".join(lines)

class LogAnalyzer:
    """
    Analyzes benchmark logs using Gemini to provide insights and summaries.
    Parses logs into a hierarchy and maps analysis over top-level runs.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name

    def _get_client(self):
        """Initializes the Gemini client with a rotated API key."""
        api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise ValueError("No API key available for LogAnalyzer.")
        return Client(api_key=api_key)

    def _parse_log_file(self, log_path: Path) -> List[LogNode]:
        """Parses the trace.jsonl file into a forest of LogNodes."""
        roots = []
        stack: List[LogNode] = []
        
        # Virtual root for global events if needed, but we'll try to find natural roots
        # If events occur before the first section, we might lose them or need a 'Global' node.
        # Let's use a 'Global' node if needed, but 'trace.jsonl' usually starts with global events.
        global_node = LogNode(name="Global Context", start_time=0)
        roots.append(global_node)
        
        # We'll treat the 'Global Context' as the default bucket for non-nested events
        # Top-level sections will be siblings in 'roots' (actually let's make them children of global? 
        # No, better to have a list of distinct runs if they are sections).
        
        # Actually, let's keep it simple: Roots are top-level sections. 
        # Events outside any section go to a 'Prelude' node.
        prelude = LogNode(name="Prelude", start_time=0)
        roots = [prelude]
        
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
                    etype = event.get('event_type')
                    timestamp = event.get('timestamp', 0)
                    data = event.get('data', {})

                    if etype == 'section_start':
                        name = data.get('name', 'Unnamed Section')
                        node = LogNode(name=name, start_time=timestamp)
                        
                        if stack:
                            stack[-1].children.append(node)
                        else:
                            roots.append(node)
                        
                        stack.append(node)
                    
                    elif etype == 'section_end':
                        if stack:
                            node = stack.pop()
                            node.end_time = timestamp
                    
                    else:
                        # Add event to current section
                        if stack:
                            stack[-1].events.append(event)
                        else:
                            # Add to the last root (likely Prelude or a closed section?)
                            # If we are not in a section, it belongs to the top level context.
                            # If roots[-1] is a closed section, we might need a new 'Interlude' node?
                            # For simplicity, add to 'Prelude' if it's the only one, or append to the last root.
                            # Actually, if we have multiple roots (runs), inter-run events are rare.
                            # Let's just add to the last root for continuity.
                            roots[-1].events.append(event)

        except Exception as e:
            print(f"Error reading log file: {e}")
            
        # Remove Prelude if empty
        if not prelude.events and not prelude.children:
            roots.remove(prelude)
            
        return roots

    async def analyze_log_file(self, log_path: Path) -> str:
        """
        Analyzes the trace.jsonl file and returns a summary.
        """
        if not log_path.exists():
            return f"Log file not found: {log_path}"

        print(f"Analyzing log file: {log_path}")
        
        # Load Static Metadata
        run_dir = log_path.parent
        
        # 1. Try to load pre-cached Markdown (Preferred)
        internals_md_path = run_dir / "generator_internals.md"
        generator_internals_context = ""
        
        if internals_md_path.exists():
            try:
                with open(internals_md_path, "r", encoding="utf-8") as f:
                    generator_internals_context = f.read()
            except Exception as e:
                print(f"Error loading generator_internals.md: {e}")
        
        # 2. Fallback: Load JSON and reconstruct if MD is missing
        if not generator_internals_context:
            metadata_path = run_dir / "run_metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    
                    gens = meta.get("generators", [])
                    gen_text = "\n".join([f"- **{g['name']}** ({g.get('model_name')})\n  Description: {g.get('description')}" for g in gens])
                    generator_internals_context = f"**Generators Configured (Fallback):**\n{gen_text}"
                except Exception as e:
                    print(f"Error loading run_metadata.json: {e}")
            else:
                generator_internals_context = "No static configuration metadata available."

        # 1. Parse Structure
        nodes = self._parse_log_file(log_path)
        if not nodes:
            return "Log file is empty or could not be parsed."

        print(f"Identified {len(nodes)} top-level execution blocks. Starting parallel analysis...")

        # 2. Map: Analyze each top-level node concurrently
        node_analyses = await self._analyze_nodes(nodes)

        # 3. Reduce: Synthesize the final report
        final_summary = await self._reduce_analyses(node_analyses, generator_internals_context)
        
        return final_summary

    async def _analyze_nodes(self, nodes: List[LogNode]) -> List[str]:
        """
        Runs analysis on each node in parallel.
        """
        tasks = []
        for i, node in enumerate(nodes):
            tasks.append(self._analyze_single_node(i, node))
        
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

    async def _analyze_single_node(self, index: int, node: LogNode) -> str:
        """
        Analyzes a single LogNode (and its hierarchy).
        """
        # Convert node tree to text representation
        log_text = node.to_text()
        
        # Skip empty nodes (common with Prelude)
        if len(log_text.splitlines()) < 2: 
            return ""

        # Load prompt from external file
        prompt_path = Path("notebooks/report/log_analysis_node_prompt.md")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
             # Fallback to a minimal prompt if file is missing
             prompt_template = "Analyze the following log block: {log_text}"

        prompt = prompt_template.format(node_name=node.name, log_text=log_text)

        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=[types.Content(parts=[types.Part(text=prompt)])]
            )
            return f"### Analysis of '{node.name}'\n\n{response.text}"
        except Exception as e:
            print(f"Error analyzing node {node.name}: {e}")
            return f"Error analyzing node {node.name}: {e}"

    async def _reduce_analyses(self, analyses: List[str], static_context: str = "") -> str:
        """
        Aggregates per-node analyses into a final report.
        """
        combined_text = "\n\n".join(analyses)
        
        # Load prompt from external file
        prompt_path = Path("notebooks/report/log_analysis_reduce_prompt.md")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
             # Fallback
             prompt_template = "Synthesize these analyses into a report: {combined_text}\nContext: {static_context}"

        prompt = prompt_template.format(combined_text=combined_text, static_context=static_context)

        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=[types.Content(parts=[types.Part(text=prompt)])]
            )
            return response.text
        except Exception as e:
            print(f"Error generating final summary: {e}")
            return "Failed to generate final summary."

async def analyze_run_logs(run_dir: Path):
    """
    Helper function to run the analyzer on a specific directory.
    """
    log_path = run_dir / "trace.jsonl"
    analyzer = LogAnalyzer()
    print(f"\n--- Starting Log Analysis on {log_path} ---")
    summary = await analyzer.analyze_log_file(log_path)
    
    # Save the analysis
    analysis_path = run_dir / "log_analysis.md"
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"\n--- Log Analysis Complete ---")
    print(f"Report saved to: {analysis_path}")
    
    # Print a preview
    lines = summary.splitlines()
    preview = "\n".join(lines[:20])
    print("\nSummary Preview:")
    print(preview)
    print("...")

if __name__ == "__main__":
    # Test block for running this script directly
    import sys
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
        asyncio.run(analyze_run_logs(run_dir))