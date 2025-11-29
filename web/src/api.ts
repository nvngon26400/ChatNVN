const isLocal = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const apiUrl = isLocal
  ? (import.meta.env.VITE_API_URL ?? "/api/chat")
  : "/api/chat";

const wsUrl = isLocal
  ? (import.meta.env.VITE_WS_URL ?? (
      window.location.protocol === 'https:'
        ? `wss://${window.location.host}/ws/chat`
        : `ws://${window.location.host}/ws/chat`
    ))
  : (
      window.location.protocol === 'https:'
        ? `wss://${window.location.host}/ws/chat`
        : `ws://${window.location.host}/ws/chat`
    );

export const API_URL = apiUrl;
export const WS_URL = wsUrl;


