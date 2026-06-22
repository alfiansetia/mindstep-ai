import os
import requests
import json
from engines.base import BaseEngine
from prompts import get_system_instruction, get_analysis_prompt

class GeminiEngine(BaseEngine):
    def __init__(self):
        # Menggunakan API v1beta atau v1
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("AI_MODEL", "gemini-1.5-flash")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def analyze(self, curhatan: str, persona: str) -> dict:
        system_instruction = get_system_instruction(persona)
        prompt = get_analysis_prompt(curhatan, system_instruction)
        
        # Payload untuk Google Gemini
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "topP": 0.95,
                "topK": 64,
                "maxOutputTokens": 2048,
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Ekstrak teks dari struktur response Gemini
            response_text = result['candidates'][0]['content']['parts'][0]['text']
            return self.clean_json_response(response_text)
        except Exception as e:
            print(f"[GeminiEngine] Error: {e}")
            if 'response' in locals() and response.text:
                print(f"Detail Error: {response.text}")
            raise e
