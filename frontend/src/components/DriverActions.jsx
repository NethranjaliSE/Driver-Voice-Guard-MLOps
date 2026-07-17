import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { STATE_META } from "../theme";

// Icons inferred from the backend's car_action text.
function iconFor(action) {
  const a = action.toLowerCase();
  if (a.includes("music")) return "🎵";
  if (a.includes("breathing")) return "🧘";
  if (a.includes("silence")) return "🔕";
  if (a.includes("window")) return "🪟";
  if (a.includes("hazard")) return "⚠️";
  if (a.includes("cruise")) return "🚗";
  if (a.includes("distance")) return "↔️";
  if (a.includes("ac")) return "❄️";
  return "🔧";
}

// Suggested in-car actions from the detected emotion's behavior profile.
// These are simulated suggestions — nothing is sent to a real vehicle.
export default function DriverActions({ state, actions = [] }) {
  const [applied, setApplied] = useState({});
  const [prevState, setPrevState] = useState(state);

  // New detected state → fresh suggestions, clear previous "applied" ticks.
  if (state !== prevState) {
    setPrevState(state);
    setApplied({});
  }

  const meta = STATE_META[state];

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-500 uppercase tracking-wide">Smart car suggestions</div>
        <span className="text-[10px] text-gray-600 border border-gray-800 rounded-full px-2 py-0.5">
          simulated — no vehicle connected
        </span>
      </div>

      {!state && (
        <p className="text-gray-600 text-sm">
          Start monitoring — car actions will be suggested here based on the detected mood.
        </p>
      )}

      {state && actions.length === 0 && (
        <p className="text-gray-500 text-sm">
          {meta?.emoji} No actions needed for <span className="font-semibold" style={{ color: meta?.color }}>{state.replace("_", " ")}</span> — keep driving safely.
        </p>
      )}

      {state && actions.length > 0 && (
        <>
          <p className="text-sm text-gray-400">
            <span className="mr-1">{meta?.emoji}</span>
            Driver&apos;s state is <span className="font-semibold" style={{ color: meta?.color }}>{state.replace("_", " ")}</span> —
            want to try these actions?
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <AnimatePresence mode="popLayout">
              {actions.map((action) => {
                const done = applied[action];
                return (
                  <motion.button
                    key={action}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setApplied((p) => ({ ...p, [action]: true }))}
                    disabled={done}
                    className={`flex items-center gap-3 text-left px-4 py-3 rounded-xl border text-sm transition-colors ${
                      done
                        ? "bg-green-500/10 border-green-500/30 text-green-300 cursor-default"
                        : "bg-gray-800/60 border-gray-700 text-gray-200 hover:bg-gray-800 hover:border-gray-600"
                    }`}
                  >
                    <span className="text-xl shrink-0">{done ? "✅" : iconFor(action)}</span>
                    <span className="flex-1">{action}</span>
                    {done && <span className="text-[10px] uppercase tracking-wide text-green-400 shrink-0">done</span>}
                  </motion.button>
                );
              })}
            </AnimatePresence>
          </div>
        </>
      )}
    </div>
  );
}
