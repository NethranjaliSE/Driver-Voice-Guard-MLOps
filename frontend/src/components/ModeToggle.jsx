import { Mic, Upload } from "lucide-react";

export default function ModeToggle({ mode, onChange }) {
  return (
    <div className="flex rounded-xl bg-gray-900 border border-gray-800 p-1 gap-1">
      {[
        { key: "record", label: "Record voice", Icon: Mic },
        { key: "upload", label: "Upload file", Icon: Upload },
      ].map(({ key, label, Icon }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${
            mode === key
              ? "bg-indigo-600 text-white shadow"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  );
}
