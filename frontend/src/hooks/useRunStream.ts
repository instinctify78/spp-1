import { useEffect, useRef, useState } from "react";

interface TokenMessage {
  type: "token";
  token: string;
  step: number;
  elapsed_ms: number;
}

interface DoneMessage {
  type: "done";
}

type StreamMessage = TokenMessage | DoneMessage | { type: "ping" };

export function useRunStream(runId: number, active: boolean) {
  const [tokens, setTokens] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!active || done) return;

    // Build WebSocket URL — replace http(s) with ws(s) from the API base
    const apiBase = import.meta.env.VITE_API_URL ?? "";
    const wsBase = apiBase
      ? apiBase.replace(/^https?/, (s) => (s === "https" ? "wss" : "ws"))
      : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

    const ws = new WebSocket(`${wsBase}/ws/runs/${runId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as StreamMessage;
      if (msg.type === "token") {
        setTokens((prev) => [...prev, msg.token]);
      } else if (msg.type === "done") {
        setDone(true);
        ws.close();
      }
    };

    ws.onerror = () => setDone(true);

    return () => {
      ws.close();
    };
  }, [runId, active, done]);

  const text = tokens.join("");
  return { text, tokens, done };
}
