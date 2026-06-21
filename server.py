import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load variabel dari file .env (jika ada)
load_dotenv()

# Inisialisasi FastAPI
app = FastAPI(
    title="MindStep AI Local Python Backend",
    description="Backend alternatif menggunakan FastAPI & Ollama untuk produktivitas mikro berbasis LLM Lokal."
)

# Konfigurasi CORS agar aplikasi React bisa berkomunikasi ke server Python lokal Anda
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Silakan ganti sesuai port React Anda (misal http://localhost:3000)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL Ollama — ubah via .env agar bisa dipakai dari luar (misal remote server)
# Contoh: OLLAMA_BASE_URL=http://192.168.1.100:11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"

# Nama model Ollama yang diunduh (misal: llama3, mistral, gemma2, dll.)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Timeout request ke Ollama (detik) — LLM lokal bisa lambat, default 180 detik
# Naikkan via .env jika masih sering 503: OLLAMA_TIMEOUT=300
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

# Pydantic Schemas untuk menangani request dan response terstruktur
class MicroStep(BaseModel):
    step_id: int
    title: str = Field(..., description="Judul langkah mikro yang konkret, singkat, dan sangat mudah dimulai.")
    description: str = Field(..., description="Penjelasan detail atau tips mikro berdurasi pendek untuk menyelesaikan langkah tersebut tanpa stres.")
    duration_minutes: int = Field(..., description="Estimasi durasi waktu dalam menit untuk menyelesaikan langkah mikro ini (di bawah 15 menit).")

class AnalysisRequest(BaseModel):
    curhatan: str
    contextHistory: Optional[str] = None
    userPersona: Optional[str] = "genz"

class AnalysisResponse(BaseModel):
    empathy_response: str
    detected_emotion: str
    energy_level_required: str
    micro_steps: List[MicroStep]


@app.get("/api/health")
def health_check():
    return {"status": "ok", "engine": "FastAPI & Ollama Local"}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_brain_dump(request: AnalysisRequest):
    """
    Endpoint alternatif untuk memisahkan tugas besar berantakan pengguna 
    menjadi 3 langkah mikro menggunakan LLM lokal (Ollama).
    """
    import requests # Pastikan library requests terinstall (pip install requests)

    persona = request.userPersona or "genz"
    
    # 1. Tentukan Sistem Instruksi dan Gaya bicara berdasarkan Persona pilihan
    if persona == "professional":
        system_instruction = (
            "Kamu adalah MindStep AI, asisten produktivitas mikro profesional untuk pekerja atau orang dewasa di Indonesia. "
            "Tugasmu membantu mengurai stres kerjaan menjadi maksimal 3 langkah mikro produktivitas di bawah 15 menit. "
            "Gunakan Bahasa Indonesia baku yang baik, sopan, tulus, dewasa, dan sangat tenang. "
            "WAJIB: Seluruh respons, termasuk semua nilai dalam JSON (empathy_response, detected_emotion, title, description) HARUS ditulis dalam Bahasa Indonesia. DILARANG menggunakan Bahasa Inggris kecuali istilah teknis yang sudah sangat umum. "
            "JANGAN REKOMENDASIKAN MAKANAN/KULINER atau topik di luar manajemen stres/produktivitas. Tolak dengan sopan jika ada pertanyaan di luar topik."
        )
    else:
        system_instruction = (
            "Kamu adalah MindStep AI, asisten produktivitas mikro khusus Gen Z di Indonesia. "
            "Tugasmu membantu mengurai stres atau penundaan tugas menjadi maksimal 3 langkah produktivitas sangat ringan. "
            "Gunakan gaya bahasa kasual Bahasa Indonesia campur sedikit kata Inggris populer ala anak Jaksel (misal: 'overwhelmed', 'burnout', 'okay', 'chill'). "
            "WAJIB: Seluruh respons JSON HARUS menggunakan Bahasa Indonesia sebagai bahasa utama. Jangan balas full Bahasa Inggris. "
            "JANGAN REKOMENDASIKAN MAKANAN/KULINER atau topik di luar manajemen stres/produktivitas. Tolak santai ala Gen Z jika ada."
        )

    # 2. Rancang Prompt agar Output Ollama tervalidasi dalam Format JSON yang Konsisten
    prompt = f"""
Sistem Instruksi: {system_instruction}

ATURAN DETEKSI PERGESERAN KONTEKS (CONTEXT SHIFT):
- Periksa apakah topik pada "Curhatan Baru Pengguna" berbeda sama sekali dengan topik di "Context History Pengguna" (misal: riwayat sebelumnya tentang skripsi, tetapi curhatan baru tentang konflik dengan teman/keluarga).
- Jika terjadi pergeseran konteks (topik baru berubah total), kamu WAJIB mengabaikan informasi pada "Context History Pengguna". Jangan bawa masalah lama ke respons baru.
- Fokus 100% pada curhatan baru untuk empathy_response dan micro_steps. Jangan berhalusinasi menyarankan langkah yang berhubungan dengan topik lama.

ATURAN BAHASA (WAJIB DIIKUTI):
- Semua nilai teks dalam JSON HARUS menggunakan Bahasa Indonesia.
- Field "empathy_response": wajib Bahasa Indonesia.
- Field "detected_emotion": boleh satu kata bahasa Inggris umum (misal: Anxious, Burnout, Overwhelmed).
- Field "energy_level_required": gunakan "Rendah", "Sedang", atau "Tinggi" (bukan Low/Medium/High).
- Field "title" dan "description" di micro_steps: wajib Bahasa Indonesia.
- JANGAN balas dengan full Bahasa Inggris.

Context History Pengguna:
{request.contextHistory or "Tidak ada riwayat pembicaraan sebelumnya."}

Curhatan Baru Pengguna:
"{request.curhatan}"

Keluarkan balasan HANYA dalam struktur JSON bersih berikut (tanpa markdown, tanpa ```json):
{{
  "empathy_response": "Kalimat respons empati hangat dalam Bahasa Indonesia.",
  "detected_emotion": "Label emosi utama (misal: Anxious, Burnout, Overwhelmed, Confused)",
  "energy_level_required": "Rendah / Sedang / Tinggi",
  "micro_steps": [
    {{
      "step_id": 1,
      "title": "Langkah pertama yang sangat enteng dalam Bahasa Indonesia",
      "description": "Penjelasan singkat cara memulainya dalam Bahasa Indonesia.",
      "duration_minutes": 3
    }},
    {{
      "step_id": 2,
      "title": "Langkah lanjutan yang logis dalam Bahasa Indonesia",
      "description": "Eksplorasi kecil berikutnya dalam Bahasa Indonesia.",
      "duration_minutes": 8
    }},
    {{
      "step_id": 3,
      "title": "Langkah final ringan dalam Bahasa Indonesia",
      "description": "Langkah ketiga agar ada progress kecil terarah.",
      "duration_minutes": 10
    }}
  ]
}}
"""

    # 3. Kirim permintaan HTTP ke daemon Ollama lokal Anda
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json" # Memaksa Ollama 0.1.33+ mengeluarkan format JSON yang valid
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        
        result_json = response.json()
        response_text = result_json.get("response", "").strip()

        # Parse text string JSON dari Ollama menjadi Dictionary Python
        parsed_data = json.loads(response_text)
        return parsed_data

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama timeout setelah {OLLAMA_TIMEOUT} detik. Model mungkin masih loading atau overloaded. Coba naikkan OLLAMA_TIMEOUT di .env."
        )
    except requests.exceptions.RequestException as req_err:
        raise HTTPException(
            status_code=503, 
            detail=f"Gagal terhubung ke Ollama lokal di {OLLAMA_API_URL}. Pastikan Ollama menyala! Error: {str(req_err)}"
        )
    except json.JSONDecodeError as json_err:
        raise HTTPException(
            status_code=500, 
            detail=f"Ollama menghasilkan format JSON yang tidak valid. Silakan coba lagi. Error: {str(json_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Terjadi kesalahan internal: {str(e)}"
        )

# Serve React build (dist folder) in production
# Jika folder 'dist' hasil build front-end ada, serve sebagai file statis
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        # Jika bukan path api, arahkan ke index.html
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse("dist/index.html")

# Panduan singkat untuk menjalankan server Python ini di komputer lokal Anda:
#  1. Install Python 3.9+
#  2. Jalankan: pip install fastapi uvicorn requests pydantic python-dotenv
#  3. Salin .env.example ke .env lalu isi OLLAMA_BASE_URL sesuai lokasi Ollama Anda
#  4. Download Ollama dari https://ollama.com dan install ke komputer Anda
#  5. Jalankan model pilihan Anda di terminal, contoh: ollama run llama3
#  6. Jalankan server ini dengan perintah: uvicorn server:app --host 0.0.0.0 --port 8000

