import { useMemo, useState } from "react";
import { askInsights } from "../api/analyzeApi";

const InsightsPanel = ({ analysisResult, babyId }) => {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");

  const context = useMemo(() => {
    if (!analysisResult) {
      return {
        baby_id: babyId,
      };
    }
    return {
      baby_id: babyId,
      prediction: analysisResult.prediction,
      confidence: analysisResult.confidence,
      recommendation: analysisResult.recommendation,
    };
  }, [analysisResult, babyId]);

  const submit = async () => {
    const q = question.trim();
    if (!q) {
      setError("Please enter a question first.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await askInsights(q, context);
      setAnswer(data.answer || "No answer returned.");
    } catch (err) {
      const payload = err?.response?.data;
      const detail = payload?.detail;
      const msg =
        (typeof payload?.detail === "string" && payload.detail) ||
        (typeof payload?.error === "string" && payload.error) ||
        (typeof detail?.detail === "string" && detail.detail) ||
        (typeof detail?.error === "string" && detail.error) ||
        (typeof err?.message === "string" && err.message) ||
        "Could not fetch insights right now.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-3xl border border-white/15 bg-black/25 p-6">
      <h2 className="mb-3 text-2xl font-bold">AI Insights Q&A</h2>
      <p className="mb-4 text-sm text-white/70">
        Ask follow-up questions like feeding timing, soothing strategies, or pattern interpretation.
      </p>

      <div className="space-y-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={4}
          placeholder="Example: My baby was predicted hungry at 2 AM. What routine should I try tonight?"
          className="w-full rounded-xl border border-white/20 bg-black/30 p-3 text-sm text-white outline-none focus:border-indigo-400"
        />

        <button
          type="button"
          onClick={submit}
          disabled={loading}
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-purple-700 px-4 py-2 text-sm font-semibold disabled:opacity-60"
        >
          {loading ? "Thinking..." : "Ask Insights"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}

      {answer && (
        <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/90">
          {answer}
        </div>
      )}
    </section>
  );
};

export default InsightsPanel;
