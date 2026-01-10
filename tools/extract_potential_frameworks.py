"""
Utility tool to discover potential new AI frameworks from VibeShare results.

This script scans the `vibeshare_results.json` output file for proper nouns
that are not yet in the known `FRAMEWORKS_TO_DETECT` list. It helps in maintaining
an up-to-date list of competing or complementary frameworks mentioned by models.
"""

import json
import re
from collections import Counter
from vibeshare.data_models import FRAMEWORKS_TO_DETECT

def extract_candidates():
    """
    Reads vibeshare_results.json and prints frequent proper noun phrases 
    that might be undetected frameworks.
    """
    try:
        with open('vibeshare_results.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("vibeshare_results.json not found.")
        return

    text_blob = ""
    for item in data:
        if item.get('response'):
            text_blob += item['response'] + "\n"

    # Normalize existing frameworks for comparison
    existing = set(f.lower() for f in FRAMEWORKS_TO_DETECT)

    # Regex for potential Proper Noun Phrases (simple heuristic)
    # Matches words starting with Uppercase, possibly followed by another Uppercase word
    # e.g. "Spring AI", "LangChain", "Vertex AI"
    # We'll look for 1-3 word capitalized sequences
    pattern = r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,2})\b'
    
    matches = re.findall(pattern, text_blob)
    
    # Filter and count
    candidates = []
    for m in matches:
        lower_m = m.lower()
        if lower_m not in existing:
            # Basic filtering of common words
            if lower_m not in {"the", "a", "an", "this", "that", "in", "on", "of", "for", "to", "and", "or", "is", "are", "it", "we", "i", "you", "pros", "cons", "features", "description", "example", "usage", "why", "how", "what", "where", "when", "who", "key", "top", "list", "use", "code", "agent", "agents", "ai", "framework", "library", "sdk", "api", "tool", "tools", "python", "java", "go", "javascript", "typescript", "model", "models", "llm", "llms", "google", "microsoft", "openai", "anthropic", "meta", "vertex", "azure", "aws", "cloud", "project", "app", "application", "system", "user", "data", "text", "search", "chat", "image", "video", "audio", "file", "json", "result", "output", "input", "value", "variable", "function", "class", "object", "method", "loop", "step", "task", "role", "goal", "memory", "history", "context", "prompt", "response", "action", "plan", "reasoning", "setup", "installation", "prerequisites", "steps", "note", "pros", "cons", "ranking", "tier", "core", "components", "architecture", "overview", "introduction", "conclusion", "summary", "reference", "source", "author", "date", "time", "version", "status", "error", "warning", "info", "debug", "trace", "log", "print", "true", "false", "none", "null", "undefined", "nan", "inf", "infinity"}:
                 candidates.append(m)

    counts = Counter(candidates)
    
    print("Top 50 Potential Framework Candidates:")
    for term, count in counts.most_common(50):
        print(f"{term}: {count}")

if __name__ == "__main__":
    extract_candidates()
