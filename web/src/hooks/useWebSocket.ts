import { useRef, useCallback, useState } from 'react';

interface WSMessage {
  type: 'token' | 'done' | 'error' | 'thinking';
  content: string;
}

export function useWebSocket(agentId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [streaming, setStreaming] = useState(false);

  const connect = useCallback(
    (onToken: (token: string) => void, onDone: (full: string) => void, onError: (err: string) => void) => {
      if (!agentId) return;

      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${protocol}://${window.location.host}/ws/chat/${agentId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const msg: WSMessage = JSON.parse(event.data);
        switch (msg.type) {
          case 'token':
            onToken(msg.content);
            break;
          case 'done':
            setStreaming(false);
            onDone(msg.content);
            break;
          case 'error':
            setStreaming(false);
            onError(msg.content);
            break;
          case 'thinking':
            setStreaming(true);
            break;
        }
      };

      ws.onerror = () => {
        setStreaming(false);
        onError('WebSocket connection error');
      };

      ws.onclose = () => {
        setStreaming(false);
      };
    },
    [agentId]
  );

  const send = useCallback((content: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content }));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStreaming(false);
  }, []);

  return { connect, send, disconnect, streaming };
}