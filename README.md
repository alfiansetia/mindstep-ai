<div align="center">
  <img width="1200" height="475" alt="MindStep AI Banner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# MindStep AI

> Asisten produktivitas mikro berbasis LLM Lokal (Ollama) — ubah stres & penundaan jadi 3 langkah kecil yang bisa langsung dikerjakan.

Proyek ini telah dimigrasikan sepenuhnya menggunakan Python backend untuk melayani model AI lokal (Ollama) secara cepat dan offline.

| Bagian | Teknologi | Port default |
|--------|-----------|-------------|
| **Frontend (FE)** | React + Vite + Tailwind | `http://localhost:5173` |
| **Backend Python (BE)** | FastAPI + Ollama (`server.py`) | `http://localhost:8000` |

---

## Prasyarat

- **Node.js** v18+
- **Python** 3.9+
- **Ollama** — unduh di [ollama.com](https://ollama.com)
- Package manager: `npm` dan `pip3`

---

## 1. Konfigurasi Environment

Salin file contoh `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Buka `.env` dan sesuaikan:

```env
# URL base API yang digunakan oleh Frontend (React).
# Kosong ("")            = FE hit server yang sama dengan host (default)
# http://localhost:8000  = FE langsung hit Python FastAPI (Ollama mode)
VITE_API_BASE_URL="http://localhost:8000"

# ── Konfigurasi Ollama ───────────────────────────────────────
# OLLAMA_BASE_URL: Base URL tempat server Ollama berjalan.
# Lokal (default) : http://localhost:11434
# Remote / luar   : http://192.168.1.100:11434  atau  https://ollama.alfilab.my.id
OLLAMA_BASE_URL="http://localhost:11434"

# OLLAMA_MODEL: Nama model Ollama yang akan digunakan.
OLLAMA_MODEL="llama3"

# OLLAMA_TIMEOUT: Batas waktu tunggu response dari Ollama (dalam detik).
# LLM lokal bisa lambat, terutama saat pertama kali load model.
OLLAMA_TIMEOUT="180"
```

---

## 2. Menjalankan Backend Python (FastAPI)

Backend FastAPI bertugas untuk memproses curhatan dan menghubungkannya dengan model Ollama lokal.

### Install dependensi Python

```bash
pip3 install fastapi uvicorn requests pydantic python-dotenv
```

### Jalankan server FastAPI

```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Cek status backend:
```bash
curl http://localhost:8000/api/health
# {"status":"ok","engine":"FastAPI & Ollama Local"}
```

---

## 3. Menjalankan Frontend (React)

```bash
# Install dependensi (hanya perlu sekali)
npm install

# Jalankan Vite dev server
npm run dev
```

Aplikasi frontend berjalan di → **http://localhost:5173**

---

## 4. Menjalankan FE & BE Bersamaan (Rekomendasi)

Buka **2 terminal terpisah**:

```bash
# Terminal 1 — Backend Python
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend React
npm run dev
```

---

## Alur Request

```
React Frontend (port 5173)
       ↓ (POST /api/analyze)
FastAPI Backend (port 8000)
       ↓ (POST /api/generate)
Ollama (lokal / remote server)
```

---

## Mode Production

Jika ingin dideploy atau dijalankan tanpa development server Node.js:

1. Build frontend terlebih dahulu:
   ```bash
   npm run build
   ```
   Ini akan menghasilkan folder `dist/`.

2. Jalankan start command:
   ```bash
   npm start
   ```
   FastAPI otomatis akan serve berkas frontend dari folder `dist/` di port `8000`. Cukup buka `http://localhost:8000` di browser.

---

## Struktur Folder Project

```
mindstep-ai/
├── src/              # Kode React (Frontend)
├── server.py         # Backend Python (FastAPI + Ollama)
├── .env              # Konfigurasi lokal
├── .env.example      # Template konfigurasi
├── package.json      # Dependensi dan script Node.js
└── vite.config.ts    # Konfigurasi Vite
```
