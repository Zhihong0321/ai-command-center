'use client';
import { useEffect, useState, useCallback } from 'react';
import { apiClient, Dashboard } from '@/lib/api';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

const TYPE_ICONS: Record<string, string> = {
  START: '🚀', PROGRESS: '⚙️', COMPLETE: '✅', BLOCKER: '🚧',
  NOTE: '📝', ERROR: '❌', HANDOFF: '🔄',
};

const AGENT_TYPE_ICONS: Record<string, string> = {
  CODEX: '🤖', GEMINI: '✨', MINIMAX: '🧠', CLAUDE: '🟠', CURSOR: '🖱️', HUMAN: '👤', OTHER: '🔵',
};

const STATUS_COLORS: Record<string, string> = {
  IDLE: 'bg-gray-700 text-gray-300', WORKING: 'bg-violet-600/40 text-violet-200',
  PAUSED: 'bg-yellow-600/40 text-yellow-200', OFFLINE: 'bg-gray-800 text-gray-500',
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await apiClient.getDashboard();
      setData(d);
    } catch { /* handle gracefully */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  const sendBroadcast = async () => {
    if (!broadcastMsg.trim()) return;
    setPosting(true);
    try {
      await apiClient.postBroadcast(broadcastMsg);
      setBroadcastMsg('');
      await load();
    } finally { setPosting(false); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-gray-500">
      <div className="text-center">
        <div className="text-4xl mb-3 animate-pulse">⚡</div>
        <div>Connecting to Command Center…</div>
      </div>
    </div>
  );

  if (!data) return (
    <div className="text-center py-20 text-red-400">
      ⚠️ Could not reach the Command Center API. Is the backend running?
    </div>
  );

  return (
    <div className="space-y-8 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent">
          Command Hub
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Last updated {formatDistanceToNow(new Date(data.generated_at), { addSuffix: true })}
        </p>
      </div>

      {/* Active Broadcasts */}
      {data.active_broadcasts.length > 0 && (
        <div className="glass p-4 border-l-4 border-violet-500 space-y-2">
          <div className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-2">📢 Active Broadcasts</div>
          {data.active_broadcasts.map(b => (
            <div key={b.id} className="text-sm text-gray-200">
              {b.message}
              <span className="text-gray-500 ml-2 text-xs">
                • {formatDistanceToNow(new Date(b.created_at), { addSuffix: true })}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Repos" value={data.repos.length} icon="📁" color="cyan" />
        <StatCard label="Active Agents" value={data.active_agents.length} icon="🤖" color="violet" />
        <StatCard
          label="Open Tasks"
          value={data.repos.reduce((s, r) => s + r.tasks.open, 0)}
          icon="📋" color="blue"
        />
        <StatCard
          label="In Progress"
          value={data.repos.reduce((s, r) => s + r.tasks.in_progress, 0)}
          icon="⚙️" color="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Repos */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-lg font-semibold text-gray-200">Repositories</h2>
          {data.repos.length === 0 ? (
            <div className="glass p-6 text-center text-gray-500 text-sm">No repos registered yet. Use the admin API to register repos.</div>
          ) : (
            data.repos.map(r => (
              <Link key={r.id} href={`/repos/${r.name}`} className="glass p-4 flex items-center justify-between hover:bg-white/5 transition-colors block">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-100">{r.display_name || r.name}</div>
                  <div className="text-xs text-gray-500 font-mono">{r.name}</div>
                  {/* Freshness indicators */}
                  <div className="flex gap-3 mt-1.5 text-xs flex-wrap">
                    {r.last_commit_date && (
                      <span className="text-gray-500">
                        📦 commit {formatDistanceToNow(new Date(r.last_commit_date), { addSuffix: true })}
                      </span>
                    )}
                    {r.last_activity_at && (
                      <span className="text-gray-500">
                        ⚡ activity {formatDistanceToNow(new Date(r.last_activity_at), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-3 text-sm shrink-0 ml-4">
                  <span className="text-blue-400">{r.tasks.open} open</span>
                  <span className="text-cyan-400">{r.tasks.in_progress} active</span>
                  <span className="text-green-400">{r.tasks.done} done</span>
                </div>
              </Link>
            ))
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Active Agents */}
          <div>
            <h2 className="text-lg font-semibold text-gray-200 mb-3">Live Agents</h2>
            {data.active_agents.length === 0 ? (
              <div className="glass p-4 text-gray-500 text-sm text-center">No agents online recently</div>
            ) : (
              <div className="space-y-2">
                {data.active_agents.map(a => (
                  <div key={a.id} className="glass p-3 flex items-center gap-3">
                    <span className="text-xl">{AGENT_TYPE_ICONS[a.type] || '🔵'}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-gray-100 truncate">{a.name}</div>
                      <div className="text-xs text-gray-500">{formatDistanceToNow(new Date(a.last_seen), { addSuffix: true })}</div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[a.status]}`}>
                      {a.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Broadcast Box */}
          <div className="glass p-4 space-y-3">
            <div className="text-sm font-semibold text-gray-300">📢 Broadcast to All Agents</div>
            <textarea
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200 resize-none focus:outline-none focus:border-violet-500"
              rows={3}
              placeholder="Give your agents new instructions…"
              value={broadcastMsg}
              onChange={e => setBroadcastMsg(e.target.value)}
            />
            <button
              onClick={sendBroadcast}
              disabled={posting || !broadcastMsg.trim()}
              className="w-full py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {posting ? 'Sending…' : 'Broadcast'}
            </button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-200">Recent Activity</h2>
          <Link href="/activity" className="text-xs text-violet-400 hover:text-violet-300">View all →</Link>
        </div>
        <div className="glass divide-y divide-gray-800">
          {data.recent_activity.slice(0, 10).map(log => (
            <div key={log.id} className="px-4 py-3 flex items-start gap-3 hover:bg-white/5 transition-colors">
              <span className="text-base mt-0.5">{TYPE_ICONS[log.type] || '•'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-200 truncate">{log.message}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  <span className="text-gray-400">{log.agent_name}</span>
                  {log.repo_name && <> · <span>{log.repo_name}</span></>}
                  {' · '}{formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                </div>
              </div>
              <span className={`text-xs font-mono type-${log.type.toLowerCase()}`}>{log.type}</span>
            </div>
          ))}
          {data.recent_activity.length === 0 && (
            <div className="p-6 text-center text-gray-500 text-sm">No activity yet. Agents will report here as they work.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  const colors: Record<string, string> = {
    cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/20',
    violet: 'from-violet-500/20 to-violet-500/5 border-violet-500/20',
    blue: 'from-blue-500/20 to-blue-500/5 border-blue-500/20',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/20',
  };
  return (
    <div className={`glass bg-gradient-to-br ${colors[color]} p-4`}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-gray-100">{value}</div>
      <div className="text-xs text-gray-400 mt-0.5">{label}</div>
    </div>
  );
}
