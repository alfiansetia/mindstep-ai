<div align="center">
  <img width="1200" height="475" alt="MindStep AI Banner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# MindStep AI

> Asisten produktivitas mikro berbasis LLM Lokal (Ollama) — ubah stres & penundaan jadi 3 langkah kecil yang bisa langsung dikerjakan.

Proyek ini telah dimigrasikan sepenuhnya menggunakan Python backend untuk melayani model AI lokal (Ollama) secara cepat dan offline.

| Bagian                  | Teknologi                  | Port default            |
| ----------------------- | -------------------------- | ----------------------- |
| **Frontend (FE)**       | React + Vite + Tailwind    | `http://localhost:5173` |
| **Backend Python (BE)** | FastAPI + Multi-LLM Engine | `http://localhost:8000` |

---

## 🚀 Fitur Baru: Multi-LLM Architecture

Proyek ini sekarang mendukung berbagai provider AI secara dinamis. Kamu bisa beralih dari model lokal (Ollama) ke model Cloud (GPT-4, Claude, dll) hanya dengan mengganti satu baris di `.env`.

### Supported Providers:

- **Ollama** (Default) — Gratis, lokal, & menjaga privasi.
- **OpenAI** — Menggunakan GPT-3.5 atau GPT-4.
- **Google Gemini** — Menggunakan model Gemini 1.5 Pro/Flash.
- **OpenRouter** — Akses ke Claude, Llama-3, dan ratusan model lainnya.
- **Groq** — Analisis super cepat dengan model Llama/Mixtral.

---

## 1. Konfigurasi Environment

Salin file contoh `.env.example` ke `.env` (atau edit file `.env` yang ada):

```env
# ── Pilih Provider AI ───────────────────────────────────────
# Opsi: ollama, openai, openrouter, groq
LLM_PROVIDER="ollama"

# ── Konfigurasi Cloud (Jika bukan Ollama) ───────────────────
AI_BASE_URL="https://api.openai.com/v1"
AI_API_KEY="sk-your-key-here"
AI_MODEL="gpt-3.5-turbo"

# ── Konfigurasi Ollama ───────────────────────────────────────
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"
OLLAMA_TIMEOUT="180"

# ── Konfigurasi Semantic Cache ───────────────────────────────
SEMANTIC_CACHE_ENABLED="true"
SEMANTIC_CACHE_THRESHOLD="0.95"
```

---

## 2. Struktur Folder & Modul

Kami menggunakan **Adapter Pattern** untuk menjaga kode tetap bersih:

```
mindstep-ai/
├── src/                # Kode React (Frontend)
├── engines/            # Modul LLM Engine (Modular)
│   ├── base.py         # Blueprint dasar AI engine
│   ├── ollama_engine.py
│   └── openai_engine.py
├── prompts.py          # Pusat kendali instruksi "Bestie AI"
├── engine_factory.py   # Logika pemilihan engine otomatis
├── server.py           # Backend FastAPI & DB Logic
├── cache.db            # Database SQLite (Otomatis)
└── .env                # Semua setingan di sini
```

---

## 3. Menjalankan Aplikasi

1. **Backend**: `python -m uvicorn server:app --reload`
2. **Frontend**: `npm run dev`

---

## Alur Request Baru

```
React Frontend
       ↓ (POST /api/analyze)
FastAPI Backend
       ↓ (engine_factory)
Pilih Provider (Ollama / GPT / OpenRouter)
       ↓ (JSON Response)
FastAPI Backend (Simpan ke DB & Cache)
       ↓
Kembali ke Frontend
```
