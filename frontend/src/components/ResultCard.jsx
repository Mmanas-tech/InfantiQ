import { motion } from "framer-motion";

const palette = {
  hungry: "from-amber-500 to-orange-500",
  belly_pain: "from-red-500 to-rose-500",
  burping: "from-cyan-500 to-blue-500",
  discomfort: "from-purple-500 to-fuchsia-500",
  tired: "from-sky-500 to-blue-500",
};

const formatPct = (value) => `${Math.round(value * 100)}%`;

const ResultCard = ({ result, onReset }) => {
  const tone = palette[result.prediction] || palette.discomfort;

  return (
    <motion.div
      className="rounded-3xl border border-white/15 bg-black/25 p-7"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
    >
      <motion.div
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 150, damping: 12 }}
        className={`mx-auto mb-6 inline-block rounded-full bg-gradient-to-r px-6 py-2 text-2xl font-extrabold uppercase tracking-wide ${tone}`}
      >
        {String(result.prediction).replaceAll("_", " ")}
      </motion.div>

      <div className="mb-5">
        <p className="mb-2 text-sm text-white/70">Confidence</p>
        <div className="h-3 overflow-hidden rounded-full bg-white/10">
          <motion.div
            className={`h-full bg-gradient-to-r ${tone}`}
            initial={{ width: 0 }}
            animate={{ width: `${result.confidence * 100}%` }}
            transition={{ duration: 0.8 }}
          />
        </div>
        <p className="mt-1 text-right text-sm font-medium">{formatPct(result.confidence)}</p>
      </div>

      <div className="space-y-3">
        {Object.entries(result.probabilities).map(([key, value]) => (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-sm capitalize text-white/90">
              <span>{key.replaceAll("_", " ")}</span>
              <span>{formatPct(value)}</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <motion.div
                className={`h-full rounded-full bg-gradient-to-r ${palette[key]}`}
                initial={{ width: 0 }}
                animate={{ width: `${value * 100}%` }}
                transition={{ duration: 0.7 }}
              />
            </div>
          </div>
        ))}
      </div>

      <p className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/85">{result.recommendation}</p>
      {Array.isArray(result.recommendation_context) && result.recommendation_context.length > 0 && (
        <ul className="mt-3 space-y-1 rounded-xl border border-white/10 bg-white/5 p-4 text-xs text-white/75">
          {result.recommendation_context.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      )}

      {result.personalization?.enabled && (
        <p className="mt-3 text-xs text-emerald-300/90">
          Personalized from {result.personalization.history_count} previous events for this baby.
        </p>
      )}
      <p className="mt-3 text-xs text-white/50">Analyzed at {new Date(result.timestamp).toLocaleString()}</p>

      <button
        onClick={onReset}
        className="mt-6 w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 font-semibold hover:bg-white/15"
      >
        Analyze Another
      </button>
    </motion.div>
  );
};

export default ResultCard;
