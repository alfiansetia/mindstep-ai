import os
import json
import math
import sqlite3
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load variabel dari file .env (jika ada)
load_dotenv()

# Inisialisasi Database SQLite untuk Semantic Cache
DB_PATH = "cache.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curhatan TEXT UNIQUE,
            embedding TEXT, -- Vektor embedding yang disimpan sebagai JSON Array
            response TEXT,  -- Respons terstruktur (AnalysisResponse) sebagai JSON String
            persona TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing SQLite database: {e}")

init_db()

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

# Konfigurasi Semantic Cache
SEMANTIC_CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.88"))

def get_embedding(text: str) -> List[float]:
    """Menghitung vektor embedding dari suatu teks menggunakan endpoint /api/embed Ollama (versi terbaru)."""
    embed_url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
    payload = {
        "model": OLLAMA_MODEL,
        "input": text
    }
    try:
        response = requests.post(embed_url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        # Versi terbaru mengembalikan 'embeddings' (jamak), kita ambil indeks pertama
        result = response.json()
        if "embeddings" in result:
            return result["embeddings"][0]
        return result.get("embedding", [])
    except Exception as e:
        print(f"⚠️ Gagal generate embedding dari Ollama: {e}")
        return []

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Menghitung nilai kedekatan/kemiripan arah dua buah vektor (Cosine Similarity)."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def find_semantic_cache(new_embedding: List[float], persona: str) -> Optional[dict]:
    """Mencari data curhatan serupa yang sudah pernah diproses sebelumnya di cache database."""
    if not new_embedding:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT curhatan, embedding, response FROM semantic_cache WHERE persona = ?", (persona,))
        rows = cursor.fetchall()
        conn.close()

        best_match = None
        highest_similarity = -1.0

        for curhatan, embedding_json, response_json in rows:
            try:
                cached_embedding = json.loads(embedding_json)
                sim = cosine_similarity(new_embedding, cached_embedding)
                if sim > highest_similarity:
                    highest_similarity = sim
                    best_match = {
                        "curhatan": curhatan,
                        "response": json.loads(response_json),
                        "similarity": sim
                    }
            except Exception as e:
                print(f"Error parsing cache row: {e}")
                continue

        if best_match and highest_similarity >= SEMANTIC_CACHE_THRESHOLD:
            print(f"🚀 [Semantic Cache HIT] Curhatan baru mirip dengan '{best_match['curhatan']}' (Similarity: {highest_similarity:.4f} >= Threshold: {SEMANTIC_CACHE_THRESHOLD})")
            return best_match["response"]

        print(f"⚡ [Semantic Cache MISS] Kemiripan tertinggi: {highest_similarity:.4f} (Threshold: {SEMANTIC_CACHE_THRESHOLD})")
        return None
    except Exception as e:
        print(f"Error reading semantic cache: {e}")
        return None

def save_semantic_cache(curhatan: str, embedding: List[float], response_data: dict, persona: str):
    """Menyimpan curhatan beserta embedding dan responnya ke cache database."""
    if not embedding:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO semantic_cache (curhatan, embedding, response, persona) VALUES (?, ?, ?, ?)",
            (curhatan, json.dumps(embedding), json.dumps(response_data), persona)
        )
        conn.commit()
        conn.close()
        print("💾 Berhasil menyimpan data ke Semantic Cache.")
    except Exception as e:
        print(f"Error saving to semantic cache: {e}")

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
    
    # Cek apakah curhatan serupa ada di Semantic Cache
    embedding = []
    if SEMANTIC_CACHE_ENABLED:
        embedding = get_embedding(request.curhatan)
        cached_response = find_semantic_cache(embedding, persona)
        if cached_response:
            return cached_response
    
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
            "Kamu adalah MindStep AI, bestie produktivitas Gen Z. "
            "WAJIB: Gunakan Bahasa Indonesia sebagai bahasa UTAMA. DILARANG menjawab full dalam Bahasa Inggris. "
            "Gaya bahasa: Kasual Jaksel (dominan Indo + bumbu kata: jujurly, valid, healing, slay, pusing bgt, spill, anyway). "
            "Tugasmu: urai stres jadi 3 langkah mikro (max 15 mnt) yang nyambung dan solutif. JANGAN SALIN CONTOH."
        )

    # 2. Rancang Prompt agar Output Ollama tervalidasi dalam Format JSON yang Konsisten
    prompt = f"""
Sistem Instruksi: {system_instruction}

ATURAN BAHASA & LOGIKA (WAJIB DIIKUTI):
1. NO FULL ENGLISH: Jangan pernah membalas satu kalimat pun dalam Bahasa Inggris penuh. Gunakan Bahasa Indonesia Jaksel yang luwes.
2. HUBUNGAN LOGIS: field "micro_steps" HARUS solusi nyata untuk masalah di "Curhatan Baru Pengguna". 
3. PERSONA: Tetap gunakan gaya Gen Z Jaksel (Indonsia + Slang) di "empathy_response" dan "title".
4. OUTPUT JSON: Keluarkan hanya JSON bersih.

ISI JSON HARUS:
- "empathy_response": Respon empati hangat dalam Bahasa Indonesia Jaksel (Bukan Inggris!).
- "detected_emotion": Emosi (misal: "Overwhelmed parah", "Burnout", "Dead-end").
- "energy_level_required": "Rendah", "Sedang", atau "Tinggi".
- "micro_steps": 3 langkah konkret dalam Bahasa Indonesia.

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
        
        # Simpan respons baru ke Semantic Cache
        if SEMANTIC_CACHE_ENABLED and embedding:
            save_semantic_cache(request.curhatan, embedding, parsed_data, persona)
            
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

