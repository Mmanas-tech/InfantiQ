import { useEffect, useRef } from "react";

const useCaretakerAlerts = ({ result, parentAway }) => {
  const lastAnalysisId = useRef(null);

  useEffect(() => {
    if (!result?.analysis_id || lastAnalysisId.current === result.analysis_id) return;
    lastAnalysisId.current = result.analysis_id;

    const predictionText = String(result.prediction || "baby status").replaceAll("_", " ");
    const confidence = Math.round((Number(result.confidence) || 0) * 100);
    const message = `Baby seems ${predictionText}. Confidence ${confidence} percent.`;

    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    }

    if (!parentAway) return;

    if (!("Notification" in window)) return;
    const notify = () => {
      const title = result.alert?.title || "InfantiQ Alert";
      const body = result.alert?.body || message;
      new Notification(title, { body });
    };

    if (Notification.permission === "granted") {
      notify();
      return;
    }

    if (Notification.permission === "default") {
      Notification.requestPermission().then((permission) => {
        if (permission === "granted") notify();
      });
    }
  }, [parentAway, result]);
};

export default useCaretakerAlerts;
