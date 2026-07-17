// Shared colour/emoji lookups. The backend now sends the emoji, headline,
// description, suggestion and car_actions inside each response — these maps
// only cover chrome the payload doesn't carry (bar colours, risk borders,
// compact rows in MonitoredAudio / AlertFeed).

// Risk level → accent colour (card borders, badges).
export const RISK_META = {
  SAFE:        { color: "#22c55e" },
  CAUTION:     { color: "#f59e0b" },
  WARNING:     { color: "#f97316" },
  DANGER:      { color: "#ef4444" },
  CALIBRATING: { color: "#9ca3af" },
};

// Raw emotion → emoji + bar colour for the 8-emotion score bars.
export const EMOTION_META = {
  neutral:   { emoji: "😐", color: "#9ca3af" },
  calm:      { emoji: "😌", color: "#22c55e" },
  happy:     { emoji: "😄", color: "#eab308" },
  sad:       { emoji: "😢", color: "#60a5fa" },
  angry:     { emoji: "😠", color: "#ef4444" },
  fearful:   { emoji: "😨", color: "#a855f7" },
  disgust:   { emoji: "🤢", color: "#84cc16" },
  surprised: { emoji: "😲", color: "#f97316" },
};

// driver_state → emoji/colour/label for compact rows (alert feed, clip list).
export const STATE_META = {
  focused:       { emoji: "😐", color: "#22c55e", label: "Focused and composed" },
  relaxed:       { emoji: "😌", color: "#22c55e", label: "Perfectly relaxed" },
  energetic:     { emoji: "😄", color: "#eab308", label: "Positive and energetic" },
  low_mood:      { emoji: "😢", color: "#f59e0b", label: "Low mood — reduced focus" },
  agitated:      { emoji: "😠", color: "#ef4444", label: "Agitated — road rage risk" },
  anxious:       { emoji: "😨", color: "#ef4444", label: "Panic or anxiety" },
  uncomfortable: { emoji: "🤢", color: "#f59e0b", label: "Discomfort — distracted" },
  startled:      { emoji: "😲", color: "#f97316", label: "Startled — brief focus loss" },
  calibrating:   { emoji: "⏳", color: "#9ca3af", label: "Calibrating — listening for clear speech" },
};
