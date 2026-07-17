import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import SafetyScoreGauge from "./components/SafetyScoreGauge";
import DriverStateCard from "./components/DriverStateCard";
import RiskBadge from "./components/RiskBadge";
import DriverActions from "./components/DriverActions";
import EmotionTimeline from "./components/EmotionTimeline";
import AlertFeed from "./components/AlertFeed";
import MonitoredAudio from "./components/MonitoredAudio";
import RecordingControls from "./components/RecordingControls";
import SessionReport from "./components/SessionReport";
import VoiceCheck from "./components/VoiceCheck";
import { fetchHealth, getSessionReport } from "./api";

function playBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 440;
    osc.type = "sine";
    gain.gain.value = 0.05;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    setTimeout(() => {
      osc.stop();
      ctx.close();
    }, 200);
  } catch {
    // Web Audio unavailable — non-critical, skip the beep.
  }
}

function formatTime(s) {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

let alertSeq = 0;
let clipSeq = 0;
const MAX_CLIPS = 20;

export default function App() {
  const [monitoring, setMonitoring] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [current, setCurrent] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [clips, setClips] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [showOverlay, setShowOverlay] = useState(false);
  const [report, setReport] = useState(null);
  const [view, setView] = useState("monitor");
  const [apiOk, setApiOk] = useState(null);
  const consecutiveDangerRef = useRef(0);

  useEffect(() => {
    if (!monitoring) return;
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [monitoring]);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        await fetchHealth();
        if (!cancelled) setApiOk(true);
      } catch {
        if (!cancelled) setApiOk(false);
      }
    }
    check();
    const id = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  function handleStart(id) {
    setSessionId(id);
    setMonitoring(true);
    setCurrent(null);
    setTimeline([]);
    setAlerts([]);
    setClips((c) => {
      c.forEach((clip) => URL.revokeObjectURL(clip.url));
      return [];
    });
    setElapsed(0);
    setShowOverlay(false);
    setReport(null);
    consecutiveDangerRef.current = 0;
  }

  function handleChunk(result, blob) {
    setCurrent(result);
    setTimeline((t) => [...t, result]);

    if (blob) {
      clipSeq += 1;
      const clip = {
        id: clipSeq,
        url: URL.createObjectURL(blob),
        state: result.state,
        confidence: result.confidence,
        safety_score: result.safety_score,
        time: new Date().toLocaleTimeString(),
      };
      setClips((c) => {
        const next = [clip, ...c];
        next.slice(MAX_CLIPS).forEach((old) => URL.revokeObjectURL(old.url));
        return next.slice(0, MAX_CLIPS);
      });
    }

    if (result.risk_level === "DANGER") {
      consecutiveDangerRef.current += 1;
      if (consecutiveDangerRef.current >= 3) setShowOverlay(true);
    } else {
      consecutiveDangerRef.current = 0;
    }

    if (result.alert_triggered) {
      playBeep();
      alertSeq += 1;
      setAlerts((a) =>
        [
          {
            id: alertSeq,
            state: result.state,
            recommendation: result.recommendation,
            time: new Date().toLocaleTimeString(),
          },
          ...a,
        ].slice(0, 20),
      );
    }
  }

  async function handleStop(id) {
    setMonitoring(false);
    if (!id) return;
    try {
      const r = await getSessionReport(id);
      setReport(r);
    } catch {
      // Report stays unavailable if the session had no chunks recorded.
    }
  }

  return (
    <div className="min-h-screen bg-[rgb(10,12,18)] text-gray-100">
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-xl shrink-0">
              🚗
            </div>
            <div>
              <h1 className="text-lg font-semibold">Driver Safety Monitor</h1>
              <p className="text-xs text-gray-500">
                Voice-based drowsiness/stress/anger detection — prototype, not a certified safety device
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span
              className={`hidden sm:inline-flex items-center gap-1.5 text-[11px] ${
                apiOk === null ? "text-gray-500" : apiOk ? "text-green-500" : "text-red-400"
              }`}
              title="Backend API status"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  apiOk === null ? "bg-gray-600" : apiOk ? "bg-green-500" : "bg-red-500 animate-pulse"
                }`}
              />
              {apiOk === null ? "API…" : apiOk ? "API online" : "API offline"}
            </span>
            {monitoring && (
              <span className="text-sm font-mono tabular-nums text-gray-400">{formatTime(elapsed)}</span>
            )}
            <span
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                monitoring ? "bg-green-500/15 text-green-400" : "bg-gray-800 text-gray-500"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${monitoring ? "bg-green-400 animate-pulse" : "bg-gray-600"}`} />
              {monitoring ? "MONITORING" : "STOPPED"}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto w-full px-4 py-8 space-y-6">
        <div className="flex rounded-xl bg-gray-900 border border-gray-800 p-1 gap-1 max-w-md">
          {[
            { key: "monitor", label: "🚗 Live monitor" },
            { key: "check", label: "🎙️ Voice check" },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setView(key)}
              disabled={monitoring && key !== "monitor"}
              title={monitoring && key !== "monitor" ? "Stop monitoring to switch tabs — or use the Voice check panel below" : undefined}
              className={`relative flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                view === key ? "text-white" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {view === key && (
                <motion.span
                  layoutId="view-tab-pill"
                  className="absolute inset-0 rounded-lg bg-indigo-600 shadow"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative">{label}</span>
            </button>
          ))}
        </div>

        {view === "check" && <VoiceCheck />}

        <div className={view === "monitor" ? "space-y-6" : "hidden"}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col items-center justify-center gap-2">
            <div className="text-xs text-gray-500 uppercase tracking-wide self-start">Safety score</div>
            <SafetyScoreGauge score={current?.safety_score ?? 100} />
          </div>

          <DriverStateCard state={current?.state} allScores={current?.all_scores} />

          <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
            <div className="text-xs text-gray-500 uppercase tracking-wide">Risk level</div>
            <RiskBadge riskLevel={current?.risk_level ?? "SAFE"} alertTriggered={current?.alert_triggered} />
            <p className="text-sm text-gray-400">
              {current?.recommendation ?? "Start monitoring to see live risk assessment."}
            </p>
          </div>
        </div>

        <DriverActions state={current?.state} />

        <EmotionTimeline timeline={timeline} />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <RecordingControls
            monitoring={monitoring}
            sessionId={sessionId}
            onStart={handleStart}
            onChunk={handleChunk}
            onStop={handleStop}
          />
          <AlertFeed alerts={alerts} />
        </div>

        <MonitoredAudio clips={clips} />

        <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-5 space-y-4">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Voice check</div>
            <p className="text-sm text-gray-400 mt-1">
              Run a one-shot check anytime — record a clip or upload an audio file, without stopping the live monitor.
            </p>
          </div>
          <VoiceCheck />
        </div>
        </div>
      </main>

      <footer className="text-center text-gray-600 text-xs py-6">
        Driver Safety Monitor · MLPClassifier + librosa · prototype, not a certified safety device
      </footer>

      <AnimatePresence>
        {showOverlay && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-red-950/95 flex flex-col items-center justify-center z-50 gap-6 text-center px-6"
          >
            <motion.div
              animate={{ scale: [1, 1.08, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="text-6xl"
            >
              ⚠️
            </motion.div>
            <h2 className="text-3xl font-bold text-white">PLEASE PULL OVER SAFELY</h2>
            <p className="text-red-200 max-w-md">
              Multiple consecutive high-risk readings detected. Find a safe place to stop and rest.
            </p>
            <button
              onClick={() => {
                setShowOverlay(false);
                consecutiveDangerRef.current = 0;
              }}
              className="px-6 py-3 bg-white text-red-900 rounded-xl font-semibold hover:bg-red-100 transition-colors"
            >
              I'm OK, continue monitoring
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <SessionReport report={report} onClose={() => setReport(null)} />
    </div>
  );
}
