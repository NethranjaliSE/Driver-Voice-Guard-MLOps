import { motion } from "framer-motion";
import { EMOTION_META, RISK_META } from "../theme";

// Primary behavior card: big emoji + headline + description from the
// backend's behavior profile, bordered in the risk colour, with all 8
// emotion probability bars sorted by score (predicted one highlighted).
export default function DriverStateCard({ result }) {
  const riskColor = (RISK_META[result?.risk_level] || RISK_META.CALIBRATING).color;
  const entries = Object.entries(result?.all_scores || {}).sort((a, b) => b[1] - a[1]);

  return (
    <div
      className="bg-gray-900 border rounded-2xl p-5 flex flex-col gap-3 transition-colors"
      style={{ borderColor: result ? `${riskColor}66` : "#1f2937" }}
    >
      <div className="text-xs text-gray-500 uppercase tracking-wide">Current state</div>

      {!result && (
        <div className="flex items-center gap-3">
          <span className="text-3xl">❔</span>
          <div>
            <div className="text-lg font-semibold text-gray-400">—</div>
            <div className="text-xs text-gray-500">Awaiting audio…</div>
          </div>
        </div>
      )}

      {result && (
        <div className="flex items-start gap-3">
          <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
            <motion.span
              className="absolute inset-0 rounded-full"
              style={{ backgroundColor: riskColor, opacity: 0.18 }}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 1.6, repeat: Infinity }}
            />
            <span className="text-3xl relative">{result.emoji}</span>
          </div>
          <div className="min-w-0">
            <div className="text-lg font-semibold leading-tight" style={{ color: riskColor }}>
              {result.headline}
            </div>
            <div className="text-xs text-gray-400 mt-1">{result.description}</div>
          </div>
        </div>
      )}

      <div className="space-y-1.5 mt-1">
        {entries.length === 0 && <p className="text-gray-600 text-xs">No data yet.</p>}
        {entries.map(([emotion, score]) => {
          const meta = EMOTION_META[emotion] || { emoji: "❓", color: "#6366f1" };
          const predicted = emotion === result?.emotion;
          return (
            <div key={emotion} className={`flex items-center gap-2 text-xs ${predicted ? "" : "opacity-80"}`}>
              <span className="w-5 text-center">{meta.emoji}</span>
              <span className={`w-16 capitalize ${predicted ? "text-gray-200 font-semibold" : "text-gray-400"}`}>
                {emotion}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-gray-800 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${score}%`, backgroundColor: meta.color, opacity: predicted ? 1 : 0.55 }}
                />
              </div>
              <span className={`w-10 text-right tabular-nums ${predicted ? "text-gray-300" : "text-gray-500"}`}>
                {score.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
