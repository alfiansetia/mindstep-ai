import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

// AI_BACKEND: 'gemini' (default) atau 'ollama' (pakai Python FastAPI lokal)
const AI_BACKEND = (process.env.AI_BACKEND || "gemini").toLowerCase();
const OLLAMA_BACKEND_URL = process.env.OLLAMA_BACKEND_URL || "http://localhost:8000";

console.log(`🤖 AI Backend mode: ${AI_BACKEND.toUpperCase()}`);
if (AI_BACKEND === "ollama") {
  console.log(`   Proxying ke Python FastAPI → ${OLLAMA_BACKEND_URL}`);
}

// Initialize Google Gen AI (hanya dipakai jika AI_BACKEND=gemini)
const apiKey = process.env.GEMINI_API_KEY;
if (AI_BACKEND === "gemini" && !apiKey) {
  console.warn("⚠️  Warning: GEMINI_API_KEY tidak diset. Set AI_BACKEND=ollama di .env untuk pakai model lokal.");
}

const ai = new GoogleGenAI({
  apiKey: apiKey || "",
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    }
  }
});

app.use(express.json());

// API route for health check
app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

// API route for MindStep AI brain-dump analysis
app.post("/api/gemini/analyze", async (req, res) => {
  const { curhatan, contextHistory, userPersona } = req.body;

  if (!curhatan) {
    return res.status(400).json({ error: "Curhatan content is required" });
  }

  const persona = userPersona || "genz";
  let prompt = "";
  let systemInstruction = "";
  let schemaDescription = "";

  if (persona === "professional") {
    prompt = `
Context History Pembicaraan/RAG:
${contextHistory || "Tidak ada riwayat sebelumnya."}

Teks Curhatan Baru Pengguna:
"${curhatan}"

Harap analisis curhatan tersebut dan berikan respons sebagai MindStep AI sesuai dengan petunjuk berikut:
1. Nada Bicara (Tone): Sangat empatik, dewasa, profesional, tenang, santun, tulus, dan penuh dukungan yang logis tanpa menggurui.
2. Gaya Bahasa: Gunakan Bahasa Indonesia yang baik, benar, terstruktur, sopan, dan formal/baku. Hindari penggunaan singkatan gaul, bahasa Jaksel, serta campuran bahasa Inggris yang berlebihan (kecuali istilah teknis yang lumrah).
3. Pendekatan Tindakan: Pecah tugas besar menjadi maksimal 3 langkah mikro produktivitas yang sangat konkret dan taktis. Langkah pertama HARUS berupa aksi super ringan yang membutuhkan waktu KURANG dari 5 menit (misalnya: "Membuka dokumen kerja utama", "Menulis satu poin pertama di agenda", "Meletakkan berkas penting di atas meja").
4. Pembatasan: JANGAN memberikan saran medis atau diagnosis psikologis formal. Fokus pada dekomposisi kognitif menjadi aksi produktif agar bebas dari rasa bimbang dan penundaan kerja (procrastination).
5. BATASAN RUANG LINGKUP (CRITICAL GUARDRAIL): Anda HANYA boleh membantu dalam lingkup produktivitas mikro, manajemen stres kerja/studi/kehidupan, dan kesehatan mental (wellbeing). Jika pengguna menanyakan hal-hal di luar lingkup ini (seperti rekomendasi makanan/kuliner, tempat wisata, pertanyaan matematika, coding, atau review produk umum), Anda HARUS MENOLAK secara sopan dalam empathy_response menggunakan Bahasa Indonesia yang formal dan sopan (sambil menjelaskan fokus Anda adalah asisten kesehatan mental & produktivitas). Setelah menolak bagian di luar konteks tersebut, fokuslah kembali ke bagian curhatan yang sesuai konteks jika ada (seperti cemas mengelola keuangan). Jangan pernah memberikan rekomendasi makanan atau jawaban di luar lingkup sama sekali!
`;

    systemInstruction = `Kamu adalah MindStep AI, asisten produktivitas mikro dan pendukung kesehatan mental (wellbeing) profesional untuk pekerja, akademisi, atau individu dewasa di Indonesia. Tugas utamanya adalah membantu mengurai beban pikiran dan kecemasan terkait produktivitas sehari-hari secara elegan, tenang, sopan, dan terstruktur dengan menggunakan Bahasa Indonesia yang baik, benar, dan penuh empati. Kamu memiliki batasan ruang lingkup yang sangat ketat: kamu HANYA boleh merespons masalah produktivitas, manajemen stres, dan mental wellbeing. Jangan pernah melayani atau memberikan jawaban terhadap pertanyaan umum di luar lingkup ini (misalnya rekomendasi kuliner/makanan, rute jalan, matematika, kode). Jika ada pertanyaan luar sekecil apa pun, tolaklah secara sopan menggunakan bahasa formal bernada santun di 'empathy_response', baru kemudian bantu urai masalah kecemasan produktivitas mereka.`;
    schemaDescription = "Kalimat respons empati yang profesional, sopan, dan dewasa yang memvalidasi perasaan cemas atau tertekan yang dialami pengguna.";
  } else {
    // Default or 'genz'
    prompt = `
Context History Pembicaraan/RAG:
${contextHistory || "Tidak ada riwayat sebelumnya."}

Teks Curhatan Baru Pengguna:
"${curhatan}"

Harap analisis curhatan tersebut dan berikan respons sebagai MindStep AI sesuai dengan petunjuk berikut:
1. Nada Bicara (Tone): Sangat empatik, suportif, menonjolkan validasi emosi terlebih dahulu, bersahabat, dan tidak menggurui (not lecturing).
2. Gaya Bahasa: Gunakan bahasa kasual ala Gen Z perkotaan di Indonesia (Jaksel style) dengan kata-kata campur bahasa Inggris populer yang natural (misal: "overwhelmed", "burnout", "hectic", "it's okay", "take your time", "slow down", "deep breath", "let's do this step by step").
3. Pendekatan Tindakan: Pecah tugas besar menjadi maksimal 3 langkah mikro produktivitas yang super konkret. Langkah pertama HARUS berupa aksi super ringan yang membutuhkan waktu KURANG dari 5 menit (misalnya: "Buka laptop aja dulu", "Tulis 1 kalimat pertama", "Taruh buku di atas meja").
4. Pembatasan: JANGAN memberikan saran medis atau diagnosis psikologis formal. Fokus pada dekomposisi kognitif menjadi aksi produktif agar bebas dari analysis paralysis.
5. BATASAN RUANG LINGKUP (CRITICAL GUARDRAIL): Anda HANYA boleh membantu dalam lingkup produktivitas mikro, manajemen stres kerja/studi/kehidupan, dan kesehatan mental (wellbeing). Jika pengguna menanyakan hal-hal di luar lingkup ini (seperti rekomendasi makanan/kuliner, tempat wisata, pertanyaan matematika, coding, atau review produk umum), Anda HARUS MENOLAK secara sopan dalam empathy_response menggunakan gaya bahasa santai/Gen Z (misal dengan menyatakan bahwa Anda adalah asisten kesehatan mental & produktivitas yang tidak bisa merekomendasikan makanan atau topik luar tersebut). Setelah menolak bagian di luar konteks tersebut, fokuslah kembali ke bagian curhatan yang sesuai konteks (seperti cemas mengelola keuangan pada contoh di atas). Jangan pernah memberikan rekomendasi makanan atau hal luar lainnya!
`;

    systemInstruction = `Kamu adalah MindStep AI, asisten produktivitas mikro dan pendukung kesehatan mental (wellbeing) khusus untuk Gen Z (mahasiswa, fresh graduates, first-jobbers) di Indonesia. Tugas utamanya adalah membantu mengurai stres dan kecemasan terkait produktivitas. Kamu memiliki batasan ruang lingkup yang sangat ketat: kamu HANYA boleh merespons masalah produktivitas, manajemen stres, dan mental wellbeing. Jangan pernah melayani atau memberikan jawaban terhadap pertanyaan umum di luar lingkup ini, seperti rekomendasi kuliner/makanan, rute perjalanan, atau penyelesaian kode/matematika. Jika pengguna menanyakan hal di luar lingkup (baik dicampur dengan stres maupun murni di luar lingkup), kamu harus secara sopan menolak menjawab hal luar tersebut di dalam 'empathy_response' dengan nada kasual anak muda, lalu fokuskan sisa responsmu untuk mendampingi perasaan cemas mereka (misal kecemasan finansialnya).`;
    schemaDescription = "Kalimat respons empati kasual ala Gen Z yang memvalidasi perasaan cemas atau overwhelmed pengguna.";
  }

  // ── MODE: OLLAMA — proxy ke Python FastAPI ──────────────────────────────
  if (AI_BACKEND === "ollama") {
    try {
      const fetch = (await import("node-fetch")).default;
      const ollamaRes = await fetch(`${OLLAMA_BACKEND_URL}/api/gemini/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ curhatan, contextHistory, userPersona }),
      });

      if (!ollamaRes.ok) {
        const errText = await ollamaRes.text();
        throw new Error(`Python FastAPI error ${ollamaRes.status}: ${errText}`);
      }

      const data = await ollamaRes.json();
      return res.json(data);
    } catch (error: any) {
      console.error("Ollama proxy error:", error);
      return res.status(503).json({
        error: "Gagal terhubung ke backend Ollama. Pastikan Python FastAPI (port 8000) menyala!",
        details: error.message
      });
    }
  }

  // ── MODE: GEMINI ─────────────────────────────────────────────────────────
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            empathy_response: {
              type: Type.STRING,
              description: schemaDescription
            },
            detected_emotion: {
              type: Type.STRING,
              description: "Label emosi utama yang terdeteksi dari teks (misal: Anxious, Burnout, Confused, Demotivated, Overwhelmed)."
            },
            energy_level_required: {
              type: Type.STRING,
              description: "Tingkat energi yang dibutuhkan pengguna untuk mengambil tindakan saat ini berdasarkan kondisi emosinya (Low, Medium, High)."
            },
            micro_steps: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  step_id: {
                    type: Type.INTEGER
                  },
                  title: {
                    type: Type.STRING,
                    description: "Judul langkah mikro yang konkret, singkat, dan sangat mudah dimulai."
                  },
                  description: {
                    type: Type.STRING,
                    description: "Penjelasan detail atau tips mikro berdurasi pendek untuk menyelesaikan langkah tersebut tanpa stres."
                  },
                  duration_minutes: {
                    type: Type.INTEGER,
                    description: "Estimasi durasi waktu dalam menit untuk menyelesaikan langkah mikro ini (disarankan di bawah 15 menit)."
                  }
                },
                required: ["step_id", "title", "description", "duration_minutes"]
              },
              description: "Daftar maksimal 3 langkah mikro produktivitas."
            }
          },
          required: ["empathy_response", "detected_emotion", "energy_level_required", "micro_steps"]
        }
      }
    });

    const resultText = response.text;
    if (!resultText) {
      throw new Error("Empty response from Gemini API");
    }

    // Try parsing to verify it is valid JSON
    const parsedData = JSON.parse(resultText.trim());
    res.json(parsedData);

  } catch (error: any) {
    console.error("Gemini analysis error:", error);
    res.status(500).json({
      error: "Gagal memproses curhatan kamu. Let's try again in a bit!",
      details: error.message
    });
  }
});

// Setup Vite Dev server or Serve build assets
async function initialize() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT} in ${process.env.NODE_ENV || 'development'} mode`);
  });
}

initialize().catch((err) => {
  console.error("Failed to start server:", err);
});
