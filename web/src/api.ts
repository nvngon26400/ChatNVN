const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/chat";
const wsUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/chat";

export const API_URL = apiUrl;
export const WS_URL = wsUrl;


