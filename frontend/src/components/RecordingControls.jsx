import { useRef, useState } from "react";
import { Play, Square, Download } from "lucide-react";
import toast from "react-hot-toast";
import { startSession, sendChunk, downloadReportPdf } from "../api";

const CHUNK_MS = 3000;

export default function RecordingControls({ monitoring, sessionId, onStart, onChunk, onStop }) {
  const [starting, setStarting] = useState(false);
  const mediaRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const sessionIdRef = useRef(null);

  // MediaRecorder's `timeslice` option only emits one self-contained WebM
  // header at the very start of the stream — every ondataavailable blob
  // after the first lacks it and won't decode on its own. Instead we start
  // a brand-new MediaRecorder (on the same mic stream) every CHUNK_MS, so
  // each chunk is its own valid, independently-decodable WebM file.
  function recordOneChunk(stream) {
    const rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
    const localChunks = [];
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) localChunks.push(e.data);
    };
    rec.onstop = async () => {
      const blob = new Blob(localChunks, { type: "audio/webm" });
      if (blob.size === 0) return;
      try {
        const result = await sendChunk(sessionIdRef.current, blob);
        onChunk(result, blob);
      } catch (err) {
        toast.error(err.message || "Chunk analysis failed");
      }
    };
    rec.start();
    mediaRef.current = rec;
  }

  async function start() {
    setStarting(true);
    try {
      const { session_id } = await startSession();
      sessionIdRef.current = session_id;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      recordOneChunk(stream);
      intervalRef.current = setInterval(() => {
        mediaRef.current?.stop();
        recordOneChunk(stream);
      }, CHUNK_MS);

      onStart(session_id);
    } catch {
      toast.error("Microphone access denied. Please allow mic permissions.");
    } finally {
      setStarting(false);
    }
  }

  function stop() {
    clearInterval(intervalRef.current);
    mediaRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    onStop(sessionIdRef.current);
  }

  async function exportPdf() {
    if (!sessionId) return;
    try {
      await downloadReportPdf(sessionId);
    } catch (err) {
      toast.error(err.message || "Could not generate PDF");
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5 flex flex-col gap-3">
      <div className="text-xs text-gray-500 uppercase tracking-wide">Recording controls</div>

      <div className="flex flex-col gap-2">
        {!monitoring ? (
          <button
            onClick={start}
            disabled={starting}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-medium transition-colors"
          >
            <Play size={16} /> {starting ? "Starting…" : "Start Monitoring"}
          </button>
        ) : (
          <button
            onClick={stop}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-medium transition-colors"
          >
            <Square size={16} /> Stop + Report
          </button>
        )}

        <button
          onClick={exportPdf}
          disabled={!sessionId}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-gray-300 rounded-xl font-medium transition-colors"
        >
          <Download size={16} /> Export PDF
        </button>
      </div>

      <p className="text-gray-600 text-xs">Records in 3-second chunks while monitoring is active.</p>
    </div>
  );
}
