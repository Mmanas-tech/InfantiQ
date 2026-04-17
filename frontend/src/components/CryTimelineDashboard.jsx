import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { fetchTimeline } from "../api/analyzeApi";

const CLASS_COLORS = {
  belly_pain: "#ef4444",
  burping: "#06b6d4",
  discomfort: "#d946ef",
  hungry: "#f59e0b",
  tired: "#3b82f6",
};

const CLASSES = ["belly_pain", "burping", "discomfort", "hungry", "tired"];

const toLabel = (key) => key.replaceAll("_", " ");

const CryTimelineDashboard = ({ babyId }) => {
  const [days, setDays] = useState(7);
  const [timeline, setTimeline] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!babyId) {
      setTimeline(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError("");

    fetchTimeline(babyId, days)
      .then((data) => {
        if (!active) return;
        setTimeline(data);
      })
      .catch(() => {
        if (!active) return;
        setError("Unable to load timeline yet. Analyze a few cries first.");
        setTimeline(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [babyId, days]);

  const maxHourly = useMemo(() => {
    if (!timeline?.time_vs_type?.length) return 1;
    return Math.max(...timeline.time_vs_type.map((point) => point.total || 0), 1);
  }, [timeline]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-3xl border border-white/15 bg-black/20 p-6"
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold">Cry Timeline Dashboard</h2>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm"
        >
          <option value={3}>Last 3 Days</option>
          <option value={7}>Last 7 Days</option>
          <option value={14}>Last 14 Days</option>
        </select>
      </div>

      {loading && <p className="text-sm text-white/70">Building timeline...</p>}
      {!loading && error && <p className="text-sm text-amber-300">{error}</p>}

      {!loading && timeline && (
        <div className="space-y-6">
          <p className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/85">
            {timeline.cycle_hint || "Not enough events yet to infer a cycle."}
          </p>

          <div>
            <p className="mb-2 text-sm text-white/75">Time vs cry type (hourly frequency)</p>
            <div className="grid grid-cols-12 gap-2 md:grid-cols-24">
              {timeline.time_vs_type.map((point) => (
                <div key={point.hour} className="flex flex-col items-center">
                  <div className="flex h-28 w-full items-end gap-[2px] rounded-md bg-white/5 px-1 pb-1">
                    {CLASSES.map((cls) => {
                      const h = Math.max(2, ((point[cls] || 0) / maxHourly) * 100);
                      return (
                        <div
                          key={`${point.hour}-${cls}`}
                          title={`${toLabel(cls)}: ${point[cls] || 0}`}
                          style={{ height: `${h}%`, background: CLASS_COLORS[cls] }}
                          className="w-full rounded-sm"
                        />
                      );
                    })}
                  </div>
                  <span className="mt-1 text-[10px] text-white/60">{String(point.hour).padStart(2, "0")}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm text-white/75">Frequency trends by day</p>
            <div className="space-y-2">
              {timeline.frequency_trends?.length ? (
                timeline.frequency_trends.map((day) => (
                  <div key={day.date} className="rounded-lg border border-white/10 bg-white/5 p-2">
                    <div className="mb-2 flex justify-between text-xs text-white/70">
                      <span>{day.date}</span>
                      <span>{day.total} events</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/10">
                      <div className="flex h-full w-full">
                        {CLASSES.map((cls) => {
                          const width = day.total ? ((day[cls] || 0) / day.total) * 100 : 0;
                          return (
                            <div
                              key={`${day.date}-${cls}`}
                              style={{ width: `${width}%`, background: CLASS_COLORS[cls] }}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-white/60">No trend data yet.</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-white/70">
            {CLASSES.map((cls) => (
              <div key={cls} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: CLASS_COLORS[cls] }} />
                <span>{toLabel(cls)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.section>
  );
};

export default CryTimelineDashboard;
