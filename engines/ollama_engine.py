import os
import requests
from engines.base import BaseEngine
from prompts import get_system_instruction, get_analysis_prompt

class OllamaEngine(BaseEngine):
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_url = f"{self.base_url.rstrip('/')}/api/generate"
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))

    def analyze(self, curhatan: str, persona: str) -> dict:
        system_instruction = get_system_instruction(persona)
        prompt = get_analysis_prompt(curhatan, system_instruction)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "").strip()
            return self.clean_json_response(response_text)
        except Exception as e:
            print(f"[OllamaEngine] Error: {e}")
            raise e
