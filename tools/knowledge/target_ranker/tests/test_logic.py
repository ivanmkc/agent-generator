"""Test Logic module."""

import pytest
from unittest.mock import MagicMock
from tools.knowledge.target_ranker.ranker import TargetRanker


class TestTargetRankerLogic:

    @pytest.fixture
    def ranker(self):
        # We don't need real repo access for these logic tests
        return TargetRanker(repo_path="dummy", stats_file="dummy")

    def test_reconstruct_constructor_explicit_init(self, ranker):
        """Should return None if the class already has an explicit __init__."""
        structure_map = {
            "pkg.MyClass": {
                "type": "Class",
                "children": ["pkg.MyClass.method", "pkg.MyClass.__init__"],
            }
        }
        entity_map = {}
        adk_inheritance = {}

        result = ranker.reconstruct_constructor_signature(
            "pkg.MyClass", structure_map, entity_map, adk_inheritance
        )
        assert result is None

    def test_reconstruct_constructor_pydantic_model(self, ranker):
        """Should reconstruct signature for Pydantic model by aggregating fields."""

        # Setup Hierarchy: Child(Parent) -> Parent(BaseModel)
        structure_map = {
            "pkg.Child": {
                "type": "Class",
                "bases": ["Parent"],
                "children": [],
                "props": [
                    {"name": "child_field", "type": "str", "docstring": "Child field"}
                ],
            },
            "pkg.Parent": {
                "type": "Class",
                "bases": ["pydantic.BaseModel"],
                "children": [],
                "props": [
                    {"name": "parent_field", "type": "int", "docstring": "Parent field"}
                ],
            },
            "pydantic.BaseModel": {
                "type": "Class",
                "bases": [],
                "children": [],
                "props": [],
            },
        }

        entity_map = {}

        # Inheritance map needs full names
        adk_inheritance = {
            "pkg.Child": ["pkg.Parent"],
            "pkg.Parent": ["pydantic.BaseModel"],
        }

        # Mock _get_properties_for_class to rely on our structure map
        # Since we use the real method, we need to make sure EXEMPTION_PHRASES doesn't filter them out.
        # But 'should_include' is simple.

        # To make the test robust, let's mock _get_properties_for_class if needed,
        # but let's try relying on the real one first since we set up structure_map.

        result = ranker.reconstruct_constructor_signature(
            "pkg.Child", structure_map, entity_map, adk_inheritance
        )

        # Expected: def __init__(self, *, parent_field: int, child_field: str):
        # Note: Order depends on traversal (reversed hierarchy -> Parent then Child)

        assert result is not None
        assert "def __init__(self, *," in result
        assert "parent_field: int" in result
        assert "child_field: str" in result

    def test_reconstruct_constructor_dataclass(self, ranker):
        """Should reconstruct signature for dataclass by aggregating fields."""

        structure_map = {
            "pkg.Data": {
                "type": "Class",
                "bases": [],
                "decorators": ["dataclass"],
                "children": [],
                "props": [{"name": "field1", "type": "int", "docstring": "Field 1"}],
            }
        }

        entity_map = {}
        adk_inheritance = {}  # No inheritance

        result = ranker.reconstruct_constructor_signature(
            "pkg.Data", structure_map, entity_map, adk_inheritance
        )

        assert result is not None
        assert "def __init__(self, *," in result
        assert "field1: int" in result

    def test_reconstruct_constructor_inherited_init(self, ranker):
        """Should return parent's __init__ signature if not Pydantic."""

        structure_map = {
            "pkg.Child": {"type": "Class", "bases": ["Parent"], "children": []},
            "pkg.Parent": {
                "type": "Class",
                "bases": [],
                "children": ["pkg.Parent.__init__"],
            },
        }

        entity_map = {
            "pkg.Parent.__init__": {
                "signature_full": "def __init__(self, name: str):",
                "docstring": "Initialize parent.",
            }
        }

        adk_inheritance = {"pkg.Child": ["pkg.Parent"]}

        result = ranker.reconstruct_constructor_signature(
            "pkg.Child", structure_map, entity_map, adk_inheritance
        )
        assert result == "def __init__(self, name: str):"

    def test_reconstruct_constructor_no_init_no_pydantic(self, ranker):
        """Should return None if standard class with no init in hierarchy."""

        structure_map = {
            "pkg.Child": {"type": "Class", "bases": ["Parent"], "children": []},
            "pkg.Parent": {
                "type": "Class",
                "bases": [],
                "children": ["pkg.Parent.method"],
            },
        }

        entity_map = {}
        adk_inheritance = {"pkg.Child": ["pkg.Parent"]}

        result = ranker.reconstruct_constructor_signature(
            "pkg.Child", structure_map, entity_map, adk_inheritance
        )
        assert result is None
