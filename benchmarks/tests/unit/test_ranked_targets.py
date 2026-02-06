import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml
from benchmarks.answer_generators.adk_tools import AdkTools
from tools.knowledge.target_ranker.models import RankedTarget

@pytest.fixture

def mock_data():

    content = """

- rank: 1

  id: google.adk.MockClass

  name: MockClass

  type: CLASS

  group: Seed

  usage_score: 100

  docstring: "A mock class for testing."

  methods:

    - signature: "def mock_method(self):"

      docstring: "A mock method."

  properties:

    - signature: "mock_prop: int"

      docstring: "A mock property."

  inherited_methods:

    BaseClass:

      - signature: "def base_method(self):"

        docstring: "Inherited method."

"""

    return yaml.safe_load(content)



@pytest.fixture



def adk_tools(mock_data, monkeypatch):



    from benchmarks.answer_generators.adk_tools import AdkTools



    from tools.knowledge.target_ranker.models import RankedTarget



    # Convert mock dicts to RankedTarget objects for the mock return value



    targets = [RankedTarget(**item) for item in mock_data]



    



    def mock_load(self):



        self._ranked_targets_path = Path("/tmp/workspace/ranked_targets.yaml")



        return targets







    # Monkeypatch the method on the class before instantiation



    monkeypatch.setattr(AdkTools, "_load_ranked_targets", mock_load)



    



    tools = AdkTools(Path("/tmp/workspace"))



    return tools











def test_list_ranked_targets(adk_tools):

    output = adk_tools.list_ranked_targets(page=1, page_size=10)

    assert "--- Ranked Targets (Page 1 of 1) ---" in output

    assert "google.adk.MockClass: A mock class for testing." in output



@pytest.mark.asyncio

async def test_search_ranked_targets(adk_tools):

    # Execute - Match found

    output = await adk_tools.search_ranked_targets("MockClass")

    # Header format depends on whether _search_provider is initialized.

    # If patched correctly, it should be initialized.

    assert "Search Results for 'MockClass'" in output

    assert "google.adk.MockClass" in output



    # Execute - No match

    output_fail = await adk_tools.search_ranked_targets("NonExistent")

    assert "No targets found matching: NonExistent" in output_fail



def test_inspect_ranked_target(adk_tools):

    output = adk_tools.inspect_ranked_target("google.adk.MockClass")

    assert "=== Inspection: google.adk.MockClass ===" in output

    assert "Type: CLASS" in output

    assert "Rank: 1" in output

    assert "A mock class for testing." in output



def test_inspect_ranked_target_not_found(adk_tools):

    output = adk_tools.inspect_ranked_target("google.adk.Unknown")

    assert "Target 'google.adk.Unknown' not found in ranked index." in output
