import sys
import os
import logging
from pydantic import BaseModel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.validators import PipelineValidator

logging.basicConfig(level=logging.INFO)

class TestSchema(BaseModel):
    name: str
    description: str
    metadata: dict

def test_json_repair():
    # An unterminated string that simulates an LLM cutting off
    broken_json = """
    {
        "name": "Architecture Estimator",
        "description": "Analyzes the deeply nested structural patterns of the target repository and extracts",
        "metadata": {"version": 1}
    """
    
    print("Testing PipelineValidator with broken JSON...")
    
    try:
        result = PipelineValidator.validate_json_output(broken_json, TestSchema)
        print("Success! Parsed output:")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"Failed! {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_json_repair()
