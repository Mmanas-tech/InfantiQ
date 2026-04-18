import axios from "axios";

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api`,
  timeout: 30000,
});

export const analyzeCry = async (audioBlob, filename = "recording.wav") => {
  const formData = new FormData();
  formData.append("audio", audioBlob, filename);
  
  const { data } = await api.post("/analyze", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return data;
};

export const analyzeCryWithContext = async (
  audioBlob,
  filename = "recording.wav",
  context = {}
) => {
  const formData = new FormData();
  formData.append("audio", audioBlob, filename);

  if (context.babyId) formData.append("baby_id", context.babyId);
  if (context.lastFeedingAt) formData.append("last_feeding_at", context.lastFeedingAt);
  if (context.lastSleepAt) formData.append("last_sleep_at", context.lastSleepAt);
  if (typeof context.parentAway === "boolean") formData.append("parent_away", String(context.parentAway));
  if (context.sourceType) formData.append("source_type", context.sourceType);

  const { data } = await api.post("/analyze", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get("/health");
  return data;
};

export const fetchTimeline = async (babyId, days = 7) => {
  const { data } = await api.get("/timeline", {
    params: {
      baby_id: babyId,
      days,
    },
  });
  return data;
};

export const askInsights = async (question, context = {}) => {
  const { data } = await api.post("/insights/ask", {
    question,
    context,
  });
  return data;
};
