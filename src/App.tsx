import React, { useState, useEffect, useRef } from "react";

// Base URL API — dikonfigurasi via .env (VITE_API_BASE_URL)
// Kosong = relative ke server saat ini (server.ts port 3000)
// Diisi  = langsung hit Python FastAPI, misal: http://localhost:8000
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
import { 
  Brain, 
  Sparkles, 
  Mic, 
  MicOff, 
  Play, 
  Pause, 
  RotateCcw, 
  Volume2, 
  Flame, 
  Clock, 
  CheckCircle2, 
  History, 
  Trash2, 
  Loader2, 
  ChevronRight, 
  Heart, 
  Calendar,
  Layers,
  Sparkle
} from "lucide-react";
import { type MicroStep, type AnalysisResponse, type HistorySession } from "./types";

export default function App() {
  // Application Data States
  const [userPersona, setUserPersona] = useState<"genz" | "professional">("genz");
  const [showPersonaModal, setShowPersonaModal] = useState<boolean>(false);

  const [curhatan, setCurhatan] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // Active response & session details
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisResponse | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({});
  
  // Speech Recognition (Web Speech API) States
  const [isListening, setIsListening] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);
  const [speechFeedback, setSpeechFeedback] = useState<string>("");

  // Sound/TTS (Speech Synthesis) States
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Gamified Timer States
  const [timerActive, setTimerActive] = useState<boolean>(false);
  const [timerSeconds, setTimerSeconds] = useState<number>(0);
  const [timerMax, setTimerMax] = useState<number>(0);
  const [timerStepId, setTimerStepId] = useState<number | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // History & Local Registry
  const [sessions, setSessions] = useState<HistorySession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Onboarding default demo triggers
  const demoCurhatan = "Aduh asli gue makin overthinking banget hari ini, mana besok udah harus bimbingan lagi tapi revisian yang kemarin belum gue sentuh sama sekali. Tiap mau buka file-nya bawaannya pengen nangis, overwhelmed parah, ga tahu harus mulai dari mana.";

  // Load Initial Session History & Preferences from localStorage
  useEffect(() => {
    const savedPersona = localStorage.getItem("mindstep_persona");
    if (savedPersona === "genz" || savedPersona === "professional") {
      setUserPersona(savedPersona);
    } else {
      setShowPersonaModal(true);
    }

    const saved = localStorage.getItem("mindstep_sessions");
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as HistorySession[];
        setSessions(parsed);
        if (parsed.length > 0) {
          // Preset the latest analysis in view
          const latest = parsed[0];
          setActiveSessionId(latest.id);
          setActiveAnalysis({
            empathy_response: latest.empathy_response,
            detected_emotion: latest.detected_emotion,
            energy_level_required: latest.energy_level_required,
            micro_steps: latest.micro_steps
          });
          // Restore completion state
          const completions: Record<number, boolean> = {};
          latest.micro_steps.forEach(step => {
            completions[step.step_id] = step.completed || false;
          });
          setCompletedSteps(completions);
        }
      } catch (e) {
        console.error("Error restoring history", e);
      }
    }
    
    // Check Speech Recognition capability
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "id-ID";

      rec.onstart = () => {
        setIsListening(true);
        setSpeechFeedback("Listening... Silakan curhat secara langsung.");
      };

      rec.onresult = (event: any) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        if (finalTranscript) {
          setCurhatan((prev) => {
            const trimmed = prev.trim();
            return trimmed ? `${trimmed} ${finalTranscript}` : finalTranscript;
          });
        }
        setSpeechFeedback(interimTranscript || "Mendengarkan suara kamu...");
      };

      rec.onerror = (err: any) => {
        console.error("Speech Recognition Error", err);
        setSpeechFeedback(`Gagal mendengar: ${err.error || "Mungkin microphone diblokir"}`);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
        setSpeechFeedback("");
      };

      recognitionRef.current = rec;
    }
  }, []);

  // Save Sessions helper
  const saveSessionsToLocal = (updatedSessions: HistorySession[]) => {
    setSessions(updatedSessions);
    localStorage.setItem("mindstep_sessions", JSON.stringify(updatedSessions));
  };

  // Trigger Brain-dump Analysis via Server-Side API
  const handleAnalyze = async (textToAnalyze: string = curhatan) => {
    if (!textToAnalyze.trim()) return;
    setIsLoading(true);
    stopTTS();
    stopTimer();

    // Buat riwayat konteks secara otomatis dari 3 sesi terakhir agar AI mengingat percakapan sebelumnya
    const computedContextHistory = sessions
      .slice(0, 3)
      .map(s => `User: "${s.original_curhatan}"\nAI: "${s.empathy_response}"`)
      .reverse()
      .join("\n\n");

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          curhatan: textToAnalyze,
          contextHistory: computedContextHistory,
          userPersona: userPersona
        })
      });

      if (!response.ok) {
        throw new Error("Failed to communicate with API");
      }

      const data: AnalysisResponse = await response.json();
      setActiveAnalysis(data);

      // Check default checkmarks
      const stepCompletions: Record<number, boolean> = {};
      data.micro_steps.forEach(step => {
        stepCompletions[step.step_id] = false;
      });
      setCompletedSteps(stepCompletions);

      // Save into history
      const newSession: HistorySession = {
        id: "sess_" + Date.now(),
        timestamp: new Date().toISOString(),
        original_curhatan: textToAnalyze,
        contextHistory: computedContextHistory,
        empathy_response: data.empathy_response,
        detected_emotion: data.detected_emotion,
        energy_level_required: data.energy_level_required,
        micro_steps: data.micro_steps
      };

      const updated = [newSession, ...sessions];
      saveSessionsToLocal(updated);
      setActiveSessionId(newSession.id);

    } catch (error: any) {
      console.error(error);
      alert("Gagal memproses curhatan kamu. Silakan coba lagi sebentar!");
    } finally {
      setIsLoading(false);
    }
  };

  // Custom demo preset loader
  const loadDemoPreset = () => {
    setCurhatan(demoCurhatan);
  };

  // Clear current editor state
  const clearEditor = () => {
    setCurhatan("");
  };

  // Toggle Micro Step Completion Tracker
  const toggleStepCompleted = (stepId: number) => {
    const updatedCompletions = {
      ...completedSteps,
      [stepId]: !completedSteps[stepId]
    };
    setCompletedSteps(updatedCompletions);

    // Update session record in stored history
    if (activeSessionId) {
      const updatedSessions = sessions.map(sess => {
        if (sess.id === activeSessionId) {
          return {
            ...sess,
            micro_steps: sess.micro_steps.map(step => {
              if (step.step_id === stepId) {
                return { ...step, completed: updatedCompletions[stepId] };
              }
              return step;
            })
          };
        }
        return sess;
      });
      saveSessionsToLocal(updatedSessions);
    }
  };

  // Text-To-Speech (Empathy Voice) Implementation
  const handleSpeak = (text: string) => {
    if (isSpeaking) {
      stopTTS();
      return;
    }

    if ("speechSynthesis" in window) {
      // cancel ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "id-ID";
      
      // Try to find a warm female/male Indonesian or generic soft voice
      const voices = window.speechSynthesis.getVoices();
      const idVoice = voices.find(v => v.lang.includes("id-ID") || v.lang.includes("id"));
      if (idVoice) {
        utterance.voice = idVoice;
      }
      utterance.rate = 0.95; // Slightly slower, more soothing
      utterance.pitch = 1.0;

      utterance.onend = () => {
        setIsSpeaking(false);
      };
      utterance.onerror = () => {
        setIsSpeaking(false);
      };

      utteranceRef.current = utterance;
      setIsSpeaking(true);
      window.speechSynthesis.speak(utterance);
    } else {
      alert("Format TTS tidak didukung browser kamu.");
    }
  };

  const stopTTS = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  };

  // Web Speech API Voice Dictation toggle
  const toggleVoiceDictation = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition tidak didukung di browser ini. Direkomendasikan menggunakan Google Chrome.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  // Focus Timer Actions
  const startTimer = (stepId: number, durationMinutes: number) => {
    stopTimer();
    setTimerStepId(stepId);
    setTimerMax(durationMinutes * 60);
    setTimerSeconds(durationMinutes * 60);
    setTimerActive(true);

    timerIntervalRef.current = setInterval(() => {
      setTimerSeconds((prev) => {
        if (prev <= 1) {
          stopTimer();
          // Auto complete step on timer completion
          toggleStepCompleted(stepId);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const stopTimer = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setTimerActive(false);
  };

  const resetTimer = () => {
    if (timerStepId !== null && timerMax > 0) {
      setTimerSeconds(timerMax);
    }
  };

  // Format countdown text e.g. "04:59"
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Handle Loading previous sessions from sidebar list
  const loadPreviousSession = (session: HistorySession) => {
    setActiveSessionId(session.id);
    setCurhatan(session.original_curhatan);
    setActiveAnalysis({
      empathy_response: session.empathy_response,
      detected_emotion: session.detected_emotion,
      energy_level_required: session.energy_level_required,
      micro_steps: session.micro_steps
    });

    const completions: Record<number, boolean> = {};
    session.micro_steps.forEach(step => {
      completions[step.step_id] = step.completed || false;
    });
    setCompletedSteps(completions);
    stopTTS();
    stopTimer();
  };

  // Delete a specific session from registry
  const deleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const updated = sessions.filter(sess => sess.id !== id);
    saveSessionsToLocal(updated);
    if (activeSessionId === idTitleOf(id)) {
      if (updated.length > 0) {
        loadPreviousSession(updated[0]);
      } else {
        setActiveSessionId(null);
        setActiveAnalysis(null);
      }
    }
  };

  const idTitleOf = (id: string) => id;

  // Render Emotion Coloration Theme
  const getEmotionStyling = (emotion: string) => {
    const em = emotion.toLowerCase();
    if (em.includes("anxious") || em.includes("cemas")) {
      return {
        bg: "bg-white border-[#E5E0D5] text-[#3A3A3A]",
        pill: "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]",
        glow: "shadow-soft",
        title: "text-[#4A5D4D]"
      };
    }
    if (em.includes("burnout") || em.includes("lelah")) {
      return {
        bg: "bg-white border-[#E5E0D5] text-[#3A3A3A]",
        pill: "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]",
        glow: "shadow-soft",
        title: "text-[#4A5D4D]"
      };
    }
    if (em.includes("overwhelmed") || em.includes("stres")) {
      return {
        bg: "bg-white border-[#E5E0D5] text-[#3A3A3A]",
        pill: "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]",
        glow: "shadow-soft",
        title: "text-[#4A5D4D]"
      };
    }
    if (em.includes("confused") || em.includes("bingung")) {
      return {
        bg: "bg-white border-[#E5E0D5] text-[#3A3A3A]",
        pill: "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]",
        glow: "shadow-soft",
        title: "text-[#4A5D4D]"
      };
    }
    return {
      bg: "bg-white border-[#E5E0D5] text-[#3A3A3A]",
      pill: "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]",
      glow: "shadow-soft",
      title: "text-[#4A5D4D]"
    };
  };

  const getEnergyBadge = (lvl: string) => {
    const l = lvl.toLowerCase();
    if (l.includes("low")) {
      return "bg-[#8DAA91] text-white border border-[#8DAA91]";
    }
    if (l.includes("medium")) {
      return "bg-[#D9AE94] text-white border border-[#D9AE94]";
    }
    return "bg-[#4A5D4D] text-white border border-[#4A5D4D]";
  };

  // Statistics calculation for user session logs
  const totalTasksSaved = sessions.length * 3;
  const completedTaskCount = sessions.reduce((acc, sess) => {
    return acc + sess.micro_steps.filter(s => s.completed).length;
  }, 0);

  const activeEmotionStyling = activeAnalysis 
    ? getEmotionStyling(activeAnalysis.detected_emotion) 
    : getEmotionStyling("default");

  return (
    <div className="min-h-screen bg-[#F9F7F2] text-[#3A3A3A] flex flex-col antialiased selection:bg-[#8DAA91]/20 selection:text-[#4A5D4D]">
      
      {/* HEADER BAR */}
      <header className="border-b border-[#E5E0D5] bg-[#F2EDE4]/80 backdrop-blur-md sticky top-0 z-40 transition-all duration-300 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-[#8DAA91] flex items-center justify-center shadow-sm">
              <Brain className="h-5 w-5 text-white" id="app-logo" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold font-display tracking-tight text-[#4A5D4D]">
                  MindStep <span className="text-[#8DAA91]">AI</span>
                </h1>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5]">
                  v1.2 GenZ-Wellbeing
                </span>
              </div>
              <p className="text-xs text-[#7A7469] font-sans">
                Asisten Produktivitas Mikro & Pelipur Stres Anak Muda
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-[#7A7469]">
            <div className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-[#E5E0D5]">
              <span className="h-2 w-2 rounded-full bg-[#8DAA91] animate-pulse"></span>
              <span>Mindfulness Offline Sync</span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-full border border-[#E5E0D5] text-[#3A3A3A]">
              <Calendar className="h-3.5 w-3.5 text-[#8DAA91]" />
              <span>{new Date().toLocaleDateString("id-ID", { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </div>
          </div>

        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: EDITOR & INPUT COGNITIVE BRAIN-DUMP (cols 5) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          {/* WELLBEING WELL-PREPARED INTRO / TIP */}
          <div className="bg-[#F2EDE4] border border-[#E5E0D5] p-5 rounded-[24px] relative overflow-hidden shadow-soft">
            <div className="absolute top-0 right-0 p-3 opacity-15 transform translate-x-2 -translate-y-2">
              <Sparkles className="h-12 w-12 text-[#8DAA91]" />
            </div>
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-white flex items-center justify-center text-[#8DAA91] flex-shrink-0">
                <Sparkle className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#4A5D4D] font-display uppercase tracking-wider">Anti Analysis Paralysis 🍃</h3>
                <p className="text-xs text-[#7A7469] mt-1.5 leading-relaxed">
                  Lagi hectic, overwhelmed, atau dead-end? Tulis atau ucapkan semua pikiran berantakan kamu di bawah. Kita dekap emosinya dan racik 3 langkah super enteng biar kamu bisa start tanpa drama!
                </p>
              </div>
            </div>
          </div>

          {/* INPUT FORM: THE BRAIN ZONE */}
          <div className="bg-white border border-[#E5E0D5] rounded-[32px] p-6 flex flex-col gap-4 relative shadow-soft">
            
            {/* Persona Selector (Adapt AI talking style & context) */}
            <div className="flex flex-col gap-1.5 border border-[#E5E0D5] rounded-2xl bg-[#F9F7F2]/50 p-3.5">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-[#4A5D4D] font-display uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-[#8DAA91]" />
                  Gaya Bicara & Respon AI :
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full font-bold bg-[#F2EDE4] text-[#8DAA91]">
                  {userPersona === "genz" ? "Gen Z Mode" : "Profesional"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setUserPersona("genz");
                    localStorage.setItem("mindstep_persona", "genz");
                  }}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition-all text-center border ${
                    userPersona === "genz"
                      ? "bg-[#8DAA91] text-white border-[#8DAA91] shadow-sm"
                      : "bg-white text-[#7A7469] border-[#E5E0D5] hover:bg-[#F2EDE4]/30"
                  }`}
                >
                  <span className="font-bold">Generasi Z</span>
                  <span className="text-[9px] opacity-80 font-normal">Jaksel, Kasual, Empatik</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUserPersona("professional");
                    localStorage.setItem("mindstep_persona", "professional");
                  }}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition-all text-center border ${
                    userPersona === "professional"
                      ? "bg-[#4A5D4D] text-white border-[#4A5D4D] shadow-sm"
                      : "bg-white text-[#7A7469] border-[#E5E0D5] hover:bg-[#F2EDE4]/30"
                  }`}
                >
                  <span className="font-bold font-sans">Profesional</span>
                  <span className="text-[9px] opacity-80 font-normal">Sopan, Baku, Dewasa</span>
                </button>
              </div>
            </div>

            {/* Curhatan Section */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-[#4A5D4D] font-display uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="h-4 w-4 text-[#8DAA91]" />
                  Active Brain-Dump
                </span>
                
                {/* Clear and template triggers */}
                <div className="flex gap-2">
                  <button 
                    onClick={loadDemoPreset}
                    className="text-[10px] font-mono text-[#8DAA91] hover:text-[#4A5D4D] transition-colors bg-[#F2EDE4] border border-[#E5E0D5] px-2.5 py-1 rounded-full text-xs font-semibold"
                    title="Load specific Chapter 2 Overthinking prompt"
                  >
                    🚀 Pakai Curhatan Demo
                  </button>
                  {curhatan && (
                    <button 
                      onClick={clearEditor}
                      className="text-[10px] text-[#8B8374] hover:text-[#3A3A3A] transition-colors flex items-center gap-0.5"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* Speech-to-Text Recognition Banner if listening */}
              {isListening && (
                <div className="bg-[#F2EDE4] border border-[#E5E0D5] p-2.5 rounded-xl flex items-center gap-3 animate-pulse">
                  <span className="h-2 w-2 rounded-full bg-[#8DAA91] animate-ping"></span>
                  <p className="text-xs text-[#7A7469] font-mono flex-grow truncate">
                    {speechFeedback}
                  </p>
                  <button 
                    onClick={() => recognitionRef.current?.stop()}
                    className="text-[10px] text-[#8B8374] hover:text-red-500 transition-colors"
                  >
                    Batal
                  </button>
                </div>
              )}

              <div className="relative">
                <textarea
                  value={curhatan}
                  onChange={(e) => setCurhatan(e.target.value)}
                  placeholder="Ketik curhatan atau hal yang bikin kamu stress berat di sini... Bebas tumpahin semua dalam keluh kesah acak."
                  className="w-full min-h-[160px] bg-[#F9F7F2]/50 border border-[#E5E0D5] rounded-2xl p-4 text-sm text-[#3A3A3A] placeholder-[#A09B90] focus:outline-none focus:ring-1 focus:ring-[#8DAA91]/50 focus:border-[#8DAA91]/50 resize-y leading-relaxed"
                />

                {/* Microphone dictate trigger */}
                <div className="absolute right-3.5 bottom-3.5 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={toggleVoiceDictation}
                    className={`h-9 w-9 rounded-full flex items-center justify-center transition-all ${
                      isListening
                        ? "bg-red-400 text-white animate-pulse shadow-md ring-4 ring-red-400/10"
                        : "bg-[#F2EDE4] text-[#4A5D4D] hover:bg-[#E5E0D5] hover:text-[#3A3A3A]"
                    }`}
                    title="Bicara lewat Microphone (Web Speech API)"
                  >
                    {isListening ? (
                      <MicOff className="h-4 w-4" />
                    ) : (
                      <Mic className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* ANALYZE TRIGGER CTA */}
            <button
              onClick={() => handleAnalyze()}
              disabled={isLoading || !curhatan.trim()}
              className={`w-full py-3.5 px-4 rounded-2xl font-display font-bold text-sm flex items-center justify-center gap-2 transition-all ${
                !curhatan.trim()
                  ? "bg-[#F2EDE4] text-[#8B8374] cursor-not-allowed border border-[#E5E0D5]"
                  : "bg-[#8DAA91] text-white hover:bg-[#7ba081] hover:shadow-lg hover:shadow-[#8DAA91]/15"
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Dekomposisi Pikiran Kamu Sedang Diproses...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Ubah Curhat Jadi Langkah Nyata</span>
                </>
              )}
            </button>
          </div>

          {/* WELLBEING METRICS DIARY (cols 5 bottom) */}
          <div className="bg-white border border-[#E5E0D5] rounded-[32px] p-6 flex flex-col gap-4 shadow-soft">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-[#4A5D4D] font-display uppercase tracking-wider flex items-center gap-2">
                <History className="h-4 w-4 text-[#8DAA91]" />
                Catatan Harian Emosi
              </h2>
              <span className="text-[10px] font-mono text-[#8B8374] bg-[#F2EDE4] px-2.5 py-0.5 rounded-full border border-[#E5E0D5]">
                Mental Fitness Log
              </span>
            </div>

            {/* Quick stats grid */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#F9F7F2] border border-[#E5E0D5] p-3 rounded-2xl text-center">
                <span className="text-xs text-[#7A7469] block font-sans">Curhat</span>
                <span className="text-lg font-bold font-display text-[#4A5D4D] mt-1 block">
                  {sessions.length}
                </span>
              </div>
              <div className="bg-[#F9F7F2] border border-[#E5E0D5] p-3 rounded-2xl text-center">
                <span className="text-xs text-[#7A7469] block font-sans">Mikro Aksi</span>
                <span className="text-lg font-bold font-display text-[#8DAA91] mt-1 block">
                  {completedTaskCount}/{totalTasksSaved}
                </span>
              </div>
              <div className="bg-[#F9F7F2] border border-[#E5E0D5] p-3 rounded-2xl text-center">
                <span className="text-xs text-[#7A7469] block font-sans">Streak Day</span>
                <span className="text-lg font-bold font-display text-[#D9AE94] mt-1 block flex items-center justify-center gap-0.5">
                  <Flame className="h-4 w-4 text-[#D9AE94] inline-block" /> {sessions.length > 0 ? "4" : "0"}
                </span>
              </div>
            </div>

            {/* Saved Sessions Log */}
            <div className="flex flex-col gap-2 max-h-[190px] overflow-y-auto pr-1">
              {sessions.length === 0 ? (
                <div className="text-center py-6 border border-dashed border-[#E5E0D5] rounded-xl">
                  <p className="text-xs text-[#7A7469]">Belum ada riwayat curhatan kamu.</p>
                  <p className="text-[11px] text-[#8B8374] mt-0.5">Gunakan curhatan demo di atas untuk memulai!</p>
                </div>
              ) : (
                sessions.map((sess) => {
                  const itemStyle = getEmotionStyling(sess.detected_emotion);
                  return (
                    <div
                      key={sess.id}
                      onClick={() => loadPreviousSession(sess)}
                      className={`flex items-center justify-between p-3 rounded-2xl border transition-all cursor-pointer ${
                        activeSessionId === sess.id
                          ? "bg-[#F2EDE4]/80 border-[#8DAA91] "
                          : "bg-[#F9F7F2]/40 border-[#E5E0D5] hover:border-[#8DAA91]/50 hover:bg-[#F2EDE4]/30"
                      }`}
                    >
                      <div className="flex-grow truncate pr-3">
                        <div className="flex items-center gap-2 mb-1 text-[11px]">
                          <span className={`px-1.5 py-0.5 rounded font-mono font-medium text-[9px] ${itemStyle.pill}`}>
                            {sess.detected_emotion}
                          </span>
                          <span className="text-[#8B8374] font-mono text-[9px]">
                            {new Date(sess.timestamp).toLocaleTimeString("id-ID", { hour: "numeric", minute: "2-digit" })}
                          </span>
                        </div>
                        <p className="text-xs text-[#3A3A3A] leading-relaxed truncate">
                          {sess.original_curhatan}
                        </p>
                      </div>

                      <button
                        onClick={(e) => deleteSession(e, sess.id)}
                        className="h-7 w-7 rounded-md hover:bg-[#E5E0D5]/60 text-[#8B8374] hover:text-[#4A5D4D] flex items-center justify-center transition-colors"
                        title="Hapus riwayat ini"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: MINDSTEP INIGHTS & DECONGESTED ACTIONS (cols 7) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          
          {/* TIMER COMPONENT WIDGET */}
          {timerSeconds > 0 && (
            <div className="bg-[#D9AE94] text-white border border-[#D9AE94]/50 rounded-[24px] p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md animate-fadeIn">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-white/20 text-white flex items-center justify-center">
                  <Clock className={`h-5 w-5 ${timerActive ? "animate-[spin_4s_linear_infinite]" : ""}`} />
                </div>
                <div>
                  <h4 className="text-xs text-white/90 font-mono font-bold uppercase tracking-wider">Focus & Flow Session Active</h4>
                  <p className="text-xs text-white/80 mt-0.5">
                    Untangle: {activeAnalysis?.micro_steps.find(s => s.step_id === timerStepId)?.title || "Langkah Mikro"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-2xl font-bold font-mono text-[#D9AE94] tracking-widest bg-white px-3 py-1 rounded-xl shadow-inner">
                  {formatTime(timerSeconds)}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setTimerActive(!timerActive)}
                    className="p-1.5 rounded-lg bg-white/20 text-white hover:bg-white/30 transition-colors"
                  >
                    {timerActive ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                  </button>
                  <button
                    onClick={resetTimer}
                    className="p-1.5 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={stopTimer}
                    className="p-1.5 rounded-lg bg-red-800/40 text-white hover:bg-red-800/60 transition-colors"
                  >
                    Stop
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ACTIVE RESPONSE VISUAL AREA */}
          {!activeAnalysis ? (
            <div className="bg-white border border-dashed border-[#E5E0D5] rounded-[40px] p-16 flex flex-col items-center justify-center text-center gap-4 flex-grow shadow-soft">
              <div className="h-16 w-16 rounded-full bg-[#F2EDE4] flex items-center justify-center border border-[#E5E0D5] text-[#8DAA91]">
                <Brain className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#4A5D4D] font-display uppercase tracking-wider">Belum Ada Analisis</h3>
                <p className="text-xs text-[#7A7469] mt-1.5 max-w-sm mx-auto leading-relaxed">
                  MindStep AI siap dengerin keluh kesah kamu. Pakai "Curhatan Demo" atau ketik langsung stres kamu di editor kiri, lalu klik analisis.
                </p>
              </div>
              <button
                onClick={loadDemoPreset}
                className="mt-2 py-2.5 px-5 rounded-full text-xs bg-[#8DAA91] text-white hover:bg-[#7ba081] transition-colors flex items-center gap-1 font-bold shadow-md"
              >
                <span>🚀 Ambil Presets Skripsi</span>
                <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-6 flex-grow font-sans">
              
              {/* EMPATHY INSIGHTS CARD */}
              <div className="bg-white rounded-[40px] p-8 md:p-10 shadow-soft border border-[#E5E0D5] flex flex-col gap-6 relative overflow-hidden">
                
                {/* Decorative natural flora motif background effect */}
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                  <Brain className="h-32 w-32 text-[#8DAA91]" />
                </div>

                <div className="flex flex-wrap gap-3 items-center">
                  <span className="px-3.5 py-1 bg-[#F2EDE4] rounded-full text-xs font-bold uppercase tracking-widest text-[#8B8374] border border-[#E5E0D5]/40">
                    Detected: {activeAnalysis.detected_emotion}
                  </span>
                  <span className={`px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-widest border ${
                    activeAnalysis.energy_level_required.toLowerCase().includes("low")
                      ? "bg-[#8DAA91]/10 text-[#4A5D4D] border-[#8DAA91]/30"
                      : "bg-[#D9AE94]/10 text-[#D9AE94] border-[#D9AE94]/30"
                  }`}>
                    Energy: {activeAnalysis.energy_level_required}
                  </span>
                </div>

                {/* EMPATHY RESPONSE SECTION WITH TTS */}
                <div className="mt-2 flex items-start justify-between gap-6">
                  <div className="flex-grow">
                    <h1 className="text-3xl md:text-[38px] leading-[1.15] font-serif italic text-[#4A5D4D] tracking-tight">
                      "{activeAnalysis.empathy_response}"
                    </h1>
                  </div>
                  
                  <button
                    onClick={() => handleSpeak(activeAnalysis.empathy_response)}
                    className={`h-11 w-11 rounded-full flex items-center justify-center flex-shrink-0 transition-all shadow-sm ${
                      isSpeaking
                        ? "bg-[#8DAA91] text-white animate-pulse"
                        : "bg-[#F2EDE4] text-[#4A5D4D] hover:bg-[#E5E0D5] hover:text-[#3A3A3A]"
                    }`}
                    title={isSpeaking ? "Hentikan Suara" : "Simak Respons dengan Audio (Empati-TTS)"}
                  >
                    <Volume2 className="h-5 w-5" />
                  </button>
                </div>

                <div className="h-[1px] w-full bg-[#E5E0D5] my-2"></div>

                <div className="flex items-center gap-4 text-xs text-[#7A7469]">
                  <div className="flex -space-x-1">
                    <div className="w-6 h-6 rounded-full border border-white bg-[#D9AE94]"></div>
                    <div className="w-6 h-6 rounded-full border border-white bg-[#8DAA91]"></div>
                  </div>
                  <p className="italic">Ratusan Generasi Z menceritakan kecemasan setara siang ini. Your feelings are completely valid.</p>
                </div>

              </div>

              {/* THREE MICRO ACTIONS ROADMAP */}
              <div className="bg-white border border-[#E5E0D5] rounded-[32px] p-6 flex flex-col gap-4 shadow-soft">
                <div className="flex items-center justify-between border-b border-[#E5E0D5] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#4A5D4D] font-display uppercase tracking-wider">
                      Productivity Micro-Steps
                    </h3>
                    <p className="text-xs text-[#7A7469] mt-0.5">
                      Selesaikan aksi super enteng ini biar nggak burnout demi progress-mu.
                    </p>
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#8DAA91] bg-[#F2EDE4] px-2.5 py-1 rounded-full border border-[#E5E0D5]">
                    Sangat Ringan
                  </span>
                </div>

                <div className="flex flex-col gap-4">
                  {activeAnalysis.micro_steps.map((step) => {
                    const isStepDone = completedSteps[step.step_id];
                    const isFirstStepAndNotDone = step.step_id === 1 && !isStepDone;
                    return (
                      <div
                        key={step.step_id}
                        className={`transition-all rounded-3xl p-5 border ${
                          isStepDone
                            ? "bg-[#F9F7F2]/60 border-[#E5E0D5] opacity-65"
                            : isFirstStepAndNotDone
                              ? "bg-[#F2EDE4] border-l-8 border-[#8DAA91] border-t border-r border-b border-[#E5E0D5] shadow-sm"
                              : "bg-white border-[#E5E0D5]"
                        }`}
                      >
                        <div className="flex items-start gap-4">
                          
                          {/* Gamified Checkbox */}
                          <button
                            type="button"
                            onClick={() => toggleStepCompleted(step.step_id)}
                            className={`h-8 w-8 rounded-full flex items-center justify-center transition-all flex-shrink-0 font-bold ${
                              isStepDone
                                ? "bg-[#8DAA91] text-white"
                                : isFirstStepAndNotDone
                                  ? "bg-white text-[#8DAA91] border border-[#8DAA91] shadow-sm hover:bg-[#8DAA91]/10"
                                  : "bg-[#F2EDE4] text-[#8B8374] border border-[#E5E0D5] hover:bg-[#E5E0D5]"
                            }`}
                          >
                            {isStepDone ? (
                              <CheckCircle2 className="h-4.5 w-4.5" />
                            ) : (
                              <span>{step.step_id}</span>
                            )}
                          </button>

                          <div className="flex-grow">
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                              <h4 className={`font-bold transition-all ${
                                isStepDone ? "text-[#7A7469] line-through font-medium" : "text-[#4A5D4D]"
                              }`}>
                                {step.title}
                              </h4>
                              
                              <div className="flex items-center gap-2">
                                <span className="text-[11px] font-mono text-[#7A7469] flex items-center gap-1 bg-[#F2EDE4] px-2 py-0.5 rounded-full border border-[#E5E0D5]/50">
                                  <Clock className="h-3 w-3 text-[#8DAA91]" />
                                  {step.duration_minutes} Menit
                                </span>

                                {!isStepDone && (
                                  <button
                                    onClick={() => startTimer(step.step_id, step.duration_minutes)}
                                    className="text-[10px] font-mono text-[#D9AE94] hover:text-[#cb9d81] bg-[#F2EDE4] px-2.5 py-0.5 rounded-full border border-[#E5E0D5] flex items-center gap-0.5 transition-all font-bold"
                                    title="Mulai Sesi Fokus Mikro sekarang"
                                  >
                                    Focus
                                  </button>
                                )}
                              </div>
                            </div>
                            
                            <p className="text-sm text-[#7A7469] mt-2 leading-relaxed">
                              {step.description}
                            </p>
                          </div>

                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="text-[11px] font-sans text-[#8B8374] flex items-center gap-1.5 justify-center mt-2 font-medium">
                  <span>✨ Tips: Mulai dari Langkah Pertama. Gak usah mikirin bab-bab selanjutnya dulu ya.</span>
                </div>

              </div>

            </div>
          )}

          {/* WELLBEING WELL-MOTIVATION ZONE */}
          <div className="mt-auto bg-[#D9AE94] rounded-[32px] p-6 text-white flex flex-col sm:flex-row gap-4 justify-between items-center shadow-soft">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest opacity-85">Kesehatan mental lu nomor satu ☕️</p>
              <p className="text-lg font-serif italic mt-0.5">Let's lower the pressure step by step.</p>
            </div>
            <button 
              onClick={() => {
                // If there's an active analysis, complete the first steps
                if (activeAnalysis) {
                  const firstNotCompleted = activeAnalysis.micro_steps.find(s => !completedSteps[s.step_id]);
                  if (firstNotCompleted) {
                    toggleStepCompleted(firstNotCompleted.step_id);
                  }
                } else {
                  loadDemoPreset();
                }
              }}
              className="bg-white text-[#D9AE94] hover:bg-[#F9F7F2] transition-colors px-6 py-2.5 rounded-full font-bold shadow-md text-xs shrink-0 cursor-pointer"
            >
              {activeAnalysis ? "I'm Doing It" : "Mulai Sekarang"}
            </button>
          </div>

        </div>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-[#E5E0D5] bg-[#F2EDE4]/30 py-6 text-center text-xs text-[#8B8374] mt-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 font-semibold uppercase tracking-wider text-[10px]">
          <p>© 2026 MindStep AI • Micro-Productivity for Wellbeing</p>
          <div className="flex gap-4">
            <span>User Status: Brain-dumping</span>
            <span>•</span>
            <span>Mode: Gentle Nudge</span>
          </div>
        </div>
      </footer>

      {/* ONBOARDING PERSONA SELECTION MODAL */}
      {showPersonaModal && (
        <div className="fixed inset-0 z-50 bg-[#3A3A3A]/40 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white border border-[#E5E0D5] w-full max-w-md rounded-[32px] p-8 shadow-2xl relative overflow-hidden flex flex-col gap-6 animate-fadeIn">
            <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
              <Brain className="h-24 w-24 text-[#8DAA91]" />
            </div>
            
            <div className="text-center animate-fadeIn">
              <div className="h-12 w-12 rounded-full bg-[#8DAA91]/15 text-[#8DAA91] mx-auto flex items-center justify-center mb-4">
                <Brain className="h-6 w-6" id="welcome-logo" />
              </div>
              <h2 className="text-xl font-bold font-display text-[#4A5D4D]">Selamat datang di MindStep AI! 👋</h2>
              <p className="text-xs text-[#7A7469] mt-2 leading-relaxed">
                Asisten produktivitas mikro & wellbeing kamu. Yuk, tentukan profil kamu untuk menyesuaikan gaya bahasa AI pas kamu masuk!
              </p>
            </div>

            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => {
                  setUserPersona("genz");
                  localStorage.setItem("mindstep_persona", "genz");
                  setShowPersonaModal(false);
                }}
                className="group border border-[#E5E0D5] hover:border-[#8DAA91] rounded-2xl p-4 text-left flex items-start gap-4 bg-[#F9F7F2]/40 hover:bg-[#8DAA91]/5 transition-all text-sm"
              >
                <div className="h-8 w-8 rounded-full bg-[#8DAA91] text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                  Z
                </div>
                <div>
                  <h4 className="font-bold text-sm text-[#4A5D4D] group-hover:text-[#8DAA91] transition-all">Generasi Z (Jaksel style)</h4>
                  <p className="text-xs text-[#7A7469] mt-1 leading-relaxed">
                    Pendekatan kasual, penuh istilah Inggris populer ("overwhelmed", "burnout"). Hangat & supel bak sahabat karib sebaya.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  setUserPersona("professional");
                  localStorage.setItem("mindstep_persona", "professional");
                  setShowPersonaModal(false);
                }}
                className="group border border-[#E5E0D5] hover:border-[#4A5D4D] rounded-2xl p-4 text-left flex items-start gap-4 bg-[#F9F7F2]/40 hover:bg-[#4A5D4D]/10 transition-all text-sm"
              >
                <div className="h-8 w-8 rounded-full bg-[#4A5D4D] text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5 animate-fadeIn">
                  P
                </div>
                <div>
                  <h4 className="font-bold text-sm text-[#4A5D4D] group-hover:text-[#4A5D4D] transition-all font-sans">Profesional / Umum</h4>
                  <p className="text-xs text-[#7A7469] mt-1 leading-relaxed">
                    Gaya bahasa yang dewasa, santun, sopan, dan terstruktur dengan Bahasa Indonesia yang baku namun tetap penuh kehangatan serta empati.
                  </p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
