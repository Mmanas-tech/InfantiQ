import { motion } from "framer-motion";
import { useState } from "react";
import FileUploader from "../components/FileUploader";
import LoadingScreen from "../components/LoadingScreen";
import MicRecorder from "../components/MicRecorder";
import ResultCard from "../components/ResultCard";
import { useAnalysis } from "../hooks/useAnalysis";

const tabs = ["record", "upload"];

const Analyzer = () => {
  const [activeTab, setActiveTab] = useState("record");
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");
  const { loading, result, error, startedAt, runAnalysis, reset } = useAnalysis();

  const handleAnalyze = async (blob, filename) => {
    setLocalError("");
    try {
      await runAnalysis(blob, filename);
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
      <div className="mx-auto max-w-2xl rounded-3xl border border-white/15 bg-black/25 p-6 md:p-8">
        <h1 className="mb-6 text-center text-3xl font-bold">Cry Analyzer</h1>

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
          <ResultCard result={result} onReset={resetAll} />
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
    </div>
  );
};

export default Analyzer;
