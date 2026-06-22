import json
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    @abstractmethod
    def analyze(self, curhatan: str, persona: str) -> dict:
        """Fungsi utama untuk menganalisis curhatan."""
        pass

    def clean_json_response(self, text: str) -> dict:
        """Helper untuk membersihkan dan memparse JSON dari response LLM."""
        try:
            # Cari posisi { dan } untuk mengambil JSON jika ada teks ekstra
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
            else:
                json_str = text
            
            return json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return {
                "empathy_response": "Aduh, maaf ya bestie, otak AI gue lagi agak konslet nih pas bacak curhatan lo. Coba lagi bentar yuk!",
                "detected_emotion": "Technical Glitch",
                "energy_level_required": "Rendah",
                "micro_steps": []
            }
