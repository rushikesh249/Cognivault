import os
from pathlib import Path

FORBIDDEN_KEYWORDS = [
    "openai",
    "anthropic",
    "google-generativeai",
    "google.generativeai",
    "cohere",
    "replicate",
    "azure-ai",
    "boto3",
    "bedrock",
]

def test_requirements_no_cloud_dependencies():
    req_file = Path(__file__).resolve().parent.parent.parent / "backend" / "requirements.txt"
    assert req_file.exists(), "backend/requirements.txt must exist"
    
    content = req_file.read_text(encoding="utf-8").lower()
    for kw in FORBIDDEN_KEYWORDS:
        assert kw not in content, f"Forbidden cloud dependency found in requirements.txt: {kw}"

def test_source_code_no_cloud_imports():
    root = Path(__file__).resolve().parent.parent.parent / "backend" / "app"
    for py_file in root.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for kw in FORBIDDEN_KEYWORDS:
            assert f"import {kw}" not in content, f"Forbidden cloud import '{kw}' found in {py_file}"
            assert f"from {kw}" not in content, f"Forbidden cloud import '{kw}' found in {py_file}"
