import { useEffect, useRef } from "react";
import { getWebSocketRoot } from "../api/client";

export function useMsgWebSocket(
  chatId: number | null,
  parentMessageId: number | null,
  suffix: "/messages/post" | "/messages/put" | "/messages/delete",
  onMessage: (ev: MessageEvent) => void,
) {
  const q =
    parentMessageId != null ? `?parent_message_id=${parentMessageId}` : "";
  const path = chatId ? `/chats/${chatId}${suffix}${q}` : "";
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    if (!chatId) return;
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
      ws.onmessage = (ev) => cbRef.current(ev);
      ws.onclose = () => {
        ws = null;
        if (!stopped) scheduleReconnect();
      };
      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      stopped = true;
      cleanupTimer();
      ws?.close();
    };
  }, [chatId, path]);
}
