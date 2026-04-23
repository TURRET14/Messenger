import { useEffect, useRef } from "react";
import { getWebSocketRoot } from "../api/client";

export type MessageWebSocketSuffix =
  | "/messages/post"
  | "/messages/put"
  | "/messages/delete"
  | "/messages/read";

export function useMsgWebSocket(
  chatId: number | null,
  parentMessageId: number | null,
  suffix: MessageWebSocketSuffix,
  onMessage: (ev: MessageEvent) => void,
  enabled = true,
) {
  const q =
    suffix === "/messages/read"
      ? ""
      : parentMessageId != null
        ? `?parent_message_id=${parentMessageId}`
        : "";
  const path = chatId ? `/chats/${chatId}${suffix}${q}` : "";
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    if (!chatId || !enabled) return;
    const root = getWebSocketRoot().replace(/\/$/, "");
    const url = `${root}${path}`;
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
      ws.onmessage = (ev) => cbRef.current(ev);
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
  }, [chatId, path, enabled]);
}
