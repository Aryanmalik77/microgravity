import os
import logging
from typing import Dict, Any, Type
from pydantic import BaseModel
from google import genai
from google.genai import types

# Use litellm or configure openai to use a specific provider
from pipeline.validators import PipelineValidator
from pipeline.analytical_scripts import AnalyticalScripts

logger = logging.getLogger(__name__)

class LLMExecutor:
    """
    Handles communication with the Language Model (Switched to Gemini).
    """
    def __init__(self, model_name: str = "models/gemini-2.5-flash", temperature: float = 0.0):
        # Map GPT names to Gemini if needed
        model_map = {
            "gpt-4o": "models/gemini-2.5-flash", 
            "gpt-4o-mini": "models/gemini-2.5-flash",
            "gpt-4": "models/gemini-2.5-pro",
            "gemini-2.0-flash-exp": "models/gemini-2.5-flash",
            "gemini-1.5-flash": "models/gemini-2.5-flash"
        }
        self.model_name = model_map.get(model_name, model_name)
        
        # Ensure correct prefixing if not present, though discovery showed 'models/'
        if not self.model_name.startswith("models/"):
             self.model_name = "models/" + self.model_name
             
        self.temperature = temperature
        
        from microgravity.config.loader import load_config
        self._config = load_config()
        api_key = self._config.providers.gemini.api_key
        
        print(f"[LLMExecutor] Initializing {self.model_name} (Requested: {model_name})", flush=True)
        if not api_key:
             raise ValueError("GEMINI_API_KEY must be set in config.json.")
             
        self.client = genai.Client(api_key=api_key)

    def generate_response(self, system_prompt: str, user_prompt: str, response_format: dict = None) -> str:
        """
        Calls the Gemini API with the provided prompts.
        """
        print(f"[LLMExecutor] Calling Gemini with model {self.model_name}...", flush=True)
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
            )
            
            if response_format and response_format.get("type") == "json_object":
                config.response_mime_type = "application/json"
            
            print(f"[LLMExecutor] Prompt length: {len(user_prompt)}", flush=True)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            print(f"[LLMExecutor] Response received. Length: {len(response.text if response.text else '0')}", flush=True)
            if not response.text:
                 print(f"[LLMExecutor] EMPTY RESPONSE! Full response object: {response}", flush=True)
                 
            return response.text
        except Exception as e:
            print(f"[LLMExecutor] CRITICAL ERROR during generate_content: {e}", flush=True)
            logger.error(f"Gemini API Error: {e}")
            raise Exception(f"Failed to communicate with Gemini: {str(e)}")

class PipelineExecutor:
    """
    Coordinates the execution and validation loop for a Seeker Agent.
    """
    def __init__(self, llm_executor: LLMExecutor):
        self.llm = llm_executor
        
    def execute_with_validation(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        schema_class: Type[BaseModel],
        max_retries: int = 3
    ) -> BaseModel:
        """
        Runs the LLM and validates output against schema.
        If validation fails, it enters Feedback Processing Mode and retries.
        """
        current_user_prompt = user_prompt
        
        for attempt in range(max_retries):
            logger.info(f"Execution Attempt {attempt + 1}/{max_retries}")
            
            try:
                # 1. Prompt Execution
                raw_response = self.llm.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=current_user_prompt,
                    response_format={"type": "json_object"}
                )
                
                logger.debug(f"Raw Output: {raw_response}")
                
                # 2. Analytical Script Enforcement (Regex/Word Detection)
                # Ensure the raw text survives basic mechanical constraints BEFORE json parsing
                is_valid, analytic_msg = AnalyticalScripts.run_regex_enforcement(raw_response)
                if not is_valid:
                    raise ValueError(f"AnalyticalScriptFailure: {analytic_msg}")
                
                # 3. Schema Validation
                validated_data = PipelineValidator.validate_json_output(raw_response, schema_class)
                
                # If we parse successfully, return it
                return validated_data
                
            except ValueError as ve:
                logger.warning(f"Validation failed on attempt {attempt + 1}: {ve}")
                
                # Enter Feedback Processing Mode: Append error to prompt and retry
                error_feedback = f"\n\n[SYSTEM FEEDBACK: Your previous output failed validation. Please fix the following error and try again:\n{str(ve)}]"
                current_user_prompt += error_feedback
                
                if attempt == max_retries - 1:
                    logger.error("Max retries exceeded. Triggering Human-In-The-Loop fallback.")
                    # In a real event-driven system, you'd emit to the EventBus here.
                    raise Exception(f"HITL_REQUIRED: Failed to generate valid output after {max_retries} attempts. Last Error: {ve}")

        raise Exception("Unexpected pipeline failure.")
