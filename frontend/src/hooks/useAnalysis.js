import { useState } from "react";
import { analyzeCryWithContext } from "../api/analyzeApi";

const MIN_LOADING_MS = 5000;

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [startedAt, setStartedAt] = useState(null);

  const runAnalysis = async (audioBlob, filename, context = {}) => {
    setError("");
    setResult(null);
    setLoading(true);
    const start = Date.now();
    setStartedAt(start);

    try {
      const apiPromise = analyzeCryWithContext(audioBlob, filename, context);
      const minDelayPromise = new Promise((resolve) => setTimeout(resolve, MIN_LOADING_MS));
      const [data] = await Promise.all([apiPromise, minDelayPromise]);
      setResult(data);
      return data;
    } catch (err) {
      const data = err?.response?.data;
      const detail = data?.detail;
      let message = "Unable to analyze audio right now.";

      if (typeof data?.error === "string" && typeof detail === "string") {
        message = `${data.error}: ${detail}`;
      } else if (typeof data?.error === "string") {
        message = data.error;
      } else if (detail && typeof detail === "object") {
        const detailError = typeof detail.error === "string" ? detail.error : "";
        const detailMsg = typeof detail.detail === "string" ? detail.detail : "";
        if (detailError && detailMsg) {
          message = `${detailError}: ${detailMsg}`;
        } else if (detailError) {
          message = detailError;
        } else if (detailMsg) {
          message = detailMsg;
        }
      } else if (typeof detail === "string") {
        message = detail;
      }

      setError(message);
      throw err;
    } finally {
      const elapsed = Date.now() - start;
      if (elapsed < MIN_LOADING_MS) {
        await new Promise((resolve) => setTimeout(resolve, MIN_LOADING_MS - elapsed));
      }
      setLoading(false);
    }
  };

  const reset = () => {
    setLoading(false);
    setError("");
    setResult(null);
    setStartedAt(null);
  };

  return { loading, result, error, startedAt, runAnalysis, reset };
};
