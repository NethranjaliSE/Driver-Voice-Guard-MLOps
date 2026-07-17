import { useCallback, useState, useEffect, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileAudio, X } from "lucide-react";

export default function FileUpload({ onFile, loading }) {
  const [file, setFile] = useState(null);

  const onDrop = useCallback((accepted) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const audioUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "audio/*": [".wav", ".mp3", ".ogg", ".flac", ".m4a"] },
    maxFiles: 1,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`bg-gray-900 border-2 border-dashed rounded-2xl p-10 flex flex-col items-center gap-4 cursor-pointer transition-colors ${
          isDragActive
            ? "border-indigo-500 bg-indigo-900/10"
            : "border-gray-700 hover:border-gray-600"
        }`}
      >
        <input {...getInputProps()} />
        <Upload size={36} className="text-gray-500" />
        <div className="text-center">
          <p className="text-gray-300 font-medium">
            {isDragActive
              ? "Drop the audio file here…"
              : "Drag & drop an audio file"}
          </p>
          <p className="text-gray-500 text-sm mt-1">or click to browse</p>
          <p className="text-gray-600 text-xs mt-2">
            WAV · MP3 · OGG · FLAC · M4A
          </p>
        </div>
      </div>

      {file && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileAudio size={20} className="text-indigo-400" />
              <div>
                <p className="text-sm text-gray-200 font-medium">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFile(null)}
                className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X size={16} />
              </button>
              <button
                onClick={() => onFile(file)}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {loading ? "Analyzing…" : "Analyze"}
              </button>
            </div>
          </div>

          {audioUrl && (
            <audio
              controls
              src={audioUrl}
              style={{ colorScheme: "dark" }}
              className="w-full"
            />
          )}
        </div>
      )}
    </div>
  );
}
