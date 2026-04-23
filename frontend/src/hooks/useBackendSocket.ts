import { useEffect, useRef } from "react";
import { getWebSocketRoot } from "../api/client";

/**
 * Подключение к WebSocket API бэкенда. Cookie сессии передаётся браузером автоматически.
 */
export function useBackendSocket(
  path: string,
  enabled: boolean,
  onEvent: () => void,
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled) return;

    const root = getWebSocketRoot().replace(/\/$/, "");
    const url = `${root}${path.startsWith("/") ? path : `/${path}`}`;

    let ws: WebSocket | null = null;
    let stopped = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const cleanupTimer = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const scheduleReconnect = () => {
      if (stopped) return;
      if (attempt >= 6) return;
      cleanupTimer();
      const delay = Math.min(30000, 800 * 2 ** attempt);
      attempt += 1;
      timer = setTimeout(connect, delay);
    };

    function connect() {
      if (stopped) return;
      if (
        ws &&
        (ws.readyState === WebSocket.CONNECTING ||
          ws.readyState === WebSocket.OPEN)
      ) {
        return;
      }
      cleanupTimer();
      try {
        ws = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        if (stopped) {
          ws?.close();
          return;
        }
        attempt = 0;
      };

      ws.onmessage = () => {
        onEventRef.current();
      };

      ws.onclose = () => {
        ws = null;
        if (!stopped) scheduleReconnect();
      };

      ws.onerror = () => {
        if (!stopped && ws && ws.readyState !== WebSocket.CLOSED) {
          ws.close();
        }
      };
    }

    connect();

    return () => {
      stopped = true;
      cleanupTimer();
      if (
        ws &&
        (ws.readyState === WebSocket.CONNECTING ||
          ws.readyState === WebSocket.OPEN)
      ) {
        ws.close();
      }
    };
  }, [path, enabled]);
}
