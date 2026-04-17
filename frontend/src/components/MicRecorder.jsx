import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

const formatTime = (seconds) => {
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
};

const MicRecorder = ({ onAnalyze, loading, setError }) => {
  const canvasRef = useRef(null);
  const { isRecording, elapsed, permissionError, waveData, startRecording, stopRecording } = useAudioRecorder();

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "rgba(20, 22, 58, 1)";
    ctx.fillRect(0, 0, w, h);

    const barWidth = w / waveData.length;
    waveData.forEach((v, i) => {
      const amp = (v / 255) * h;
      const x = i * barWidth;
      const y = h - amp;
      const grd = ctx.createLinearGradient(0, y, 0, h);
      grd.addColorStop(0, "#8f55ff");
      grd.addColorStop(1, "#5a93ff");
      ctx.fillStyle = grd;
      ctx.fillRect(x, y, Math.max(barWidth - 2, 1), amp);
    });
  }, [waveData]);

  const begin = async () => {
    setError("");
    await startRecording();
  };

  const stopAndAnalyze = async () => {
    const blob = await stopRecording();
    if (!blob) {
      setError("Recording failed. Please try again.");
      return;
    }
    onAnalyze(blob, "recording.webm");
  };

  return (
    <div className="space-y-5">
      <div className="flex justify-center">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={isRecording ? stopAndAnalyze : begin}
          disabled={loading}
          className={`relative flex h-28 w-28 items-center justify-center rounded-full text-4xl ${
            isRecording ? "bg-red-500" : "bg-gradient-to-r from-indigo-600 to-purple-700"
          }`}
        >
          <span className={`absolute inset-0 rounded-full ${isRecording ? "animate-ping bg-red-400/50" : "animate-pulse bg-white/10"}`} />
          <span className="relative">🎙️</span>
        </motion.button>
      </div>

      <canvas ref={canvasRef} width="640" height="120" className="h-28 w-full rounded-xl border border-white/15" />

      <div className="flex items-center justify-between text-sm text-white/80">
        <span>{isRecording ? "Recording..." : "Ready"}</span>
        <span>{formatTime(elapsed)}</span>
      </div>

      {permissionError && <p className="text-sm text-amber-300">{permissionError}</p>}

      {isRecording && elapsed >= 2 && (
        <motion.button
          onClick={stopAndAnalyze}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full rounded-xl bg-gradient-to-r from-red-600 to-rose-600 px-5 py-3 font-semibold text-white"
        >
          Stop & Analyze
        </motion.button>
      )}
    </div>
  );
};

export default MicRecorder;
