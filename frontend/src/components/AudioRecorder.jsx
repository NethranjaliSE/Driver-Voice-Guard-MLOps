import { useState, useRef, useEffect, useMemo } from "react";
import { Mic, Square, RotateCcw } from "lucide-react";
import toast from "react-hot-toast";

export default function AudioRecorder({ onAudio, loading }) {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [blob, setBlob] = useState(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const audioUrl = useMemo(() => (blob ? URL.createObjectURL(blob) : null), [blob]);
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      rec.ondataavailable = (e) => chunksRef.current.push(e.data);
      rec.onstop = () => {
        const b = new Blob(chunksRef.current, { type: "audio/webm" });
        setBlob(b);
        stream.getTracks().forEach((t) => t.stop());
      };

      rec.start();
      mediaRef.current = rec;
      setRecording(true);
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch {
      toast.error("Microphone access denied. Please allow mic permissions.");
    }
  }

  function stopRecording() {
    mediaRef.current?.stop();
    clearInterval(timerRef.current);
    setRecording(false);
  }

  function reset() {
    setBlob(null);
    setDuration(0);
  }

  function formatTime(s) {
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  }

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-8 flex flex-col items-center gap-6">
      {/* Waveform / idle indicator */}
      <div className="w-24 h-24 rounded-full bg-gray-800 flex items-center justify-center relative">
        {recording && (
          <div className="absolute inset-0 rounded-full bg-red-500/20 animate-ping" />
        )}
        <div
          className={`flex items-end gap-1 h-8 ${!recording && "opacity-30"}`}
        >
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className={`w-2 rounded-full bg-indigo-400 ${recording ? "soundwave-bar" : ""}`}
              style={{
                height: recording ? "32px" : `${[14, 22, 30, 22, 14][i]}px`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Timer */}
      <div className="text-3xl font-mono text-gray-200 tabular-nums">
        {formatTime(duration)}
      </div>

      {/* Playback of the recorded clip */}
      {audioUrl && !recording && (
        <audio
          controls
          src={audioUrl}
          style={{ colorScheme: "dark" }}
          className="w-full"
        />
      )}

      {/* Controls */}
      <div className="flex gap-3">
        {!recording && !blob && (
          <button
            onClick={startRecording}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors"
          >
            <Mic size={18} /> Start recording
          </button>
        )}

        {recording && (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-medium transition-colors"
          >
            <Square size={18} /> Stop
          </button>
        )}

        {blob && !recording && (
          <>
            <button
              onClick={reset}
              className="flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl font-medium transition-colors"
            >
              <RotateCcw size={16} /> Re-record
            </button>
            <button
              onClick={() => onAudio(blob)}
              disabled={loading}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-medium transition-colors"
            >
              {loading ? "Analyzing…" : "Analyze emotion"}
            </button>
          </>
        )}
      </div>

      <p className="text-gray-600 text-xs">
        Speak clearly for 2–5 seconds · WAV / WebM supported
      </p>
    </div>
  );
}
