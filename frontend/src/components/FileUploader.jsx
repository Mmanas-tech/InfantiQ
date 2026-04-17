import { motion } from "framer-motion";
import { useCallback, useMemo } from "react";
import { useDropzone } from "react-dropzone";

const MAX_SIZE = 10 * 1024 * 1024;
const ACCEPT = {
  "audio/wav": [".wav"],
  "audio/mpeg": [".mp3"],
  "audio/ogg": [".ogg"],
  "audio/mp4": [".m4a"],
  "audio/x-m4a": [".m4a"],
  "audio/webm": [".webm"],
};

const formatSize = (bytes) => `${(bytes / (1024 * 1024)).toFixed(2)} MB`;

const FileUploader = ({ file, setFile, onAnalyze, loading, error, setError }) => {
  const onDrop = useCallback(
    (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles?.length) {
        setError("Only wav, mp3, ogg, m4a, webm files up to 10MB are supported.");
        return;
      }
      if (!acceptedFiles?.length) return;

      const picked = acceptedFiles[0];
      if (picked.size > MAX_SIZE) {
        setError("That file is too large. Please use an audio file under 10MB.");
        return;
      }
      setError("");
      setFile(picked);
    },
    [setFile, setError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    multiple: false,
  });

  const dropClass = useMemo(
    () =>
      isDragActive
        ? "border-purple-300/90 shadow-neon bg-purple-500/10 border-dashed"
        : "border-white/20 bg-white/5",
    [isDragActive]
  );

  return (
    <div className="space-y-5">
      <motion.div
        {...getRootProps()}
        whileHover={{ y: -2 }}
        className={`cursor-pointer rounded-2xl border-2 p-8 text-center transition-all ${dropClass}`}
      >
        <input {...getInputProps()} />
        <p className="text-lg font-semibold">Drag & drop audio, or click to browse</p>
        <p className="mt-2 text-sm text-white/70">Supports .wav, .mp3, .ogg, .m4a, .webm (up to 10MB)</p>
      </motion.div>

      {file && (
        <div className="rounded-xl border border-white/15 bg-black/20 p-4">
          <p className="font-medium">🎵 {file.name}</p>
          <p className="text-sm text-white/70">{formatSize(file.size)}</p>
        </div>
      )}

      {error && <p className="text-sm text-red-300">{error}</p>}

      <motion.button
        disabled={!file || loading}
        onClick={() => file && onAnalyze(file, file.name)}
        whileHover={!file || loading ? undefined : { scale: 1.02 }}
        className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-purple-700 px-5 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45"
      >
        Analyze Cry
      </motion.button>
    </div>
  );
};

export default FileUploader;
