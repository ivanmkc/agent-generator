
import pytest
from tools.target_ranker.ranker import TargetRanker

class TestTargetRankerBlacklisting:
    
    @pytest.fixture
    def ranker(self):
        return TargetRanker(repo_path="dummy", stats_file="dummy")

    def test_blacklist_exclusion(self, ranker):
        """Verify that blacklisted fields (e.g. invocation_id) are excluded even if they don't have init=False."""
        structure_map = {
            "pkg.Event": {
                "type": "Class",
                "bases": ["pydantic.BaseModel"],
                "decorators": [],
                "children": [],
                "props": [
                    {"name": "valid_field", "type": "str", "docstring": "User content", "init_excluded": False},
                    {"name": "invocation_id", "type": "str", "docstring": "Internal ID", "init_excluded": False},  # No init=False, should be caught by blacklist
                    {"name": "parent_agent", "type": "Any", "docstring": "Parent", "init_excluded": True} # Explicit init=False
                ]
            },
            "pydantic.BaseModel": {"type": "Class", "bases": [], "props": []}
        }
        
        entity_map = {}
        adk_inheritance = {"pkg.Event": ["pydantic.BaseModel"]}
        
        result = ranker.reconstruct_constructor_signature("pkg.Event", structure_map, entity_map, adk_inheritance)
        
        assert result is not None
        assert "valid_field: str" in result
        assert "invocation_id" not in result
        assert "parent_agent" not in result

    def test_blacklist_model_config(self, ranker):
        """Verify model_config is excluded."""
        structure_map = {
            "pkg.Config": {
                "type": "Class",
                "bases": ["pydantic.BaseModel"],
                "props": [
                    {"name": "model_config", "type": "ConfigDict", "docstring": "Config", "init_excluded": False},
                    {"name": "real_setting", "type": "int", "docstring": "Setting", "init_excluded": False}
                ]
            },
            "pydantic.BaseModel": {"type": "Class", "bases": [], "props": []}
        }
        
        entity_map = {}
        adk_inheritance = {"pkg.Config": ["pydantic.BaseModel"]}
        
        result = ranker.reconstruct_constructor_signature("pkg.Config", structure_map, entity_map, adk_inheritance)
        
        assert "real_setting: int" in result
        assert "model_config" not in result
