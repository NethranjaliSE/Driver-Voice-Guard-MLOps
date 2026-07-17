import { Mic } from "lucide-react";

export default function Header() {
  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
          <Mic size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-base font-semibold leading-tight gradient-text">
            Speech Emotion Recognition
          </h1>
          <p className="text-xs text-gray-500">
            Record or upload audio · AI detects your emotion
          </p>
        </div>
      </div>
    </header>
  );
}
