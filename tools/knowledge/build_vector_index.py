import os
import yaml
import numpy as np
import json
from pathlib import Path
from google import genai
from google.genai import types
from typing import List, Dict, Any
import asyncio
import argparse
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RANKED_TARGETS_FILE

async def build_index(input_file: Path):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        return

    client = genai.Client(api_key=api_key)

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    # Store embeddings based on input file location
    output_dir = input_file.parent
    vectors_path = output_dir / "vectors.npy"
    keys_path = output_dir / "vector_keys.yaml"

    with open(input_file, "r") as f:
        targets = yaml.safe_load(f)

    if not targets:
        print("Error: No targets found in YAML.")
        return

    print(f"Indexing {len(targets)} targets into {output_dir}...")

    texts = []
    vector_keys = []

    for t in targets:
        # Construct rich text representation
        name = t.get("name", "")
        fqn = t.get("id", "")
        type_ = t.get("type", "")
        docstring = t.get("docstring", "") or ""
        
        methods = t.get("methods", [])
        method_sigs = "\n".join([m.get("signature", "") for m in methods])
        
        rich_text = f"Name: {name}\nFQN: {fqn}\nType: {type_}\nDocstring: {docstring}\nMethods:\n{method_sigs}"
        texts.append(rich_text)
        vector_keys.append({
            "id": fqn,
            "type": type_,
            "rank": t.get("rank", 9999)
        })

    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...")
        
        try:
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=batch_texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            batch_vecs = [e.values for e in response.embeddings]
            all_embeddings.extend(batch_vecs)
        except Exception as e:
            print(f"Warning: text-embedding-004 failed: {e}. Trying gemini-embedding-001...")
            try:
                response = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch_texts,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                )
                batch_vecs = [e.values for e in response.embeddings]
                all_embeddings.extend(batch_vecs)
            except Exception as e2:
                print(f"Error during embedding with fallback: {e2}")
                return

    # Save artifacts alongside the YAML
    np.save(vectors_path, np.array(all_embeddings))
    with open(keys_path, "w") as f:
        yaml.dump(vector_keys, f, sort_keys=False)

    print(f"Successfully built index artifacts at {output_dir}")

async def main():
    parser = argparse.ArgumentParser(description="Generate vector embeddings for ranked targets.")
    parser.add_argument("--input-yaml", type=str, help="Path to ranked_targets.yaml")
    args = parser.parse_args()

    input_file = Path(args.input_yaml) if args.input_yaml else RANKED_TARGETS_FILE
    await build_index(input_file)

if __name__ == "__main__":
    asyncio.run(main())
