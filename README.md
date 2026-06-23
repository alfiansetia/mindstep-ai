<div align="center">
  <img width="1200" height="475" alt="MindStep AI Banner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
  
  # 🍃 MindStep AI: Your Mental Productivity Bestie
  
  # "Ubah stres dan overwhelming menjadi langkah kecil yang konkret. Asisten produktivitas mikro berbasis LLM (Local/Cloud) dengan pendekatan psikologi Gen-Z."
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-sage.svg)](https://opensource.org/licenses/MIT)
  [![FastAPI](https://img.shields.io/badge/Backend-FastAPI-4A5D4D.svg)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/Frontend-React%2019-8DAA91.svg)](https://react.dev/)
  [![Tailwind](https://img.shields.io/badge/Styling-Tailwind%20v4-38B2AC.svg)](https://tailwindcss.com/)
  [![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://sqlite.org/)
</div>

---

## 🌟 Mengapa MindStep AI?

Sering dapet _Analysis Paralysis_ karena tugas numpuk? MindStep AI hadir buat nangkep semua "sampah pikiran" lo (_Brain-dump_) dan ngeracik **3 langkah mikro** yang durasinya di bawah 15 menit. Gak ada lagi alasan buat nggak mulai.

---

## ✨ Fitur "Plus" Terbaru

### 1. 🧠 Hybrid AI Intelligence (Multi-Engine)

Mendukung berbagai provider AI secara dinamis (Ollama, OpenAI, Gemini). Pindah engine cuma lewat `.env`.

### 2. 👥 Anonymous Multi-User Isolation

Setiap browser/perangkat punya **User ID unik** sendiri. Riwayat curhat dan progress tanaman lo terisolasi aman dan nggak bakal kecampur sama user lain di server yang sama.

### 3. 🗄️ Database Chat Persistence (SQLite)

Semua riwayat curhatan tersimpan di backend. Reload browser atau ganti hari, progress lo tetep ada.

### 4. 📱 Mobile-First Native Experience

UI yang jempol-friendly dengan **Bottom Navigation Bar** dan transisi halus ala aplikasi native.

### 5. 🌙 Deep Forest Dark Mode & Zen Mode

Tema gelap yang adem dan fitur timer imersif buat bantu lo fokus nyelesain tugas mikro tanpa gangguan.

---

## 📊 Arsitektur Database (SQLite)

Aplikasi ini menggunakan SQLite (`cache.db`) dengan skema yang dirancang untuk kecepatan dan persistensi data per-user.

### 1. Tabel `sessions` (Riwayat Analisis)

Menyimpan data lengkap setiap sesi curhat dan micro-steps.
| Kolom | Tipe | Deskripsi |
| :--- | :--- | :--- |
| `id` | TEXT (PK) | ID unik sesi curhat. |
| `user_id` | TEXT | ID Unik pengguna (anonymous isolation). |
| `original_curhatan`| TEXT | Teks curhatan asli dari user. |
| `empathy_response` | TEXT | Jawaban empati dari AI. |
| `micro_steps` | TEXT (JSON) | Daftar langkah kecil (tasks) dalam format JSON. |

### 2. Tabel `user_activity` (Mood Tracker)

Digunakan untuk data statistik dan grafik pertumbuhan emosi.
| Kolom | Tipe | Deskripsi |
| :--- | :--- | :--- |
| `emotion` | TEXT | Jenis emosi yang dideteksi (Frustrated, Happy, etc). |
| `energy_level` | TEXT | Level energi yang dibutuhkan untuk tugas. |
| `user_id` | TEXT | ID Unik pengguna. |
| `created_at` | DATE | Tanggal aktivitas. |

### 3. Tabel `plant_stats` (Gamification)

Menyimpan status tanaman virtual untuk setiap user.
| Kolom | Tipe | Deskripsi |
| :--- | :--- | :--- |
| `user_id` | TEXT (Unique)| Pemilik tanaman. |
| `level` | INTEGER | Level evolusi tanaman (1-10+). |
| `xp` | INTEGER | Experience points saat ini (0-99). |

---

## 🛠️ Konfigurasi & Setup

1. **Setup Environment**: Salin `.env.example` ke `.env` dan masukkan API Key lo.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   npm install
   ```
3. **Jalankan Aplikasi**:
   - **Backend**: `python -m uvicorn server:app --reload`
   - **Frontend**: `npm run dev`

---

<div align="center">
  <p>Built with ❤️ by Antigravity for the Gen-Z Productivity Revolution.</p>
  <p><i>"Small steps are still progress."</i> 🍃</p>
</div>
