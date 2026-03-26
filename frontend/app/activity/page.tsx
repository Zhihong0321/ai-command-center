'use client';
import { useEffect, useState, useCallback } from 'react';
import { apiClient, ActivityLog } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

const TYPE_ICONS: Record<string, string> = {
  START: '🚀', PROGRESS: '⚙️', COMPLETE: '✅', BLOCKER: '🚧',
  NOTE: '📝', ERROR: '❌', HANDOFF: '🔄',
};

const TYPES = ['', 'START', 'PROGRESS', 'COMPLETE', 'BLOCKER', 'NOTE', 'ERROR', 'HANDOFF'];

export default function ActivityPage() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    const l = await apiClient.getActivity({ type: typeFilter || undefined, limit: 100 });
    setLogs(l);
    setLoading(false);
  }, [typeFilter]);

  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);

  return (
    <div className="space-y-6 fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gray-100">Activity Feed</h1>
        <p className="text-gray-500 text-sm mt-1">All agent actions across every repo</p>
      </div>

      {/* Type filter */}
      <div className="flex gap-2 flex-wrap">
        {TYPES.map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors flex items-center gap-1 ${
              typeFilter === t
                ? 'border-violet-500 bg-violet-600/30 text-violet-200'
                : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-500'
            }`}
          >
            {t ? <>{TYPE_ICONS[t]} {t}</> : 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : logs.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">No activity yet.</div>
      ) : (
        <div className="glass divide-y divide-gray-800">
          {logs.map(log => (
            <div key={log.id} className="px-4 py-3 flex items-start gap-3 hover:bg-white/5 transition-colors">
              <span className="text-lg mt-0.5">{TYPE_ICONS[log.type] || '•'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-100">{log.message}</div>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 flex-wrap">
                  {log.agent && <span className="text-violet-300">{log.agent.name}</span>}
                  {log.repo && <><span>·</span><span className="text-cyan-300">{log.repo.name}</span></>}
                  {log.task_id && <><span>·</span><span className="text-gray-600 font-mono">task:{log.task_id.slice(0, 8)}</span></>}
                  <span>·</span>
                  <span>{formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}</span>
                </div>
                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <pre className="text-xs text-gray-600 mt-1 bg-gray-900 rounded p-2 overflow-x-auto">
                    {JSON.stringify(log.metadata, null, 2)}
                  </pre>
                )}
              </div>
              <span className={`text-xs font-mono shrink-0 type-${log.type.toLowerCase()}`}>{log.type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
