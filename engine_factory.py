import os
from engines.base import BaseEngine
from engines.ollama_engine import OllamaEngine
from engines.openai_engine import OpenAIEngine
from engines.gemini_engine import GeminiEngine

def get_engine() -> BaseEngine:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    if provider == "openai" or provider == "openrouter" or provider == "groq":
        return OpenAIEngine()
    elif provider == "gemini":
        return GeminiEngine()
    else:
        return OllamaEngine()
