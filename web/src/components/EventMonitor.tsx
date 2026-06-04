import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

interface Event {
  id: string;
  type: string;
  source: string;
  data: Record<string, unknown>;
  timestamp: string;
}

const EventMonitor: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [stats, setStats] = useState<{ total_events: number; listener_count: number; type_counts: Record<string, number> } | null>(null);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const connect = () => {
    try {
      const ws = api.ws.connect();
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setEvents((prev) => [data, ...prev].slice(0, 200));
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
      };

      ws.onerror = () => {
        setConnected(false);
      };
    } catch {}
  };

  const disconnect = () => {
    wsRef.current?.close();
    setConnected(false);
  };

  useEffect(() => {
    loadStats();
    return () => disconnect();
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.events.stats();
      setStats(data);
    } catch {}
  };

  const filteredEvents = filter
    ? events.filter((e) => e.type.includes(filter))
    : events;

  const typeColors: Record<string, string> = {
    'agent.': 'text-blue-600',
    'task.': 'text-purple-600',
    'memory.': 'text-green-600',
    'dream.': 'text-indigo-600',
    'autopilot.': 'text-orange-600',
    'tool.': 'text-red-600',
    'collaboration.': 'text-pink-600',
    'system.': 'text-gray-600',
    'error.': 'text-red-600',
  };

  const getEventColor = (type: string) => {
    for (const [prefix, color] of Object.entries(typeColors)) {
      if (type.startsWith(prefix)) return color;
    }
    return 'text-gray-600';
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Event Monitor</h2>
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-500">{connected ? 'Connected' : 'Disconnected'}</span>
          <button
            onClick={connected ? disconnect : connect}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              connected
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
            }`}
          >
            {connected ? 'Disconnect' : 'Connect WS'}
          </button>
          <button
            onClick={loadStats}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Refresh Stats
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-blue-600">{stats.total_events}</div>
            <div className="text-xs text-gray-500 mt-1">Total Events</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-green-600">{stats.listener_count}</div>
            <div className="text-xs text-gray-500 mt-1">Active Listeners</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-purple-600">{Object.keys(stats.type_counts).length}</div>
            <div className="text-xs text-gray-500 mt-1">Event Types</div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-3">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter events by type (e.g., agent, task)..."
          className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Event Stream */}
      <div
        ref={containerRef}
        className="bg-white rounded-xl border max-h-[500px] overflow-y-auto"
      >
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            {connected ? 'Waiting for events...' : 'Connect to receive real-time events'}
          </div>
        ) : (
          <div className="divide-y">
            {filteredEvents.map((event) => (
              <div key={event.id} className="p-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-mono font-medium ${getEventColor(event.type)}`}>
                    {event.type}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {event.source && (
                  <div className="text-xs text-gray-500 mt-0.5">Source: {event.source}</div>
                )}
                {Object.keys(event.data).length > 0 && (
                  <pre className="mt-1 text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto max-h-24">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventMonitor;