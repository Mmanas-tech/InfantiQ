import { motion } from "framer-motion";
import { useState } from "react";
import BabyAvatar from "../components/BabyAvatar";
import CryTimelineDashboard from "../components/CryTimelineDashboard";
import FileUploader from "../components/FileUploader";
import InsightsPanel from "../components/InsightsPanel";
import LoadingScreen from "../components/LoadingScreen";
import MicRecorder from "../components/MicRecorder";
import ResultCard from "../components/ResultCard";
import { useAnalysis } from "../hooks/useAnalysis";
import useCaretakerAlerts from "../hooks/useCaretakerAlerts";

const tabs = ["record", "upload"];

const formatLocalDateTime = (value) => {
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toISOString().slice(0, 16);
};

const Analyzer = () => {
  const [activeTab, setActiveTab] = useState("record");
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");
  const [babyId, setBabyId] = useState("baby-001");
  const [lastFeedingAt, setLastFeedingAt] = useState("");
  const [lastSleepAt, setLastSleepAt] = useState("");
  const [parentAway, setParentAway] = useState(false);
  const { loading, result, error, startedAt, runAnalysis, reset } = useAnalysis();
  useCaretakerAlerts({ result, parentAway });

  const handleAnalyze = async (blob, filename) => {
    setLocalError("");
    try {
      await runAnalysis(blob, filename, {
        babyId: babyId.trim(),
        lastFeedingAt: lastFeedingAt ? new Date(lastFeedingAt).toISOString() : "",
        lastSleepAt: lastSleepAt ? new Date(lastSleepAt).toISOString() : "",
        parentAway,
      });
    } catch {
      // handled by hook
    }
  };

  const resetAll = () => {
    setFile(null);
    setLocalError("");
    reset();
  };

  return (
    <div className="min-h-screen px-4 py-14 text-white">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="rounded-3xl border border-white/15 bg-black/25 p-6 md:p-8">
          <h1 className="mb-6 text-center text-3xl font-bold">Cry Analyzer</h1>

          <div className="mb-6 grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block text-white/70">Baby ID</span>
              <input
                value={babyId}
                onChange={(e) => setBabyId(e.target.value)}
                className="w-full rounded-lg border border-white/20 bg-black/20 px-3 py-2 text-sm"
                placeholder="baby-001"
              />
            </label>

            <label className="flex items-end gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={parentAway}
                onChange={(e) => setParentAway(e.target.checked)}
                className="h-4 w-4"
              />
              Parent away mode (voice + notifications)
            </label>

            <div className="space-y-2">
              <label className="text-sm">
                <span className="mb-1 block text-white/70">Last Feeding</span>
                <input
                  type="datetime-local"
                  value={lastFeedingAt}
                  onChange={(e) => setLastFeedingAt(e.target.value)}
                  className="w-full rounded-lg border border-white/20 bg-black/20 px-3 py-2 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={() => setLastFeedingAt(formatLocalDateTime(Date.now()))}
                className="rounded-md border border-white/20 bg-white/10 px-3 py-1 text-xs"
              >
                Mark feeding now
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-sm">
                <span className="mb-1 block text-white/70">Last Sleep</span>
                <input
                  type="datetime-local"
                  value={lastSleepAt}
                  onChange={(e) => setLastSleepAt(e.target.value)}
                  className="w-full rounded-lg border border-white/20 bg-black/20 px-3 py-2 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={() => setLastSleepAt(formatLocalDateTime(Date.now()))}
                className="rounded-md border border-white/20 bg-white/10 px-3 py-1 text-xs"
              >
                Mark sleep now
              </button>
            </div>
          </div>

          {!loading && !result && (
            <div className="mb-6 flex rounded-xl border border-white/15 bg-white/5 p-1">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className="relative w-1/2 rounded-lg py-2 text-sm font-semibold uppercase tracking-wide"
                >
                  {activeTab === tab && (
                    <motion.span
                      layoutId="tab-indicator"
                      className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-700"
                      transition={{ type: "spring", stiffness: 260, damping: 24 }}
                    />
                  )}
                  <span className="relative z-10">{tab === "record" ? "Record Audio" : "Upload File"}</span>
                </button>
              ))}
            </div>
          )}

          {loading && startedAt ? (
            <LoadingScreen startedAt={startedAt} />
          ) : result ? (
            <div className="space-y-4">
              <BabyAvatar prediction={result.prediction} confidence={result.confidence} />
              <ResultCard result={result} onReset={resetAll} />
            </div>
          ) : activeTab === "record" ? (
            <MicRecorder onAnalyze={handleAnalyze} loading={loading} setError={setLocalError} />
          ) : (
            <FileUploader
              file={file}
              setFile={setFile}
              onAnalyze={handleAnalyze}
              loading={loading}
              error={localError}
              setError={setLocalError}
            />
          )}

          {(error || localError) && !loading && !result && (
            <p className="mt-5 rounded-xl border border-red-300/30 bg-red-400/10 p-3 text-sm text-red-200">
              {error || localError}
            </p>
          )}
        </div>

        <CryTimelineDashboard babyId={babyId.trim()} />
        <InsightsPanel analysisResult={result} babyId={babyId.trim()} />
      </div>
    </div>
  );
};

export default Analyzer;
