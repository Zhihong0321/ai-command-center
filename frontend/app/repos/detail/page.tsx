'use client';
import { useEffect, useState, Suspense } from 'react';
import { apiClient, Repo, Task, ActivityLog } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

const STATUS_CLASSES: Record<string, string> = {
  OPEN: 'badge-open', CLAIMED: 'badge-claimed', IN_PROGRESS: 'badge-in_progress',
  REVIEW: 'badge-review', DONE: 'badge-done', BLOCKED: 'badge-blocked',
};
const TYPE_ICONS: Record<string, string> = {
  START: '🚀', PROGRESS: '⚙️', COMPLETE: '✅', BLOCKER: '🚧', NOTE: '📝', ERROR: '❌', HANDOFF: '🔄',
};

function RepoDetailContent() {
  const searchParams = useSearchParams();
  const name = searchParams.get('name');

  const [repo, setRepo] = useState<Repo | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityLog[]>([]);
  const [commits, setCommits] = useState<Array<{ sha: string; author: string; message: string; url: string; committed_at: string }>>([]);
  const [prs, setPRs] = useState<Array<{ pr_number: number; title: string; status: string; url: string; author: string }>>([]);
  const [tab, setTab] = useState<'tasks' | 'activity' | 'commits' | 'prs'>('tasks');
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (!name) return;
    (async () => {
      const [r, t, a] = await Promise.all([
        apiClient.getRepo(name),
        apiClient.getTasks({ repo: name }),
        apiClient.getActivity({ repo: name, limit: 50 }),
      ]);
      setRepo(r); setTasks(t); setActivity(a);
      try {
        const [c, p] = await Promise.all([apiClient.getCommits(name), apiClient.getPRs(name)]);
        setCommits(c as typeof commits); setPRs(p as typeof prs);
      } catch { /* no commits cached yet */ }
    })();
  }, [name]);

  const sync = async () => {
    if (!name) return;
    setSyncing(true);
    await apiClient.syncRepo(name);
    const [c, p] = await Promise.all([apiClient.getCommits(name), apiClient.getPRs(name)]);
    setCommits(c as typeof commits); setPRs(p as typeof prs);
    setSyncing(false);
  };

  if (!name) return <div className="text-center py-12 text-gray-500">No repository specified.</div>;
  if (!repo) return <div className="text-center py-12 text-gray-500">Loading…</div>;

  const openCount = tasks.filter(t => t.status === 'OPEN').length;
  const activeCount = tasks.filter(t => ['CLAIMED', 'IN_PROGRESS'].includes(t.status)).length;
  const doneCount = tasks.filter(t => t.status === 'DONE').length;

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <Link href="/repos" className="text-xs text-gray-500 hover:text-gray-300 mb-1 inline-block">← Repos</Link>
          <h1 className="text-3xl font-bold text-gray-100">{repo.display_name || repo.name}</h1>
          <div className="text-xs text-gray-500 font-mono mt-0.5">{repo.name}</div>
          {repo.description && <p className="text-sm text-gray-400 mt-2">{repo.description}</p>}
          <div className="flex gap-3 mt-2 text-xs flex-wrap">
            {repo.github_url && <a href={repo.github_url} target="_blank" className="text-blue-400 hover:underline">GitHub ↗</a>}
            {repo.railway_url && <a href={repo.railway_url} target="_blank" className="text-green-400 hover:underline">Railway ↗</a>}
          </div>
          {repo.local_path && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs text-gray-500">📂 Local path:</span>
              <code className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-amber-300 font-mono select-all">{repo.local_path}</code>
            </div>
          )}
        </div>
        <button
          onClick={sync} disabled={syncing}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm transition-colors"
        >
          {syncing ? '⏳ Syncing…' : '🔄 Sync GitHub'}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[{ label: 'Open', val: openCount, color: 'text-blue-400' }, { label: 'Active', val: activeCount, color: 'text-cyan-400' }, { label: 'Done', val: doneCount, color: 'text-green-400' }].map(s => (
          <div key={s.label} className="glass p-4 text-center">
            <div className={`text-2xl font-bold ${s.color}`}>{s.val}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label} tasks</div>
          </div>
        ))}
      </div>

      <div className="flex gap-1 border-b border-gray-800">
        {(['tasks', 'activity', 'commits', 'prs'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${tab === t ? 'border-violet-500 text-violet-300' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            {t} {t === 'tasks' ? `(${tasks.length})` : t === 'commits' ? `(${commits.length})` : t === 'prs' ? `(${prs.length})` : ''}
          </button>
        ))}
      </div>

      {tab === 'tasks' && (
        <div className="glass divide-y divide-gray-800">
          {tasks.length === 0 ? <div className="p-8 text-center text-gray-500">No tasks for this repo yet.</div> : tasks.map(t => (
            <div key={t.id} className="p-4 hover:bg-white/5 transition-colors">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLASSES[t.status] || ''}`}>{t.status.replace('_', ' ')}</span>
                <span className="text-xs text-gray-500">{t.priority}</span>
              </div>
              <div className="font-medium text-gray-100">{t.title}</div>
              {t.assignee && <div className="text-xs text-gray-400 mt-0.5">→ <span className="text-violet-300">{t.assignee.name}</span></div>}
            </div>
          ))}
        </div>
      )}

      {tab === 'activity' && (
        <div className="glass divide-y divide-gray-800">
          {activity.length === 0 ? <div className="p-8 text-center text-gray-500">No activity yet.</div> : activity.map(l => (
            <div key={l.id} className="px-4 py-3 flex items-start gap-3 hover:bg-white/5 transition-colors">
              <span className="text-base">{TYPE_ICONS[l.type] || '•'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-200">{l.message}</div>
                <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
                  {l.agent && <span className="text-violet-300">{l.agent.name}</span>}
                  <span>{formatDistanceToNow(new Date(l.created_at), { addSuffix: true })}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'commits' && (
        <div className="glass divide-y divide-gray-800">
          {commits.length === 0 ? <div className="p-8 text-center text-gray-500">No commits cached. Click "Sync GitHub" to fetch.</div> : commits.map(c => (
            <div key={c.sha} className="px-4 py-3 hover:bg-white/5 transition-colors">
              <a href={c.url} target="_blank" className="text-sm text-gray-100 hover:text-white">{c.message.split('\n')[0]}</a>
              <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
                <span className="font-mono text-cyan-400">{c.sha.slice(0, 7)}</span>
                <span>{c.author}</span>
                {c.committed_at && <span>{formatDistanceToNow(new Date(c.committed_at), { addSuffix: true })}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'prs' && (
        <div className="glass divide-y divide-gray-800">
          {prs.length === 0 ? <div className="p-8 text-center text-gray-500">No PRs cached. Click "Sync GitHub" to fetch.</div> : prs.map(p => (
            <div key={p.pr_number} className="px-4 py-3 flex items-center gap-3 hover:bg-white/5 transition-colors">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${p.status === 'merged' ? 'bg-violet-600/20 text-violet-300' : p.status === 'open' ? 'bg-green-600/20 text-green-300' : 'bg-gray-700 text-gray-400'}`}>
                {p.status}
              </span>
              <div className="flex-1 min-w-0">
                <a href={p.url} target="_blank" className="text-sm text-gray-100 hover:text-white truncate block">
                  #{p.pr_number} {p.title}
                </a>
                <div className="text-xs text-gray-500">by {p.author}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RepoDetailPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-gray-500">Loading details...</div>}>
      <RepoDetailContent />
    </Suspense>
  );
}
