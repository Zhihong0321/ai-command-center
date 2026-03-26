'use client';
import { useEffect, useState } from 'react';
import { apiClient, Task } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

const STATUS_CLASSES: Record<string, string> = {
  OPEN: 'badge-open', CLAIMED: 'badge-claimed', IN_PROGRESS: 'badge-in_progress',
  REVIEW: 'badge-review', DONE: 'badge-done', BLOCKED: 'badge-blocked',
};

const PRIORITY_COLORS: Record<string, string> = {
  LOW: 'text-gray-500', NORMAL: 'text-gray-400',
  HIGH: 'text-amber-400', CRITICAL: 'text-red-400',
};

const STATUSES = ['', 'OPEN', 'CLAIMED', 'IN_PROGRESS', 'REVIEW', 'DONE', 'BLOCKED'];

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [repos, setRepos] = useState<{ name: string }[]>([]);
  const [form, setForm] = useState({ repo_name: '', title: '', description: '', priority: 'NORMAL' });
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    const [t, r] = await Promise.all([
      apiClient.getTasks(filter ? { status: filter } : {}),
      apiClient.getRepos(),
    ]);
    setTasks(t);
    setRepos(r);
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter]);

  const createTask = async () => {
    if (!form.repo_name || !form.title) return;
    setCreating(true);
    try {
      await apiClient.createTask(form);
      setShowCreate(false);
      setForm({ repo_name: '', title: '', description: '', priority: 'NORMAL' });
      await load();
    } finally { setCreating(false); }
  };

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Task Board</h1>
          <p className="text-gray-500 text-sm mt-1">{tasks.length} tasks</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-sm font-medium transition-colors"
        >
          + New Task
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {STATUSES.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === s
                ? 'border-violet-500 bg-violet-600/30 text-violet-200'
                : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-500'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Create Task Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-gray-100">Create Task</h2>
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
              value={form.repo_name}
              onChange={e => setForm(f => ({ ...f, repo_name: e.target.value }))}
            >
              <option value="">Select Repo…</option>
              {repos.map(r => <option key={r.name} value={r.name}>{r.name}</option>)}
            </select>
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
              placeholder="Task title"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            />
            <textarea
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200 resize-none"
              rows={3}
              placeholder="Description (optional)"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            />
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
              value={form.priority}
              onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
            >
              {['LOW', 'NORMAL', 'HIGH', 'CRITICAL'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div className="flex gap-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">Cancel</button>
              <button onClick={createTask} disabled={creating} className="flex-1 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-sm font-medium transition-colors">
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Task List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading tasks…</div>
      ) : tasks.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">No tasks found.</div>
      ) : (
        <div className="glass divide-y divide-gray-800">
          {tasks.map(t => (
            <div key={t.id} className="p-4 hover:bg-white/5 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASSES[t.status] || ''}`}>
                      {t.status.replace('_', ' ')}
                    </span>
                    <span className={`text-xs font-semibold ${PRIORITY_COLORS[t.priority]}`}>
                      {t.priority}
                    </span>
                    <Link href={`/repos/${t.repo.name}`} className="text-xs text-cyan-400 hover:text-cyan-300">
                      {t.repo.display_name || t.repo.name}
                    </Link>
                  </div>
                  <div className="mt-1 font-medium text-gray-100">{t.title}</div>
                  {t.description && <div className="text-xs text-gray-500 mt-0.5 truncate">{t.description}</div>}
                  {t.assignee && (
                    <div className="text-xs text-gray-400 mt-1">
                      Assigned to <span className="text-violet-300">{t.assignee.name}</span>
                    </div>
                  )}
                </div>
                <div className="text-xs text-gray-500 whitespace-nowrap">
                  {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
                </div>
              </div>
              {t.github_pr_url && (
                <a href={t.github_pr_url} target="_blank" className="text-xs text-blue-400 hover:underline mt-1 inline-block">
                  🔗 PR
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
