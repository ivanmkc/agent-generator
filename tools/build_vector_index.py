import os
import yaml
import numpy as np
import json
from pathlib import Path
from google import genai
from google.genai import types
from typing import List, Dict, Any
import asyncio
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RANKED_TARGETS_FILE

# Store embeddings alongside the YAML file
OUTPUT_DIR = RANKED_TARGETS_FILE.parent
VECTORS_PATH = OUTPUT_DIR / "targets_vectors.npy"
META_PATH = OUTPUT_DIR / "targets_meta.json"

async def build_index():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        return

    client = genai.Client(api_key=api_key)

    if not RANKED_TARGETS_FILE.exists():
        print(f"Error: {RANKED_TARGETS_FILE} not found.")
        return

    with open(RANKED_TARGETS_FILE, "r") as f:
        targets = yaml.safe_load(f)

    if not targets:
        print("Error: No targets found in YAML.")
        return

    print(f"Indexing {len(targets)} targets into {OUTPUT_DIR}...")

    texts = []
    metadata = []

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
        metadata.append({
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
    np.save(VECTORS_PATH, np.array(all_embeddings))
    with open(META_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Successfully built index at {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(build_index())
