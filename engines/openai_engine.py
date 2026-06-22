import os
import requests
from engines.base import BaseEngine
from prompts import get_system_instruction, get_analysis_prompt

class OpenAIEngine(BaseEngine):
    def __init__(self):
        # Bisa dipakai untuk OpenAI, OpenRouter, Groq, dll.
        self.api_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip('/') + "/chat/completions"
        self.api_key = os.getenv("AI_API_KEY", "")
        self.model = os.getenv("AI_MODEL", "gpt-3.5-turbo")

    def analyze(self, curhatan: str, persona: str) -> dict:
        system_instruction = get_system_instruction(persona)
        prompt = get_analysis_prompt(curhatan, system_instruction)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"} if "gpt-4" in self.model or "gpt-3.5" in self.model else None
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            response_text = result["choices"][0]["message"]["content"].strip()
            return self.clean_json_response(response_text)
        except Exception as e:
            print(f"[OpenAIEngine] Error: {e}")
            raise e
