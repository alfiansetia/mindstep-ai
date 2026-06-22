import os
import json
from google import genai
from google.genai import types
from engines.base import BaseEngine
from prompts import get_system_instruction, get_analysis_prompt

class GeminiEngine(BaseEngine):
    def __init__(self):
        # Konfigurasi Client Gemini baru (SDK v2)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_id = os.getenv("AI_MODEL", "gemini-flash-lite-latest").strip()
        
        if not self.api_key:
            print("⚠️ [GeminiEngine] API Key tidak ditemukan di .env!")
            
        self.client = genai.Client(api_key=self.api_key)

    def analyze(self, curhatan: str, persona: str) -> dict:
        system_instruction = get_system_instruction(persona)
        prompt = get_analysis_prompt(curhatan, system_instruction)
        
        try:
            # Panggil Gemini via SDK baru
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=64,
                    max_output_tokens=2048,
                    response_mime_type="application/json"
                )
            )
            
            if not response.text:
                raise Exception("Gemini SDK v2 returned an empty response.")
                
            return self.clean_json_response(response.text)
        except Exception as e:
            print(f"🚨 [GeminiEngine SDK v2] Error: {e}")
            raise e
