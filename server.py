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
        # Tabel untuk Semantic Cache
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curhatan TEXT UNIQUE,
            embedding TEXT,
            response TEXT,
            persona TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Tabel BARU untuk Tracking Emosi & Aktivitas (Long-term)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emotion TEXT,
            energy_level TEXT,
            curhatan_summary TEXT,
            session_id TEXT,
            created_at DATE DEFAULT (DATE('now'))
        )
        """)
        # Tambahkan kolom session_id jika belum ada (Backward compatibility)
        cursor.execute("PRAGMA table_info(user_activity)")
        columns = [col[1] for col in cursor.fetchall()]
        if "session_id" not in columns:
            cursor.execute("ALTER TABLE user_activity ADD COLUMN session_id TEXT")
        # Tabel untuk Mental Garden
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plant_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            plant_type TEXT DEFAULT 'succulent'
        )
        """)
        # Masukkan baris pertama jika kosong
        cursor.execute("INSERT OR IGNORE INTO plant_stats (id, level, xp) VALUES (1, 1, 0)")
        
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

# Konfigurasi Semantic Cache (Diperketat agar emosi lebih akurat)
SEMANTIC_CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))

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

def save_user_activity(emotion: str, energy_level: str, curhatan: str, session_id: str = None):
    """Mencatatkan histori emosi pengguna untuk keperluan statistik dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Simpan ringkasan curhatan (ambil 50 karakter pertama)
        summary = (curhatan[:47] + '..') if len(curhatan) > 50 else curhatan
        cursor.execute(
            "INSERT INTO user_activity (emotion, energy_level, curhatan_summary, session_id) VALUES (?, ?, ?, ?)",
            (emotion, energy_level, summary, session_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving to user activity: {e}")

@app.delete("/api/session/{session_id}")
def delete_session(session_id: str):
    """Menghapus data aktivitas berdasarkan session_id."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_activity WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return {"status": "deleted"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

# Pydantic Schemas untuk menangani request dan response terstruktur
class MicroStep(BaseModel):
    step_id: int
    title: str = Field(..., description="Judul langkah mikro yang konkret, singkat, dan sangat mudah dimulai.")
    description: str = Field(..., description="Penjelasan detail atau tips mikro berdurasi pendek untuk menyelesaikan langkah tersebut tanpa stres.")
    duration_minutes: int = Field(..., description="Estimasi durasi waktu dalam menit untuk menyelesaikan langkah mikro ini (di bawah 15 menit).")

class AnalysisRequest(BaseModel):
    curhatan: str
    userPersona: Optional[str] = "genz"
    sessionId: Optional[str] = None

class AnalysisResponse(BaseModel):
    empathy_response: str
    detected_emotion: str
    energy_level_required: str
    micro_steps: List[MicroStep]


@app.get("/api/health")
def health_check():
    return {"status": "ok", "engine": "FastAPI & Ollama Local"}

@app.get("/api/stats")
def get_stats():
    """Mengambil statistik emosi untuk ditampilkan di dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Hitung distribusi emosi
        cursor.execute("SELECT emotion, COUNT(*) FROM user_activity GROUP BY emotion ORDER BY COUNT(*) DESC LIMIT 5")
        emotions = [{"label": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # 2. Hitung aktivitas 7 hari terakhir
        cursor.execute("SELECT created_at, COUNT(*) FROM user_activity WHERE created_at > date('now', '-7 days') GROUP BY created_at")
        activity = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # 3. Total curhatan
        cursor.execute("SELECT COUNT(*) FROM user_activity")
        total = cursor.fetchone()[0]
        
        conn.close()
        return {
            "top_emotions": emotions,
            "weekly_activity": activity,
            "total_curhatan": total
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/plant")
def get_plant():
    """Mengambil status tanaman mental."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT level, xp, plant_type FROM plant_stats WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return {"level": row[0], "xp": row[1], "type": row[2]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/plant/grow")
def grow_plant(amount: int = 10):
    """Menambah XP tanaman mental (misal 10 XP per tugas selesai)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE plant_stats SET xp = xp + ? WHERE id = 1", (amount,))
        
        # Logika Level Up (tiap 100 XP naik level)
        cursor.execute("SELECT xp, level FROM plant_stats WHERE id = 1")
        xp, level = cursor.fetchone()
        new_level = (xp // 100) + 1
        if new_level > level:
            cursor.execute("UPDATE plant_stats SET level = ? WHERE id = 1", (new_level,))
            
        conn.commit()
        conn.close()
        return {"status": "ok", "new_xp": xp + amount, "level": new_level}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/reset")
def reset_all_data():
    """Mereset seluruh data aplikasi (Aktivitas, Garden, & Semantic Cache)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Kosongkan histori emosi
        cursor.execute("DELETE FROM user_activity")
        # Kosongkan Semantic Cache agar AI menganalisis ulang dari nol
        cursor.execute("DELETE FROM semantic_cache")
        # Reset Mental Garden
        cursor.execute("UPDATE plant_stats SET level = 1, xp = 0 WHERE id = 1")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Semua data termasuk cache memori AI berhasil dihapus."}
    except Exception as e:
        return {"error": str(e), "status": "failed"}


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
            "WAJIB: Gunakan Bahasa Indonesia sebagai bahasa UTAMA. "
            "Gaya bahasa: Kasual Jaksel (dominan Indo + bumbu kata: jujurly, valid, healing, slay, pusing bgt, spill, anyway). "
            "FOKUS TUGAS: Hanya urai stres jadi 3 langkah mikro (max 15 mnt). "
            "PEMBATASAN TOPIK: Tolak pertanyaan di luar manajemen stres/produktivitas (misal: rekomendasi makanan, berita, info umum). "
            "CARA TOLAK: Tolak dengan empati ala sahabat, contoh: 'Aduh bestie, mending kita fokus beresin rasa pusing lo dulu yuk, topik itu spill nanti aja kalau lo udah chill'."
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
            
        # Simpan ke histori aktivitas untuk Dashboard dengan session ID
        save_user_activity(
            parsed_data.get("detected_emotion", "Unknown"),
            parsed_data.get("energy_level_required", "Rendah"),
            request.curhatan,
            request.sessionId
        )
            
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

