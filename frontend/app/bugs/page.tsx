'use client';
import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || '';

interface BugReport {
  id: string; title: string; severity: string; status: string;
  area?: string; site_url?: string; steps_to_reproduce?: string;
  observed_behavior?: string; expected_behavior?: string; analysis?: string;
  screenshot_url?: string; created_at: string;
  repo?: { id: string; name: string };
  filed_by?: { id: string; name: string; type: string };
  task_id?: string;
}

const SEVERITY_CLASSES: Record<string, string> = {
  LOW: 'bg-gray-700 text-gray-300', MEDIUM: 'bg-amber-600/20 text-amber-300 border border-amber-500/20',
  HIGH: 'bg-orange-600/20 text-orange-300 border border-orange-500/20',
  CRITICAL: 'bg-red-600/30 text-red-300 border border-red-500/30',
};
const STATUS_CLASSES: Record<string, string> = {
  OPEN: 'badge-open', INVESTIGATING: 'badge-claimed', CONFIRMED: 'badge-in_progress',
  FIXED: 'badge-done', WONT_FIX: 'badge-blocked',
};
const STATUSES = ['', 'OPEN', 'INVESTIGATING', 'CONFIRMED', 'FIXED', 'WONT_FIX'];

export default function BugsPage() {
  const [bugs, setBugs] = useState<BugReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<BugReport | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await axios.get(`${API_URL}/api/bugs`, {
      headers: { 'X-API-Key': API_KEY },
      params: filter ? { status: filter } : {},
    });
    setBugs(res.data);
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (bugId: string, status: string) => {
    await axios.patch(`${API_URL}/api/bugs/${bugId}/status`,
      { status }, { headers: { 'X-API-Key': API_KEY } });
    await load();
    if (selected?.id === bugId) {
      const updated = await axios.get(`${API_URL}/api/bugs/${bugId}`, { headers: { 'X-API-Key': API_KEY } });
      setSelected(updated.data);
    }
  };

  return (
    <div className="space-y-6 fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gray-100">Bug Reports</h1>
        <p className="text-gray-500 text-sm mt-1">
          Structured bug reports filed by agents (including browser-testing agents like Openclaw)
        </p>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {STATUSES.map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === s ? 'border-violet-500 bg-violet-600/30 text-violet-200' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-500'
            }`}>
            {s || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : bugs.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">No bug reports found.</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Bug list */}
          <div className="lg:col-span-1 glass divide-y divide-gray-800 h-fit">
            {bugs.map(b => (
              <button key={b.id} onClick={() => setSelected(b)}
                className={`w-full text-left px-4 py-3 hover:bg-white/5 transition-colors ${selected?.id === b.id ? 'bg-white/5' : ''}`}>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_CLASSES[b.severity]}`}>
                    {b.severity}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASSES[b.status] || ''}`}>
                    {b.status}
                  </span>
                </div>
                <div className="text-sm font-medium text-gray-100 text-left line-clamp-2">{b.title}</div>
                <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
                  {b.filed_by && <span className="text-violet-300">{b.filed_by.name}</span>}
                  {b.repo && <span className="text-cyan-300">{b.repo.name}</span>}
                </div>
                <div className="text-xs text-gray-600 mt-0.5">
                  {formatDistanceToNow(new Date(b.created_at), { addSuffix: true })}
                </div>
              </button>
            ))}
          </div>

          {/* Detail panel */}
          {selected ? (
            <div className="lg:col-span-2 glass p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_CLASSES[selected.severity]}`}>
                      {selected.severity}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASSES[selected.status] || ''}`}>
                      {selected.status}
                    </span>
                    {selected.area && <span className="text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">{selected.area}</span>}
                  </div>
                  <h2 className="text-xl font-semibold text-gray-100">{selected.title}</h2>
                  <div className="text-xs text-gray-500 mt-1 flex gap-3">
                    {selected.filed_by && <span>Filed by <span className="text-violet-300">{selected.filed_by.name}</span></span>}
                    {selected.repo && <span>Repo: <span className="text-cyan-300">{selected.repo.name}</span></span>}
                    <span>{formatDistanceToNow(new Date(selected.created_at), { addSuffix: true })}</span>
                  </div>
                </div>
                {/* Status updater */}
                <select
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300"
                  value={selected.status}
                  onChange={e => updateStatus(selected.id, e.target.value)}
                >
                  {['OPEN', 'INVESTIGATING', 'CONFIRMED', 'FIXED', 'WONT_FIX'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {selected.site_url && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-1">🌐 Site URL</div>
                  <a href={selected.site_url} target="_blank" className="text-blue-400 hover:underline text-sm break-all">
                    {selected.site_url}
                  </a>
                </div>
              )}

              {[
                { label: '📋 Steps to Reproduce', value: selected.steps_to_reproduce },
                { label: '👁️ Observed Behavior', value: selected.observed_behavior },
                { label: '✅ Expected Behavior', value: selected.expected_behavior },
                { label: '🔍 Agent Analysis', value: selected.analysis },
              ].filter(f => f.value).map(f => (
                <div key={f.label}>
                  <div className="text-xs font-semibold text-gray-400 mb-1">{f.label}</div>
                  <div className="text-sm text-gray-300 bg-gray-900/60 rounded-lg p-3 whitespace-pre-wrap">{f.value}</div>
                </div>
              ))}

              {selected.screenshot_url && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 mb-1">📸 Screenshot</div>
                  <a href={selected.screenshot_url} target="_blank" className="text-blue-400 hover:underline text-sm">View screenshot ↗</a>
                </div>
              )}
            </div>
          ) : (
            <div className="lg:col-span-2 glass p-12 text-center text-gray-500 flex items-center justify-center">
              Select a bug report to view details
            </div>
          )}
        </div>
      )}
    </div>
  );
}
