import { motion, useInView } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import ParallaxHero from "../components/ParallaxHero";

const steps = [
  { title: "Record or Upload", icon: "🎙️", text: "Capture a live cry or upload an audio clip in seconds." },
  { title: "AI Analyzes", icon: "🧠", text: "Dual-branch deep learning model evaluates acoustic patterns." },
  { title: "Get Instant Results", icon: "⚡", text: "Receive cry category, confidence, and recommendation immediately." },
];

const stats = [
  { label: "Cry Types Detected", target: 5, suffix: "" },
  { label: "Accuracy", target: 98, suffix: "%" },
  { label: "Analysis Time", target: 3, suffix: "s", prefix: "< " },
];

const Counter = ({ target, suffix = "", prefix = "", start }) => {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!start) return;
    let raf;
    const t0 = performance.now();
    const duration = 1200;

    const run = (t) => {
      const p = Math.min((t - t0) / duration, 1);
      setValue(Math.round(target * p));
      if (p < 1) raf = requestAnimationFrame(run);
    };

    raf = requestAnimationFrame(run);
    return () => cancelAnimationFrame(raf);
  }, [start, target]);

  return (
    <p className="text-2xl font-bold md:text-3xl">
      {prefix}
      {value}
      {suffix}
    </p>
  );
};

const Landing = () => {
  const statRef = useRef(null);
  const inView = useInView(statRef, { once: true, margin: "-80px" });
  const year = useMemo(() => new Date().getFullYear(), []);

  return (
    <div className="min-h-screen bg-transparent text-white">
      <ParallaxHero />

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-10">
        <h2 className="text-center text-3xl font-bold md:text-4xl">How It Works</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {steps.map((step, idx) => (
            <motion.article
              key={step.title}
              initial={{ y: 35, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.12 }}
              whileHover={{ y: -8 }}
              className="rounded-2xl border border-white/15 bg-white/5 p-6 shadow-lg transition-shadow hover:shadow-neon"
            >
              <div className="mb-3 text-3xl">{step.icon}</div>
              <h3 className="text-xl font-bold">{step.title}</h3>
              <p className="mt-2 text-sm text-white/75">{step.text}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section ref={statRef} className="mx-auto mb-20 max-w-6xl px-6">
        <div className="grid gap-4 rounded-2xl border border-white/20 bg-white/5 p-6 md:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <Counter start={inView} target={stat.target} suffix={stat.suffix} prefix={stat.prefix || ""} />
              <p className="mt-1 text-sm text-white/70">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-white/10 bg-black/25 px-6 py-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <p className="font-semibold">InfantiQ</p>
          <p className="text-sm text-white/60">Powered by Deep Learning • {year}</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
