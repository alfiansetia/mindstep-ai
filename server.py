import os
import json
import math
import sqlite3
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header
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
        # Tabel untuk Mental Garden (Sekarang per-user)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plant_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
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
        # Tabel untuk menyimpan session lengkap (Sekarang per-user)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            timestamp TEXT,
            original_curhatan TEXT,
            empathy_response TEXT,
            detected_emotion TEXT,
            energy_level_required TEXT,
            micro_steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Backward compatibility for user_id columns
        for table in ["user_activity", "sessions"]:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [col[1] for col in cursor.fetchall()]
            if "user_id" not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT DEFAULT 'anonymous'")
        
        # Migrasi plant_stats ke per-user jika ID 1 masih ada tanpa user_id
        cursor.execute("PRAGMA table_info(plant_stats)")
        cols = [col[1] for col in cursor.fetchall()]
        if "user_id" not in cols:
             # This is a bit tricky, we might just drop and recreate if it's empty or has dev data
             cursor.execute("DROP TABLE plant_stats")
             cursor.execute("""
                CREATE TABLE plant_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE,
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

def log_user_activity(emotion, energy, curhatan, user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_activity (emotion, energy_level, curhatan_summary, user_id)
        VALUES (?, ?, ?, ?)
        """, (emotion, energy, curhatan[:100], user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")


def save_session_full(res, user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO sessions (id, user_id, timestamp, original_curhatan, empathy_response, detected_emotion, energy_level_required, micro_steps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res["id"], 
            user_id,
            res["timestamp"], 
            res["original_curhatan"], 
            res["empathy_response"], 
            res["detected_emotion"], 
            res["energy_level_required"],
            json.dumps(res["micro_steps"])
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving session: {e}")

@app.get("/api/sessions")
async def get_sessions(x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    sessions = []
    for r in rows:
        sessions.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "original_curhatan": r["original_curhatan"],
            "empathy_response": r["empathy_response"],
            "detected_emotion": r["detected_emotion"],
            "energy_level_required": r["energy_level_required"],
            "micro_steps": json.loads(r["micro_steps"])
        })
    return sessions

@app.put("/api/sessions/{session_id}/steps")
async def update_steps(session_id: str, steps: List[dict], x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET micro_steps = ? WHERE id = ? AND user_id = ?", (json.dumps(steps), session_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str, x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

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
async def get_stats(x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Top Emotions
    cursor.execute("""
        SELECT emotion, COUNT(*) as count 
        FROM user_activity 
        WHERE user_id = ?
        GROUP BY emotion 
        ORDER BY count DESC LIMIT 5
    """, (user_id,))
    emotions = [{"label": row[0], "count": row[1]} for row in cursor.fetchall()]
    
    # 2. Activity logic
    cursor.execute("""
        SELECT created_at, COUNT(*) 
        FROM user_activity 
        WHERE user_id = ?
        GROUP BY created_at 
        ORDER BY created_at DESC LIMIT 7
    """, (user_id,))
    activity = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
    
    # 3. Total curhatan
    cursor.execute("SELECT COUNT(*) FROM user_activity WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]
    
    conn.close()
    return {
        "top_emotions": emotions,
        "weekly_activity": activity,
        "total_curhatan": total
    }

@app.get("/api/history")
async def get_mood_diary(x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT created_at, emotion, energy_level, curhatan_summary 
        FROM user_activity 
        WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 20
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({
            "date": r[0],
            "emotion": r[1],
            "energy": r[2],
            "summary": r[3],
            "id": f"{r[0]}-{r[1]}"
        })
    return history

@app.get("/api/quote")
def get_daily_quote(persona: str = "genz"):
    """Quote di-disable sesuai request user."""
    return {"quote": "", "author": ""}

@app.get("/api/plant")
async def get_plant_stats(x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT level, xp, plant_type FROM plant_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        # Buat baru untuk user unik ini
        cursor.execute("INSERT INTO plant_stats (user_id, level, xp, plant_type) VALUES (?, 1, 0, 'succulent')", (user_id,))
        conn.commit()
        return {"level": 1, "xp": 0, "plant_type": "succulent"}
        
    conn.close()
    return {"level": row[0], "xp": row[1], "plant_type": row[2] or "succulent"}

@app.post("/api/plant/xp")
async def add_xp(amount: int, x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ambil data lama
    cursor.execute("SELECT level, xp FROM plant_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        row = (1, 0)
        cursor.execute("INSERT INTO plant_stats (user_id, level, xp) VALUES (?, 1, 0)", (user_id,))
        
    level, xp = row
    new_xp = xp + amount
    
    # Level up logic: every 100 XP
    new_level = level + (new_xp // 100)
    remaining_xp = new_xp % 100
    
    cursor.execute("UPDATE plant_stats SET level = ?, xp = ? WHERE user_id = ?", (new_level, remaining_xp, user_id))
    conn.commit()
    conn.close()
    return {"level": new_level, "xp": remaining_xp}

@app.post("/api/reset")
async def reset_all_data(x_user_id: Optional[str] = Header(None)):
    user_id = x_user_id or "anonymous"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_activity WHERE user_id = ?", (user_id,))
        cursor.execute("UPDATE plant_stats SET level = 1, xp = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return {"status": "data cleared for user"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_brain_dump(request: AnalysisRequest, x_user_id: Optional[str] = Header(None)):
    """
    Endpoint utama untuk menganalisis curhatan pengguna menggunakan engine LLM pilihan.
    """
    user_id = x_user_id or "anonymous"
    # Batasi input maksimal 3000 karakter demi performa
    if len(request.curhatan) > 3000:
        raise HTTPException(status_code=400, detail="Curhatan kamu terlalu panjang (maksimal 3000 karakter). Coba cicil dulu ya!")

    persona = request.userPersona or "genz"
    
    # 1. Cek Semantic Cache
    embedding = []
    if SEMANTIC_CACHE_ENABLED:
        embedding = get_embedding(request.curhatan)
        cached_response = find_semantic_cache(embedding, persona)
        if cached_response:
            # Simpan ke riwayat session per user
            from datetime import datetime
            cached_response["id"] = request.sessionId or f"sess_{int(datetime.now().timestamp())}"
            cached_response["timestamp"] = datetime.now().isoformat()
            cached_response["original_curhatan"] = request.curhatan
            save_session_full(cached_response, user_id)
            log_user_activity(cached_response.get("detected_emotion", "Unknown"), cached_response.get("energy_level_required", "Rendah"), request.curhatan, user_id)
            return cached_response
    
    # 2. Panggil Engine LLM yang dipilih (Ollama, OpenAI, dll)
    try:
        engine = get_engine()
        parsed_data = engine.analyze(request.curhatan, persona)
            
        # 3. Simpan ke Cache & Aktivitas
        if SEMANTIC_CACHE_ENABLED and embedding:
            save_semantic_cache(request.curhatan, embedding, parsed_data, persona)
            
        from datetime import datetime
        now_ts = datetime.now().isoformat()
        session_id = request.sessionId or f"sess_{int(datetime.now().timestamp())}"
        
        # Prepare full session data
        full_session = {
            "id": session_id,
            "timestamp": now_ts,
            "original_curhatan": request.curhatan,
            "empathy_response": parsed_data.get("empathy_response", ""),
            "detected_emotion": parsed_data.get("detected_emotion", ""),
            "energy_level_required": parsed_data.get("energy_level_required", ""),
            "micro_steps": parsed_data.get("micro_steps", [])
        }
        
        save_session_full(full_session, user_id)
        log_user_activity(
            parsed_data.get("detected_emotion", "Unknown"),
            parsed_data.get("energy_level_required", "Rendah"),
            request.curhatan,
            user_id
        )
            
        return full_session


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

