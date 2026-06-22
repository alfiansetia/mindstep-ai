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
    if not os.path.exists(DB_PATH):
        print("Initial database created.")
        
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        # Aktifkan WAL Mode agar tidak 'database is locked'
        cursor.execute("PRAGMA journal_mode=WAL")
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
        # Tabel untuk Quote Harian
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT,
            author TEXT,
            target_date DATE UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# Konfigurasi Semantic Cache (Diperketat agar emosi lebih akurat)
SEMANTIC_CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))

# Import Engine Factory
from engine_factory import get_engine

def get_embedding(text: str) -> List[float]:
    """Menghitung vektor embedding menggunakan Ollama (dibutuhkan untuk Semantic Cache)."""
    # Catatan: Embedding tetap menggunakan Ollama lokal karena gratis & cepat untuk caching lokal.
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip('/')
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
    embed_url = f"{ollama_base}/api/embed"
    try:
        response = requests.post(embed_url, json={"model": ollama_model, "input": text}, timeout=10)
        response.raise_for_status()
        result = response.json()
        if "embeddings" in result:
            return result["embeddings"][0]
        return result.get("embedding", [])
    except Exception as e:
        print(f"⚠️ Gagal generate embedding: {e}")
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
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
    provider = os.getenv("LLM_PROVIDER", "ollama")
    return {"status": "ok", "engine": provider}

@app.get("/api/stats")
def get_stats():
    """Mengambil statistik emosi untuk ditampilkan di dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
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

@app.get("/api/history")
def get_detailed_history(limit: int = 20):
    """Mengambil history curhat detail untuk tampilan Diary."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, emotion, energy_level, curhatan_summary, created_at, session_id FROM user_activity ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for r in rows:
            history.append({
                "id": r[0],
                "emotion": r[1],
                "energy": r[2],
                "summary": r[3],
                "date": r[4],
                "session_id": r[5]
            })
        return history
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/quote")
def get_daily_quote(persona: str = "genz"):
    """Mengambil atau membuat quote penyemangat harian yang personal."""
    from datetime import date
    today_date = date.today().isoformat()
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        # Cek apakah sudah ada quote buat hari ini
        cursor.execute("SELECT quote, author FROM daily_quotes WHERE target_date = ?", (today_date,))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return {"quote": row[0], "author": row[1]}
        
        # Ambil emosi terakhir user agar quote-nya 'nyambung'
        cursor.execute("SELECT emotion FROM user_activity ORDER BY id DESC LIMIT 1")
        last_emotion = cursor.fetchone()
        emotion_context = last_emotion[0] if last_emotion else "santai"
        
        instruction = f"Buatlah 1 kalimat quote penyemangat pendek (max 15 kata) untuk seseorang yang sedang merasa {emotion_context}. Gunakan gaya bahasa {persona}. Jangan pakai kutipan tokoh terkenal, buatlah original."
        
        engine = get_engine()
        res = engine.analyze(f"Buat quote: {instruction}", persona)
        
        quote_text = res.get("empathy_response", "Tetap semangat ya bestie! ✨")
        author = "MindStep AI"
        
        cursor.execute(
            "INSERT INTO daily_quotes (quote, author, target_date) VALUES (?, ?, ?)",
            (quote_text, author, today_date)
        )
        conn.commit()
        conn.close()
        
        return {"quote": quote_text, "author": author}
    except Exception as e:
        print(f"Error getting quote: {e}")
        return {"quote": "Setiap progress kecil tetaplah progress. Kamu hebat!", "author": "MindStep AI"}

@app.get("/api/plant")
def get_plant():
    """Mengambil status tanaman mental."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE plant_stats SET xp = xp + ? WHERE id = 1", (amount,))
        
        # Logika Level Up (tiap 100 XP naik level)
        cursor.execute("SELECT xp, level FROM plant_stats WHERE id = 1")
        row = cursor.fetchone()
        xp, level = row[0], row[1]
        
        new_level = (xp // 100) + 1
        if new_level > level:
            cursor.execute("UPDATE plant_stats SET level = ? WHERE id = 1", (new_level,))
            level = new_level
            
        conn.commit()
        conn.close()
        return {"status": "ok", "new_xp": xp, "level": level}
    except Exception as e:
        if 'conn' in locals(): conn.close()
        return {"error": str(e)}

@app.post("/api/reset")
def reset_all_data():
    """Mereset seluruh data aplikasi (Aktivitas, Garden, & Semantic Cache)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
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
    Endpoint utama untuk menganalisis curhatan pengguna menggunakan engine LLM pilihan.
    """
    persona = request.userPersona or "genz"
    
    # 1. Cek Semantic Cache
    embedding = []
    if SEMANTIC_CACHE_ENABLED:
        embedding = get_embedding(request.curhatan)
        cached_response = find_semantic_cache(embedding, persona)
        if cached_response:
            return cached_response
    
    # 2. Panggil Engine LLM yang dipilih (Ollama, OpenAI, dll)
    try:
        engine = get_engine()
        parsed_data = engine.analyze(request.curhatan, persona)
            
        # 3. Simpan ke Cache & Aktivitas
        if SEMANTIC_CACHE_ENABLED and embedding:
            save_semantic_cache(request.curhatan, embedding, parsed_data, persona)
            
        save_user_activity(
            parsed_data.get("detected_emotion", "Unknown"),
            parsed_data.get("energy_level_required", "Rendah"),
            request.curhatan,
            request.sessionId
        )
            
        return parsed_data

    except Exception as e:
        print(f"🚨 [Analysis Error]: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Gagal menganalisis curhatan: {str(e)}"
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

