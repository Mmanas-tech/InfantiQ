import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

const phases = [
  { key: "receive", label: "Receiving audio...", end: 1200 },
  { key: "extract", label: "Extracting features...", end: 2500 },
  { key: "network", label: "Running neural network...", end: 4000 },
  { key: "final", label: "Finalizing results...", end: 5000 },
];

const LoadingScreen = ({ startedAt }) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let frame;
    const tick = () => {
      setElapsed(Date.now() - startedAt);
      frame = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(frame);
  }, [startedAt]);

  const phase = useMemo(() => phases.find((p) => elapsed < p.end) || phases[phases.length - 1], [elapsed]);

  return (
    <div className="rounded-3xl border border-white/15 bg-black/25 p-8">
      <AnimatePresence mode="wait">
        <motion.div
          key={phase.key}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -14 }}
          transition={{ duration: 0.35 }}
          className="space-y-5"
        >
          <h3 className="text-center text-2xl font-bold">{phase.label}</h3>

          {phase.key === "receive" && <div className="sine-bg h-20 rounded-xl" />}

          {phase.key === "extract" && (
            <div className="grid grid-cols-8 gap-1">
              {Array.from({ length: 64 }).map((_, i) => (
                <motion.span
                  key={i}
                  className="h-5 rounded bg-indigo-400/50"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.018 }}
                />
              ))}
            </div>
          )}

          {phase.key === "network" && (
            <svg viewBox="0 0 400 180" className="h-44 w-full">
              {[40, 90, 140].map((y) => (
                <circle key={`l${y}`} cx="60" cy={y} r="10" fill="rgba(111,196,255,0.85)" />
              ))}
              {[35, 75, 115, 155].map((y) => (
                <circle key={`m${y}`} cx="190" cy={y} r="10" fill="rgba(175,140,255,0.85)" />
              ))}
              {[70, 110].map((y) => (
                <circle key={`r${y}`} cx="330" cy={y} r="12" fill="rgba(255,145,145,0.85)" />
              ))}

              {[[60, 40, 190, 35], [60, 90, 190, 75], [60, 140, 190, 115], [190, 75, 330, 70], [190, 115, 330, 110]].map(
                (line, idx) => (
                  <g key={idx}>
                    <line x1={line[0]} y1={line[1]} x2={line[2]} y2={line[3]} stroke="rgba(255,255,255,0.35)" strokeWidth="2" />
                    <motion.circle
                      cx={line[0]}
                      cy={line[1]}
                      r="3"
                      fill="#fff"
                      animate={{ cx: [line[0], line[2]], cy: [line[1], line[3]] }}
                      transition={{ duration: 0.9, repeat: Infinity, repeatType: "loop", ease: "linear", delay: idx * 0.15 }}
                    />
                  </g>
                )
              )}
            </svg>
          )}

          {phase.key === "final" && (
            <div className="flex justify-center py-3">
              <motion.div
                className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-emerald-300"
                animate={{ rotate: [0, 180, 360], borderRadius: ["50%", "40%", "50%"] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              >
                <motion.span initial={{ opacity: 0 }} animate={{ opacity: elapsed > 4700 ? 1 : 0 }} className="text-2xl">
                  ✓
                </motion.span>
              </motion.div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default LoadingScreen;
