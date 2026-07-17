import { useState } from "react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import ModeToggle from "./ModeToggle";
import AudioRecorder from "./AudioRecorder";
import FileUpload from "./FileUpload";
import SafetyScoreGauge from "./SafetyScoreGauge";
import RiskBadge from "./RiskBadge";
import DriverActions from "./DriverActions";
import { STATE_META } from "../theme";
import { analyzeVoice } from "../api";

// One-shot voice check: record a clip or upload an audio file, analyze it
// once via /analyze/voice, and show the same driver-state readout as the
// live dashboard — no session required.
export default function VoiceCheck() {
  const [mode, setMode] = useState("record");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleAudio(fileOrBlob) {
    setLoading(true);
    try {
      const r = await analyzeVoice(fileOrBlob);
      setResult(r);
    } catch (e) {
      toast.error(`Analysis failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  const meta = result ? STATE_META[result.state] : null;

  return (
    <div className="space-y-6">
      <div className="max-w-xl mx-auto space-y-4">
        <ModeToggle mode={mode} onChange={setMode} />
        {mode === "record" ? (
          <AudioRecorder onAudio={handleAudio} loading={loading} />
        ) : (
          <FileUpload onFile={handleAudio} loading={loading} />
        )}
      </div>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col items-center justify-center gap-2">
              <div className="text-xs text-gray-500 uppercase tracking-wide self-start">Safety score</div>
              <SafetyScoreGauge score={result.safety_score} />
            </div>

            <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Detected state</div>
              <div className="flex items-center gap-3">
                <span className="text-4xl">{meta?.emoji ?? "❔"}</span>
                <div>
                  <div className="text-xl font-semibold" style={{ color: meta?.color }}>
                    {result.state[0].toUpperCase() + result.state.slice(1)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {result.confidence.toFixed(0)}% confidence · {result.latency_ms}ms
                  </div>
                </div>
              </div>
              <div className="space-y-1.5 mt-1">
                {Object.entries(result.all_scores)
                  .sort((a, b) => b[1] - a[1])
                  .map(([label, score]) => (
                    <div key={label} className="flex items-center gap-2 text-xs">
                      <span className="w-16 text-gray-400 capitalize">{label}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-gray-800 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${score}%`, backgroundColor: (STATE_META[label] || {}).color || "#6366f1" }}
                        />
                      </div>
                      <span className="w-10 text-right text-gray-500 tabular-nums">{score.toFixed(0)}%</span>
                    </div>
                  ))}
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Risk level</div>
              <RiskBadge riskLevel={result.risk_level} alertTriggered={result.alert_triggered} />
              <p className="text-sm text-gray-400">{result.recommendation}</p>
            </div>
          </div>

          <DriverActions state={result.state} />
        </motion.div>
      )}
    </div>
  );
}
