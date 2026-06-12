import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

interface StatusBarProps {
  className?: string;
}

interface ConnectionStatus {
  platform_health: string;
  active_agents: number;
  ws_connections: number;
  uptime: string;
  last_updated: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({ className }) => {
  const [status, setStatus] = useState<ConnectionStatus>({
    platform_health: 'unknown',
    active_agents: 0,
    ws_connections: 0,
    uptime: '',
    last_updated: '',
  });
  const [expanded, setExpanded] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const pulseData = useCallback(async () => {
    try {
      const [healthRes, agentRes] = await Promise.all([
        api.platformHub.health().catch(() => null),
        api.agents.list(1, 1).catch(() => ({ items: [], total: 0 })),
      ]);

      setStatus((prev) => ({
        platform_health: healthRes?.overall || 'unknown',
        active_agents: (typeof agentRes?.total === 'number' ? agentRes.total : prev.active_agents),
        ws_connections: prev.ws_connections,
        uptime: healthRes?.uptime_seconds
          ? healthRes.uptime_seconds < 60
            ? `${Math.round(healthRes.uptime_seconds)}s`
            : healthRes.uptime_seconds < 3600
            ? `${Math.round(healthRes.uptime_seconds / 60)}m`
            : `${Math.round(healthRes.uptime_seconds / 3600)}h`
          : 'N/A',
        last_updated: new Date().toLocaleTimeString(),
      }));
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    pulseData();
    const interval = setInterval(pulseData, 15000);
    return () => clearInterval(interval);
  }, [pulseData]);

  useEffect(() => {
    const connectWs = () => {
      try {
        const ws = api.ws.connect();
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          // Subscribe to system room
          ws.send(JSON.stringify({ action: 'subscribe', room: 'system' }));
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'platform_health') {
              setStatus((prev) => ({
                ...prev,
                platform_health: msg.payload?.overall || prev.platform_health,
                uptime: msg.payload?.uptime_seconds
                  ? msg.payload.uptime_seconds < 60
                    ? `${Math.round(msg.payload.uptime_seconds)}s`
                    : `${Math.round(msg.payload.uptime_seconds / 60)}h`
                  : prev.uptime,
              }));
            }
            if (msg.type === 'agent_status') {
              setStatus((prev) => ({
                ...prev,
                active_agents: msg.payload?.active_count ?? prev.active_agents,
              }));
            }
          } catch {
            // invalid message
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          // Reconnect after 5s
          setTimeout(connectWs, 5000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        setTimeout(connectWs, 5000);
      }
    };

    connectWs();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const healthColor =
    status.platform_health === 'healthy'
      ? '#10b981'
      : status.platform_health === 'degraded'
      ? '#f59e0b'
      : status.platform_health === 'critical'
      ? '#ef4444'
      : '#9ca3af';

  return (
    <div className={`status-bar ${className || ''}`} onClick={() => setExpanded(!expanded)}>
      <div className="status-bar-main">
        <div className="status-bar-section">
          <span
            className="status-bar-dot"
            style={{ background: wsConnected ? '#10b981' : '#ef4444' }}
          />
          <span className="status-bar-text">{wsConnected ? 'Connected' : 'Offline'}</span>
        </div>

        <div className="status-bar-section">
          <span
            className="status-bar-dot"
            style={{ background: healthColor }}
          />
          <span className="status-bar-text">
            {status.platform_health.charAt(0).toUpperCase() + status.platform_health.slice(1)}
          </span>
        </div>

        <div className="status-bar-section">
          <span className="status-bar-text">
            {status.active_agents} agents
          </span>
        </div>

        <div className="status-bar-section">
          <span className="status-bar-text status-bar-time">
            {status.last_updated || '--:--:--'}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="status-bar-expanded">
          <div className="status-bar-detail">
            <span>Platform Health</span>
            <span style={{ color: healthColor }}>{status.platform_health}</span>
          </div>
          <div className="status-bar-detail">
            <span>Active Agents</span>
            <span>{status.active_agents}</span>
          </div>
          <div className="status-bar-detail">
            <span>Uptime</span>
            <span>{status.uptime}</span>
          </div>
          <div className="status-bar-detail">
            <span>WebSocket</span>
            <span style={{ color: wsConnected ? '#10b981' : '#ef4444' }}>
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};