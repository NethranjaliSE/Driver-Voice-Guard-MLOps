import { motion } from "framer-motion";
import { STATE_META } from "../theme";

export default function DriverStateCard({ state, allScores = {} }) {
  const meta = STATE_META[state] || { emoji: "❔", color: "#9ca3af", label: "Awaiting audio…" };
  const entries = Object.entries(allScores).sort((a, b) => b[1] - a[1]);

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
      <div className="text-xs text-gray-500 uppercase tracking-wide">Current state</div>

      <div className="flex items-center gap-3">
        <div className="relative w-12 h-12 flex items-center justify-center">
          {state && (
            <motion.span
              className="absolute inset-0 rounded-full"
              style={{ backgroundColor: meta.color, opacity: 0.18 }}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 1.6, repeat: Infinity }}
            />
          )}
          <span className="text-3xl relative">{meta.emoji}</span>
        </div>
        <div>
          <div className="text-lg font-semibold" style={{ color: meta.color }}>
            {state ? state[0].toUpperCase() + state.slice(1) : "—"}
          </div>
          <div className="text-xs text-gray-500">{meta.label}</div>
        </div>
      </div>

      <div className="space-y-1.5 mt-1">
        {entries.length === 0 && <p className="text-gray-600 text-xs">No data yet.</p>}
        {entries.map(([label, score]) => (
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
  );
}
