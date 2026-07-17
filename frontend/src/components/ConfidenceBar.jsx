import { motion } from "framer-motion";

export default function ConfidenceBar({ label, score, highlight, meta }) {
  const barColor = highlight ? "bg-indigo-500" : "bg-gray-700";

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span
          className={`text-sm capitalize flex items-center gap-1.5 ${highlight ? "text-gray-100 font-medium" : "text-gray-400"}`}
        >
          {meta?.emoji} {label}
        </span>
        <span
          className={`text-sm tabular-nums ${highlight ? "text-indigo-400 font-medium" : "text-gray-500"}`}
        >
          {score.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
