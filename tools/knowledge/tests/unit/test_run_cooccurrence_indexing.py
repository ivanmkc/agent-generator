import yaml
import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.knowledge.run_cooccurrence_indexing import generate_cooccurrence

def test_generate_cooccurrence():
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create some fake code files
        code1 = """
import google.genai as genai
from google.cloud import storage

client = genai.Client()
bucket = storage.Client()
        """
        
        code2 = """
import google.genai.types as types
from google.genai import Client

c = Client()
t = types.GenerateContentConfig()
        """
        
        code3 = """
from vertexai.preview.generative_models import GenerativeModel
import vertexai

model = GenerativeModel("gemini-pro")
        """
        
        # Write files
        (tmp_path / "file1.py").write_text(code1)
        (tmp_path / "file2.py").write_text(code2)
        (tmp_path / "file3.py").write_text(code3)
        (tmp_path / "test_ignored.py").write_text("import google.genai") # should be ignored
        
        output_file = tmp_path / "output.yaml"
        
        from tools.knowledge.run_cooccurrence_indexing import generate_cooccurrence
        generate_cooccurrence([tmp_path], str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            data = yaml.safe_load(f)
            
        assert "meta" in data
        assert "associations" in data

def test_generate_cooccurrence_with_counts():
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Need entities to appear in >= 2 files
        code1 = """
import google.genai as genai
from google.cloud import storage
"""
        code2 = """
import google.genai as genai
from google.cloud import storage
"""
        code3 = """
import google.genai as genai
import vertexai
"""
        
        (tmp_path / "file1.py").write_text(code1)
        (tmp_path / "file2.py").write_text(code2)
        (tmp_path / "file3.py").write_text(code3)
        
        output_file = tmp_path / "output.yaml"
        from tools.knowledge.run_cooccurrence_indexing import generate_cooccurrence
        generate_cooccurrence([tmp_path], str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            data = yaml.safe_load(f)
            
        associations = data["associations"]
        
        # google.genai is in 3 files
        # google.cloud is in 2 files
        # vertexai is in 1 file (count < 2, so it shouldn't be a context, but it can be a target)
        
        genai_to_cloud = [a for a in associations if a["context"] == "google.genai" and a["target"] == "google.cloud"]
        assert len(genai_to_cloud) == 1
        assert genai_to_cloud[0]["support"] == 2
        assert genai_to_cloud[0]["probability"] == round(2 / 3, 3)
        
        cloud_to_genai = [a for a in associations if a["context"] == "google.cloud" and a["target"] == "google.genai"]
        assert len(cloud_to_genai) == 1
        assert cloud_to_genai[0]["support"] == 2
        assert cloud_to_genai[0]["probability"] == 1.0
import ast
from tools.knowledge.run_cooccurrence_indexing import GranularUsageVisitor

def test_granular_usage_visitor():
    code = """
import google.genai as genai
from google.cloud import storage
import vertexai.preview.generative_models

client = genai.Client()
bucket = storage.Client()
model = vertexai.preview.generative_models.GenerativeModel("gemini-pro")
client.models.generate_content()
"""
    tree = ast.parse(code)
    visitor = GranularUsageVisitor()
    visitor.visit(tree)

    used = visitor.used_entities
    assert "google.genai" in used
    assert "google.cloud.storage" in used
    assert "vertexai.preview.generative_models" in used
    assert "google.genai.Client" in used
    assert "google.cloud.storage.Client" in used
    assert "vertexai.preview.generative_models.GenerativeModel" in used
    assert "client.models.generate_content" in used

def test_dynamic_cooccurrence():
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Need entities to appear in >= 2 files
        code1 = """
import google.genai as genai
from pydantic import BaseModel
import sys
import os
"""
        code2 = """
import google.genai as genai
from pydantic import BaseModel
import sys
"""
        code3 = """
from pydantic import BaseModel
import langchain
import os
"""
        
        (tmp_path / "file1.py").write_text(code1)
        (tmp_path / "file2.py").write_text(code2)
        (tmp_path / "file3.py").write_text(code3)
        
        output_file = tmp_path / "output_dyn.yaml"
        # Dynamic mode: no explicit namespaces
        
        
        from tools.knowledge.run_cooccurrence_indexing import generate_cooccurrence
        generate_cooccurrence([tmp_path], str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            data = yaml.safe_load(f)
            
        associations = data["associations"]
        
        # pydantic is in 3 files
        # google is in 2 files
        # sys, os should NOT be present (stdlib)
        
        targets = {a["target"] for a in associations}
        contexts = {a["context"] for a in associations}
        
        # Should NOT capture stdlib
        assert "sys" not in targets
        assert "os" not in targets
        assert "sys" not in contexts
        assert "os" not in contexts
        
        # Should CAPTURE dynamic non-stdlib usages
        assert "pydantic.BaseModel" in targets or "pydantic" in targets
        assert "google.genai" in targets
