import { motion, useScroll, useTransform } from "framer-motion";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const words = ["Hear", "What", "Your", "Baby", "Needs"];

const floatingWaves = Array.from({ length: 4 }).map((_, i) => i);

const ParallaxHero = () => {
  const navigate = useNavigate();
  const { scrollY } = useScroll();
  const yBack = useTransform(scrollY, [0, 1200], [0, 120]);
  const yMid = useTransform(scrollY, [0, 1200], [0, 360]);
  const yFront = useTransform(scrollY, [0, 1200], [0, 720]);
  const yStars = useTransform(scrollY, [0, 1200], [0, 60]);

  const [rippling, setRippling] = useState(false);

  const stars = useMemo(
    () =>
      Array.from({ length: 80 }).map((_, i) => ({
        id: i,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        size: `${Math.random() * 2.2 + 0.8}px`,
        opacity: Math.random() * 0.7 + 0.2,
      })),
    []
  );

  const onCtaClick = () => {
    setRippling(true);
    setTimeout(() => navigate("/analyzer"), 300);
  };

  return (
    <section className="relative flex min-h-[92vh] items-center justify-center overflow-hidden px-6 pt-24">
      <motion.div style={{ y: yBack }} className="parallax-layer absolute inset-0">
        <div className="absolute -left-24 top-16 h-80 w-80 rounded-full bg-indigo-700/30 blur-3xl" />
        <div className="absolute right-10 top-40 h-[28rem] w-[28rem] rounded-full bg-purple-600/20 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-blue-600/20 blur-3xl" />
      </motion.div>

      <motion.div style={{ y: yStars }} className="parallax-layer absolute inset-0">
        {stars.map((s) => (
          <span
            key={s.id}
            className="absolute rounded-full bg-white"
            style={{ left: s.left, top: s.top, width: s.size, height: s.size, opacity: s.opacity }}
          />
        ))}
      </motion.div>

      <motion.div style={{ y: yMid }} className="parallax-layer absolute inset-0 opacity-60">
        {floatingWaves.map((wave) => (
          <svg
            key={wave}
            viewBox="0 0 1200 220"
            className="absolute left-0 h-48 w-full"
            style={{ top: `${25 + wave * 14}%` }}
          >
            <path
              d="M0,110 C200,20 380,200 600,110 C820,20 1000,180 1200,110"
              fill="none"
              stroke="rgba(160,150,255,0.5)"
              strokeWidth="2"
              className="[stroke-dasharray:8_12] [animation:waveStroke_4s_ease-in-out_infinite]"
            />
          </svg>
        ))}
      </motion.div>

      <motion.div style={{ y: yFront }} className="parallax-layer relative z-10 mx-auto max-w-5xl text-center">
        <motion.div
          className="mb-8 inline-flex h-20 w-20 items-center justify-center rounded-full border border-white/25 bg-white/10 text-4xl"
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 140, damping: 14 }}
        >
          👶
        </motion.div>

        <motion.h1
          className="text-4xl font-extrabold leading-tight md:text-7xl"
          initial="hidden"
          animate="show"
          variants={{
            hidden: {},
            show: {
              transition: { staggerChildren: 0.15 },
            },
          }}
        >
          {words.map((word) => (
            <motion.span
              key={word}
              className="mr-3 inline-block"
              variants={{ hidden: { y: 24, opacity: 0 }, show: { y: 0, opacity: 1 } }}
            >
              {word}
            </motion.span>
          ))}
        </motion.h1>

        <p className="mx-auto mt-6 max-w-3xl text-lg text-white/80 md:text-xl">
          AI-powered infant cry analysis. Hunger. Pain. Discomfort. Sleepiness. Decoded instantly.
        </p>

        <motion.button
          onClick={onCtaClick}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
          className="relative mt-10 overflow-hidden rounded-full border border-purple-300/50 bg-gradient-to-r from-indigo-600 to-purple-700 px-9 py-4 text-lg font-semibold text-white shadow-neon glow-pulse"
        >
          <span className="relative z-10">Try Analyzer →</span>
          {rippling && (
            <motion.span
              className="absolute inset-0 rounded-full bg-white/30"
              initial={{ scale: 0, opacity: 0.5 }}
              animate={{ scale: 2.2, opacity: 0 }}
              transition={{ duration: 0.3 }}
            />
          )}
        </motion.button>
      </motion.div>
    </section>
  );
};

export default ParallaxHero;
