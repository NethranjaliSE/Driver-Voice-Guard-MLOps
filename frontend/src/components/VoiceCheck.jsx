import { useState } from "react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import ModeToggle from "./ModeToggle";
import AudioRecorder from "./AudioRecorder";
import FileUpload from "./FileUpload";
import SafetyScoreGauge from "./SafetyScoreGauge";
import RiskBadge from "./RiskBadge";
import DriverActions from "./DriverActions";
import DriverStateCard from "./DriverStateCard";
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

            <DriverStateCard result={result} />

            <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Risk level</div>
              <RiskBadge riskLevel={result.risk_level} alertTriggered={result.alert_triggered} />
              <p className="text-sm text-gray-400 italic">{result.suggestion}</p>
              <p className="text-xs text-gray-600">
                Detected emotion: <span className="capitalize text-gray-400">{result.emotion}</span> ·{" "}
                {result.confidence.toFixed(0)}% confidence
                {result.latency_ms != null && <> · {result.latency_ms}ms</>}
              </p>
            </div>
          </div>

          <DriverActions state={result.driver_state} actions={result.car_actions} />
        </motion.div>
      )}
    </div>
  );
}
