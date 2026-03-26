'use client';
import { useEffect, useState, useCallback } from 'react';
import { apiClient, Agent } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

const TYPE_ICONS: Record<string, string> = {
  CODEX: '🤖', GEMINI: '✨', MINIMAX: '🧠', CLAUDE: '🟠', CURSOR: '🖱️', HUMAN: '👤', OTHER: '🔵',
};
const STATUS_CLASSES: Record<string, string> = {
  IDLE: 'badge-idle', WORKING: 'badge-working', PAUSED: 'badge-paused', OFFLINE: 'badge-offline',
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const a = await apiClient.getAgents();
    setAgents(a);
    setLoading(false);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);

  const now = new Date();
  const isOnline = (a: Agent) => a.last_seen && (now.getTime() - new Date(a.last_seen).getTime()) < 15 * 60 * 1000;

  return (
    <div className="space-y-6 fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gray-100">Agents</h1>
        <p className="text-gray-500 text-sm mt-1">{agents.filter(isOnline).length} online · {agents.length} total</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : agents.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">
          <p>No agents registered yet.</p>
          <p className="text-xs mt-2 font-mono text-gray-600">POST /api/agents with admin key to register</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(a => (
            <div key={a.id} className={`glass p-5 space-y-3 ${isOnline(a) ? 'ring-1 ring-violet-500/20' : ''}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{TYPE_ICONS[a.type] || '🔵'}</span>
                  <div>
                    <div className="font-semibold text-gray-100">{a.name}</div>
                    <div className="text-xs text-gray-500">{a.type}</div>
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASSES[a.status] || ''}`}>
                  {a.status}
                </span>
              </div>

              <div className="text-xs text-gray-500 space-y-1">
                <div className="flex justify-between">
                  <span>Last seen</span>
                  <span className={isOnline(a) ? 'text-green-400' : 'text-gray-600'}>
                    {a.last_seen ? formatDistanceToNow(new Date(a.last_seen), { addSuffix: true }) : 'Never'}
                  </span>
                </div>
                {a.current_task_id && (
                  <div className="flex justify-between">
                    <span>Current task</span>
                    <span className="font-mono text-violet-300 text-xs">{a.current_task_id.slice(0, 8)}…</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Registered</span>
                  <span>{formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}</span>
                </div>
              </div>

              {isOnline(a) && (
                <div className="flex items-center gap-1.5 text-xs text-green-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                  Online
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
