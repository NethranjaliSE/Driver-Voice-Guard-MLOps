import { motion } from "framer-motion";

const RISK_META = {
  SAFE:    { label: "SAFE",    bg: "bg-green-500/15",  text: "text-green-400",  ring: "ring-green-500/40",  dot: "bg-green-400" },
  CAUTION: { label: "CAUTION", bg: "bg-yellow-500/15", text: "text-yellow-400", ring: "ring-yellow-500/40", dot: "bg-yellow-400" },
  WARNING: { label: "WARNING", bg: "bg-orange-500/15", text: "text-orange-400", ring: "ring-orange-500/40", dot: "bg-orange-400" },
  DANGER:  { label: "DANGER",  bg: "bg-red-500/15",    text: "text-red-400",    ring: "ring-red-500/40",    dot: "bg-red-400" },
  CALIBRATING: { label: "CALIBRATING", bg: "bg-gray-500/15", text: "text-gray-400", ring: "ring-gray-500/40", dot: "bg-gray-400" },
};

export default function RiskBadge({ riskLevel = "SAFE", alertTriggered = false }) {
  const meta = RISK_META[riskLevel] || RISK_META.SAFE;

  return (
    <motion.div
      animate={alertTriggered ? { opacity: [1, 0.35, 1] } : { opacity: 1 }}
      transition={{ duration: 0.4, repeat: alertTriggered ? 2 : 0 }}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ring-1 self-start ${meta.bg} ${meta.text} ${meta.ring} font-semibold text-sm`}
    >
      <span className={`w-2 h-2 rounded-full ${meta.dot}`} />
      {meta.label}
    </motion.div>
  );
}
