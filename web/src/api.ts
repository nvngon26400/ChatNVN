// Default to same-origin endpoints when deployed behind FastAPI
const apiUrl = import.meta.env.VITE_API_URL ?? "/api/chat";
const wsUrl = import.meta.env.VITE_WS_URL ?? (
  (typeof window !== 'undefined' && window.location.protocol === 'https:')
    ? `wss://${window.location.host}/ws/chat`
    : `ws://${window.location.host}/ws/chat`
);

export const API_URL = apiUrl;
export const WS_URL = wsUrl;


