import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { STATE_META } from "../theme";

// Suggested in-car actions per detected driver state.
// These are simulated suggestions — nothing is sent to a real vehicle.
const STATE_ACTIONS = {
  alert: [
    { id: "keep-music", icon: "🎵", label: "Keep the current music playing" },
    { id: "route-ok", icon: "🗺️", label: "Continue on the current route" },
  ],
  drowsy: [
    { id: "energetic-music", icon: "🎵", label: "Play energetic music" },
    { id: "ac-cool", icon: "❄️", label: "Set AC to cool (18°C)" },
    { id: "window", icon: "🪟", label: "Open the window slightly — fresh air" },
    { id: "coffee-stop", icon: "☕", label: "Show the nearest rest area / coffee shop" },
  ],
  stressed: [
    { id: "soft-music", icon: "🎵", label: "Play soft music" },
    { id: "ac-comfort", icon: "❄️", label: "Set AC to comfortable (24°C)" },
    { id: "breathing", icon: "🧘", label: "Start a breathing exercise" },
    { id: "silence-calls", icon: "📵", label: "Silence calls / notifications" },
  ],
  angry: [
    { id: "calm-music", icon: "🎵", label: "Play calm music" },
    { id: "ac-cool-angry", icon: "❄️", label: "Set AC to cool" },
    { id: "break", icon: "⏸️", label: "Take a 5-minute break — stop somewhere safe" },
    { id: "easy-route", icon: "🗺️", label: "Find a route with less traffic" },
  ],
};

export default function DriverActions({ state }) {
  const [applied, setApplied] = useState({});
  const [prevState, setPrevState] = useState(state);

  // New detected state → fresh suggestions, clear previous "applied" ticks.
  if (state !== prevState) {
    setPrevState(state);
    setApplied({});
  }

  const actions = STATE_ACTIONS[state] || [];
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

      {state && (
        <>
          <p className="text-sm text-gray-400">
            <span className="mr-1">{meta?.emoji}</span>
            Driver&apos;s mood is <span className="font-semibold" style={{ color: meta?.color }}>{state}</span> —
            want to try these actions?
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <AnimatePresence mode="popLayout">
              {actions.map((a) => {
                const done = applied[a.id];
                return (
                  <motion.button
                    key={a.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setApplied((p) => ({ ...p, [a.id]: true }))}
                    disabled={done}
                    className={`flex items-center gap-3 text-left px-4 py-3 rounded-xl border text-sm transition-colors ${
                      done
                        ? "bg-green-500/10 border-green-500/30 text-green-300 cursor-default"
                        : "bg-gray-800/60 border-gray-700 text-gray-200 hover:bg-gray-800 hover:border-gray-600"
                    }`}
                  >
                    <span className="text-xl shrink-0">{done ? "✅" : a.icon}</span>
                    <span className="flex-1">{a.label}</span>
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
