'use client';
import { useEffect, useState } from 'react';
import { apiClient, Repo } from '@/lib/api';
import Link from 'next/link';

export default function ReposPage() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getRepos().then(r => { setRepos(r); setLoading(false); });
  }, []);

  const CATEGORY_COLORS: Record<string, string> = {
    ai: 'bg-violet-600/20 text-violet-300', web: 'bg-blue-600/20 text-blue-300',
    api: 'bg-cyan-600/20 text-cyan-300', game: 'bg-amber-600/20 text-amber-300',
    general: 'bg-gray-700 text-gray-300',
  };

  return (
    <div className="space-y-6 fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gray-100">Repositories</h1>
        <p className="text-gray-500 text-sm mt-1">{repos.length} repos registered</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : repos.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">
          <p>No repos registered yet.</p>
          <p className="text-xs mt-2 font-mono text-gray-600">POST /api/repos with admin key to add repos</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {repos.map(r => (
            <Link key={r.id} href={`/repos/${r.name}`} className="glass p-5 hover:bg-white/5 transition-colors space-y-3 block">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-gray-100">{r.display_name || r.name}</div>
                  <div className="text-xs text-gray-500 font-mono">{r.name}</div>
                </div>
                {r.category && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[r.category.toLowerCase()] || CATEGORY_COLORS.general}`}>
                    {r.category}
                  </span>
                )}
              </div>
              {r.description && <p className="text-sm text-gray-400 line-clamp-2">{r.description}</p>}
              <div className="flex items-center gap-3 text-xs">
                {r.github_url && (
                  <a href={r.github_url} target="_blank" onClick={e => e.stopPropagation()}
                    className="text-blue-400 hover:text-blue-300 flex items-center gap-1">
                    GitHub ↗
                  </a>
                )}
                {r.railway_url && (
                  <a href={r.railway_url} target="_blank" onClick={e => e.stopPropagation()}
                    className="text-green-400 hover:text-green-300 flex items-center gap-1">
                    Railway ↗
                  </a>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
