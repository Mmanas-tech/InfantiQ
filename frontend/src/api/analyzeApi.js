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

export const healthCheck = async () => {
  const { data } = await api.get("/health");
  return data;
};
