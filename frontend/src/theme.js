// Shared colour/emoji/label lookup for each driver state — kept in one
// place since SafetyScoreGauge, DriverStateCard, AlertFeed and the
// full-screen overlay all need to render the same state consistently.
export const STATE_META = {
  alert:    { emoji: "🟢", color: "#22c55e", label: "Focused" },
  drowsy:   { emoji: "🟡", color: "#eab308", label: "Drowsy — take a break" },
  stressed: { emoji: "🟠", color: "#f97316", label: "Stressed" },
  angry:    { emoji: "🔴", color: "#ef4444", label: "Agitated — road rage risk" },
  calibrating: { emoji: "⚪", color: "#9ca3af", label: "Calibrating — listening for clear speech" },
};
