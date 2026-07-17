import { motion } from "framer-motion";
import ConfidenceBar from "./ConfidenceBar";

const EMOTION_META = {
  calm: {
    emoji: "😌",
    color: "text-blue-400",
    bg: "bg-blue-900/30",
    border: "border-blue-700/40",
    label: "Calm",
  },
  happy: {
    emoji: "😄",
    color: "text-yellow-400",
    bg: "bg-yellow-900/30",
    border: "border-yellow-700/40",
    label: "Happy",
  },
  fearful: {
    emoji: "😨",
    color: "text-purple-400",
    bg: "bg-purple-900/30",
    border: "border-purple-700/40",
    label: "Fearful",
  },
  disgust: {
    emoji: "🤢",
    color: "text-green-400",
    bg: "bg-green-900/30",
    border: "border-green-700/40",
    label: "Disgust",
  },
};

const EMOTION_TIPS = {
  calm: "Your voice carries a calm, relaxed tone — great for meditation or focused work contexts.",
  happy:
    "Your voice sounds upbeat and cheerful. Perfect energy for presentations or social calls!",
  fearful:
    "A hint of anxiety or nervousness was detected. Take a deep breath — you've got this!",
  disgust:
    "Your voice conveys displeasure or discomfort. Consider reframing your thoughts.",
};

export default function EmotionResult({ result }) {
  const { emotion, confidence, all_scores, latency_ms } = result;
  const meta = EMOTION_META[emotion] || {
    emoji: "🎭",
    color: "text-gray-400",
    bg: "bg-gray-800",
    border: "border-gray-700",
    label: emotion,
  };

  const sorted = Object.entries(all_scores).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-4">
      {/* Primary result card */}
      <div className={`rounded-2xl border p-6 ${meta.bg} ${meta.border}`}>
        <div className="flex items-center gap-4">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 12 }}
            className="text-6xl"
          >
            {meta.emoji}
          </motion.div>
          <div className="flex-1">
            <motion.h2
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className={`text-3xl font-bold ${meta.color}`}
            >
              {meta.label}
            </motion.h2>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-gray-400 text-sm mt-1"
            >
              {confidence}% confidence
              {latency_ms && (
                <span className="ml-3 text-gray-600">· {latency_ms}ms</span>
              )}
            </motion.p>
          </div>
        </div>

        {/* Insight */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-4 text-sm text-gray-400 leading-relaxed"
        >
          {EMOTION_TIPS[emotion]}
        </motion.p>
      </div>

      {/* All scores */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Confidence breakdown
        </h3>
        {sorted.map(([label, score], i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.07 }}
          >
            <ConfidenceBar
              label={label}
              score={score}
              highlight={label === emotion}
              meta={EMOTION_META[label]}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
