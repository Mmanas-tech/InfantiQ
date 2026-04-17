import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { healthCheck } from "./api/analyzeApi";
import Analyzer from "./pages/Analyzer";
import Landing from "./pages/Landing";

function App() {
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    let mounted = true;
    const ping = async () => {
      try {
        await healthCheck();
        if (mounted) setBackendOnline(true);
      } catch {
        if (mounted) setBackendOnline(false);
      }
    };

    ping();
    const timer = setInterval(ping, 15000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <div>
      {!backendOnline && (
        <div className="sticky top-0 z-50 border-b border-amber-300/40 bg-amber-300/15 px-4 py-2 text-center text-sm text-amber-100 backdrop-blur">
          Backend offline. You can still explore the UI, but analysis requests may fail.
        </div>
      )}

      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/analyzer" element={<Analyzer />} />
      </Routes>
    </div>
  );
}

export default App;
