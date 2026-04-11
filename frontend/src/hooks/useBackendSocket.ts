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
      cleanupTimer();
      const delay = Math.min(8000, 400 + attempt * 500);
      attempt += 1;
      timer = setTimeout(connect, delay);
    };

    function connect() {
      if (stopped) return;
      cleanupTimer();
      try {
        ws = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
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
        ws?.close();
      };
    }

    connect();

    return () => {
      stopped = true;
      cleanupTimer();
      ws?.close();
    };
  }, [path, enabled]);
}
