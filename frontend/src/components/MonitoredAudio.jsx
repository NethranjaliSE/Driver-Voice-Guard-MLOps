import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { STATE_META } from "../theme";

// Playback list of the chunks the live monitor actually analyzed, each next
// to the state it was classified as — lets the user listen back and judge
// whether the detection was correct.
export default function MonitoredAudio({ clips }) {
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);

  // Stop playback when the panel unmounts.
  useEffect(() => () => audioRef.current?.pause(), []);

  function toggle(clip) {
    if (playingId === clip.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }
    audioRef.current?.pause();
    const audio = new Audio(clip.url);
    audio.onended = () => setPlayingId(null);
    audio.play();
    audioRef.current = audio;
    setPlayingId(clip.id);
  }

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-500 uppercase tracking-wide">Monitored audio</div>
        <span className="text-[10px] text-gray-600">last {clips.length} chunk{clips.length === 1 ? "" : "s"}</span>
      </div>

      {clips.length === 0 && (
        <p className="text-gray-600 text-sm">
          Analyzed audio chunks will appear here — play them back to verify the detected state.
        </p>
      )}

      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {clips.map((clip) => {
          const meta = STATE_META[clip.state] || {};
          const playing = playingId === clip.id;
          return (
            <div
              key={clip.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl border text-sm ${
                playing ? "bg-indigo-500/10 border-indigo-500/40" : "bg-gray-800/50 border-gray-800"
              }`}
            >
              <button
                onClick={() => toggle(clip)}
                className="w-8 h-8 shrink-0 flex items-center justify-center rounded-full bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                title={playing ? "Pause" : "Play this chunk"}
              >
                {playing ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
              </button>
              <span className="font-mono text-xs text-gray-500 tabular-nums shrink-0">{clip.time}</span>
              <span className="shrink-0">{meta.emoji}</span>
              <span className="font-medium capitalize" style={{ color: meta.color }}>
                {clip.state}
              </span>
              <span className="text-xs text-gray-500 ml-auto tabular-nums shrink-0">
                {clip.confidence.toFixed(0)}% · score {clip.safety_score}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
