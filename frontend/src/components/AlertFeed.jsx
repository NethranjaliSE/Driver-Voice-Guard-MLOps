import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { STATE_META } from "../theme";

export default function AlertFeed({ alerts = [] }) {
  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3 max-h-72 overflow-y-auto">
      <div className="text-xs text-gray-500 uppercase tracking-wide">Alert feed</div>

      {alerts.length === 0 && <p className="text-gray-600 text-sm">No alerts yet.</p>}

      <AnimatePresence initial={false}>
        {alerts.map((a) => {
          const meta = STATE_META[a.state] || {};
          return (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-start gap-2 bg-red-950/40 border border-red-900/60 rounded-lg p-3"
            >
              <AlertTriangle size={16} className="text-red-400 mt-0.5 shrink-0" />
              <div className="text-sm">
                <div className="font-medium capitalize" style={{ color: meta.color || "#f87171" }}>
                  {meta.emoji} {a.state}
                </div>
                <div className="text-gray-400 text-xs">{a.recommendation}</div>
                <div className="text-gray-600 text-[11px] mt-0.5">{a.time}</div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
