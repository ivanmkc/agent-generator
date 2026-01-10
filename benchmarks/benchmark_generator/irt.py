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

"""Item Response Theory (IRT) logic for the Prismatic Generator."""

import json
import math
from pathlib import Path
from typing import Dict, Any

class IRTManager:
    """Manages IRT parameters for code targets."""

    def __init__(self, data_file: Path | str | None = None):
        self.data_file = Path(data_file) if data_file else None
        self.data: Dict[str, Any] = {}
        if self.data_file and self.data_file.exists():
            try:
                self.data = json.loads(self.data_file.read_text())
            except Exception:
                self.data = {}

    def get_target_info(self, target_id: str) -> Dict[str, float]:
        """Retrieves IRT parameters for a target (difficulty, discrimination)."""
        return self.data.get(target_id, {"difficulty": 0.0, "discrimination": 1.0, "variance": 0.5})

    def calculate_priority(self, target: Dict[str, Any], coverage_data: Dict[str, Any] | None) -> float:
        """
        Calculates priority based on Complexity, Coverage, and IRT Information.
        Priority = w1 * Complexity + w2 * (1 - Coverage) + w3 * FisherInformation
        """
        complexity = target.get("complexity_score", 0)
        
        # Coverage: If method is covered, priority drops. If uncovered, priority high.
        # We assume coverage_data maps file_path -> coverage_percentage (0-100)
        # or list of covered lines.
        # Simplified: If we have coverage data, use it.
        coverage_score = 0.0
        if coverage_data:
            # Placeholder: Check if file is in coverage data
            # In a real impl, we'd check specific lines.
            if target["file_path"] in coverage_data:
                # Assume high coverage if present, so lower priority
                coverage_score = -50.0 
            else:
                # Uncovered file
                coverage_score = 50.0
        
        # IRT Fisher Information
        # We want targets where we have high uncertainty (variance) or high discrimination
        # Fisher Information ~ Discrimination^2 / Variance (roughly, for selection)
        # Actually we want targets that maximize information about Ability.
        # For generation, we prioritize targets that are 'hard' or 'discriminating'.
        target_id = f"{target['file_path']}::{target['method_name']}"
        irt_params = self.get_target_info(target_id)
        irt_score = irt_params["discrimination"] * 10 + irt_params["difficulty"] * 5

        # Docstring bonus
        doc_bonus = 10 if target.get("docstring") else 0

        return complexity + coverage_score + irt_score + doc_bonus
