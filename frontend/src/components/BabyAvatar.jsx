import { motion } from "framer-motion";

const moodMap = {
  belly_pain: { face: "😣", label: "Distressed" },
  burping: { face: "😗", label: "Fussy" },
  discomfort: { face: "😕", label: "Uneasy" },
  hungry: { face: "😢", label: "Hungry" },
  tired: { face: "🥱", label: "Sleepy" },
};

const ringTone = {
  belly_pain: "from-red-500 to-orange-500",
  burping: "from-cyan-500 to-blue-500",
  discomfort: "from-fuchsia-500 to-pink-500",
  hungry: "from-amber-500 to-yellow-500",
  tired: "from-indigo-500 to-sky-500",
};

const BabyAvatar = ({ prediction, confidence = 0 }) => {
  const mood = moodMap[prediction] || { face: "🙂", label: "Calm" };
  const tone = ringTone[prediction] || "from-slate-500 to-slate-700";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-white/15 bg-white/5 p-5"
    >
      <p className="mb-4 text-sm uppercase tracking-wide text-white/70">Interactive Baby Avatar</p>
      <div className="flex items-center gap-4">
        <motion.div
          key={prediction}
          initial={{ scale: 0.85, rotate: -8 }}
          animate={{
            scale: [1, 1.04, 1],
            rotate: [0, 2, -2, 0],
          }}
          transition={{ duration: 1.6, repeat: Infinity }}
          className={`flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br text-5xl shadow-xl ${tone}`}
        >
          {mood.face}
        </motion.div>

        <div className="flex-1">
          <p className="text-xl font-bold">{mood.label}</p>
          <p className="text-sm text-white/70">Current cry signal: {String(prediction || "unknown").replaceAll("_", " ")}</p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
            <motion.div
              className={`h-full bg-gradient-to-r ${tone}`}
              initial={{ width: 0 }}
              animate={{ width: `${Math.round(confidence * 100)}%` }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default BabyAvatar;
