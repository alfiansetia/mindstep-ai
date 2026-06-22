<div align="center">
  <img width="1200" height="475" alt="MindStep AI Banner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
  
  # 🍃 MindStep AI: Your Mental Productivity Bestie
  
  > **Ubah stres dan overwhelming menjadi langkah kecil yang konkret.**  
  > Asisten produktivitas mikro berbasis LLM (Local/Cloud) dengan pendekatan psikologi Gen-Z.
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-sage.svg)](https://opensource.org/licenses/MIT)
  [![FastAPI](https://img.shields.io/badge/Backend-FastAPI-4A5D4D.svg)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/Frontend-React%2019-8DAA91.svg)](https://react.dev/)
  [![Tailwind](https://img.shields.io/badge/Styling-Tailwind%20v4-38B2AC.svg)](https://tailwindcss.com/)
</div>

---

## 🌟 Mengapa MindStep AI?

Sering dapet _Analysis Paralysis_ karena tugas numpuk? MindStep AI hadir buat nangkep semua "sampah pikiran" lo (_Brain-dump_) dan ngeracik **3 langkah mikro** yang durasinya di bawah 15 menit. Gak ada lagi alasan buat nggak mulai.

---

## ✨ Fitur "Plus" Terbaru

### 1. 🧠 Hybrid AI Intelligence (Multi-Engine)

Mendukung berbagai provider AI secara dinamis. Pindah dari **Ollama (Lokal & Gratis)** ke **Gemini Pro** atau **GPT-4** cuma dengan ganti satu baris di `.env`.

### 2. 🗄️ Database Chat Persistence (SQLite)

Riwayat curhatan lo sekarang **nggak bakal ilang** walau reload browser atau pindah device. Semua tersimpan aman di database backend.

### 3. 📱 Mobile-First Native Experience

User Interface yang dioptimalkan untuk HP dengan **Bottom Navigation Bar**, _smooth transitions_, dan layout yang jempol-friendly.

### 4. 🌙 Deep Forest Dark Mode

Mode gelap spesial dengan palet warna hijau hutan yang menenangkan, cocok buat nemenin lo curhat pas malem-malem sebelum tidur.

### 5. 🧘 Zen Focus Mode

Fitur timer imersif yang nutupin semua gangguan di layar. Bikin lo bener-bener fokus nyelesain satu langkah kecil sampe tuntas.

### 6. 🪴 Mental Garden (Gamification)

Taman virtual yang tumbuh seiring lo nyelesain tugas. Makin rajin lo gerak, makin besar pohon mental lo berevolusi!

---

## 🛠️ Konfigurasi & Setup

### 1. Setup Environment

Salin `.env.example` ke `.env` dan sesuaikan provider lo:

```env
# Opsi: ollama, openai, openrouter, groq, gemini
LLM_PROVIDER="ollama"

# Jika pake Ollama
OLLAMA_MODEL="llama3"
OLLAMA_BASE_URL="http://localhost:11434"

# Jika pake Cloud (GPT/Gemini)
AI_API_KEY="your-api-key"
```

### 2. Cara Menjalankan

Pastikan lo punya Python 3.9+ dan Node.js terbaru.

**Langkah 1: Jalankan Backend (FastAPI)**

```bash
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Langkah 2: Jalankan Frontend (Vite)**

```bash
npm install
npm run dev
```

---

## 📂 Struktur Modular

Proyek ini didesain biar gampang di-upgrade:

- `server.py`: Otak backend (FastAPI, SQLite, API Endpoints).
- `engines/`: Folder modular buat nambahin provider AI baru.
- `prompts.py`: Pusat kendali instruksi "Persona Bestie" AI.
- `src/App.tsx`: UI utama yang responsif & interaktif.

---

<div align="center">
  <p>Built with ❤️ by Antigravity for the Gen-Z Productivity Revolution.</p>
  <p><i>"Small steps are still progress."</i> 🍃</p>
</div>
