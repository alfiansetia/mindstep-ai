<div align="center">
  <img width="1200" height="475" alt="MindStep AI Banner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# MindStep AI

> Asisten produktivitas mikro berbasis LLM — ubah stres & penundaan jadi 3 langkah kecil yang bisa langsung dikerjakan.

Proyek ini terdiri dari dua bagian yang bisa dijalankan secara bersamaan:

| Bagian | Teknologi | Port default |
|--------|-----------|-------------|
| **Frontend (FE)** | React + Vite + Tailwind | `http://localhost:5173` |
| **Backend Node (BE-TS)** | Express + TypeScript (`server.ts`) | `http://localhost:3000` |
| **Backend Python (BE-PY)** | FastAPI + Ollama (`server.py`) | `http://localhost:8000` |

---

## Prasyarat

- **Node.js** v18+
- **Python** 3.9+
- **Ollama** — download di [ollama.com](https://ollama.com)
- Package manager: `npm` dan `pip3`

---

## 1. Konfigurasi Environment

Salin file contoh lalu isi sesuai kebutuhan:

```bash
cp .env.example .env
```

Buka `.env` dan sesuaikan:

```env
# Kunci API Gemini (hanya diperlukan jika AI_BACKEND=gemini)
GEMINI_API_KEY="isi_api_key_kamu"

# ── Mode AI Backend ─────────────────────────────────────────
# 'gemini'  → pakai Google Gemini API (butuh GEMINI_API_KEY valid)
# 'ollama'  → pakai model lokal via Python FastAPI (tanpa API key)
AI_BACKEND="ollama"

# URL Python FastAPI (digunakan server.ts saat AI_BACKEND=ollama)
OLLAMA_BACKEND_URL="http://localhost:8000"

# ── Frontend API Target ──────────────────────────────────────
# Kosong ("")           → FE hit server.ts (Node.js) di port 3000
# http://localhost:8000 → FE langsung hit Python FastAPI
VITE_API_BASE_URL="http://localhost:8000"

# ── Konfigurasi Ollama ───────────────────────────────────────
# Lokal: http://localhost:11434
# Remote: http://192.168.1.100:11434
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"
```

---

## 2. Menjalankan Backend Python / FastAPI (Ollama Mode)

Backend ini menggunakan **Ollama** (LLM lokal) via FastAPI dan **tidak membutuhkan API key** apapun.

### Install dependensi Python

```bash
pip3 install fastapi uvicorn requests pydantic python-dotenv
```

### Pastikan Ollama menyala & model tersedia

```bash
# Pull model jika belum ada
ollama pull llama3

# (opsional) cek model yang tersedia
ollama list
```

### Jalankan server FastAPI

```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Cek status:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","engine":"FastAPI & Ollama Local"}
```

---

## 3. Menjalankan Frontend (React + Vite)

Frontend akan langsung hit Python FastAPI jika `VITE_API_BASE_URL=http://localhost:8000` di `.env`.

```bash
# Install dependensi (hanya perlu sekali)
npm install

# Jalankan Vite dev server (FE saja)
npm run dev
```

Frontend berjalan di → **http://localhost:5173**

> **Catatan:** `VITE_API_BASE_URL` di `.env` menentukan ke mana FE mengirim request:

---

## 4. Menjalankan Backend Node.js (Gemini Mode — opsional)

Gunakan ini **hanya jika** ingin memakai Google Gemini API atau proxy Node.js. Pastikan `AI_BACKEND` di `.env` sudah diset dengan benar.

```bash
npm run dev:node
```

> `npm run dev:node` menjalankan `tsx server.ts` di port 3000 (include Vite middleware).

---

## 5. Menjalankan FE + BE Python Bersamaan (Rekomendasi Ollama)

Buka **2 terminal terpisah**:

```bash
# Terminal 1 — Backend Python (FastAPI + Ollama)
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend (Vite dev server)
npm run dev
```

Pastikan di `.env`:
```env
AI_BACKEND="ollama"
VITE_API_BASE_URL="http://localhost:8000"
OLLAMA_BASE_URL="http://localhost:11434"
```

---

## Ringkasan Mode & Alur Request

| Mode | `VITE_API_BASE_URL` | `AI_BACKEND` | Alur |
|------|---------------------|--------------|------|
| **Ollama (rekomendasi)** | `http://localhost:8000` | `ollama` | FE → FastAPI → Ollama |
| **Gemini via Node** | *(kosong)* | `gemini` | FE → server.ts → Gemini API |
| **Ollama via Node** | *(kosong)* | `ollama` | FE → server.ts → FastAPI → Ollama |

---

## Struktur Project

```
mindstep-ai/
├── src/              # Kode React (Frontend)
│   └── App.tsx       # Komponen utama, VITE_API_BASE_URL dipakai di sini
├── server.ts         # Backend Node.js (Gemini API / proxy ke Ollama)
├── server.py         # Backend Python (FastAPI + Ollama)
├── .env              # Konfigurasi lokal (tidak di-commit ke git)
├── .env.example      # Template konfigurasi
└── vite.config.ts    # Konfigurasi Vite
```

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `API key not valid` | Pastikan `AI_BACKEND=ollama` di `.env`, atau isi `GEMINI_API_KEY` yang valid |
| `Gagal terhubung ke Ollama` | Jalankan `ollama pull llama3` lalu cek `OLLAMA_BASE_URL` di `.env` |
| `CORS error` di browser | Pastikan Python FastAPI menyala di port 8000 |
| `zsh: command not found: uvicorn` | Gunakan `python3 -m uvicorn ...` (bukan langsung `uvicorn`) |
| Port sudah terpakai | Ganti port di perintah uvicorn dan sesuaikan `VITE_API_BASE_URL` |
| Model tidak ditemukan | Jalankan `ollama pull <nama-model>` terlebih dahulu |
