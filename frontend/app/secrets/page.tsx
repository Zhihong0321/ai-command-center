'use client';
import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || '';

interface SecretEntry {
  id: string;
  label: string;
  description?: string;
  key_type: string;
  repo?: { name: string; display_name?: string };
  created_at: string;
  last_accessed_at?: string;
  last_accessed_by?: string;
}

const TYPE_ICONS: Record<string, string> = {
  DATABASE: '🗄️', API_KEY: '🔑', SSH: '🖥️', OTHER: '🔐',
};

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ label: '', value: '', unlock_key: '', description: '', key_type: 'DATABASE', repo_name: '' });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // Reveal state
  const [revealId, setRevealId] = useState<string | null>(null);
  const [unlockInput, setUnlockInput] = useState('');
  const [revealResult, setRevealResult] = useState<string | null>(null);
  const [revealError, setRevealError] = useState('');
  const [revealing, setRevealing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await axios.get(`${API_URL}/api/secrets`, { headers: { 'X-API-Key': API_KEY } });
    setSecrets(res.data);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveSecret = async () => {
    if (!form.label || !form.value || !form.unlock_key) return;
    setSaving(true);
    setSaveMsg('');
    try {
      await axios.post(`${API_URL}/api/secrets`, form, { headers: { 'X-API-Key': API_KEY } });
      setSaveMsg('✅ Secret stored. The unlock key was NOT saved. Keep it safe.');
      setForm({ label: '', value: '', unlock_key: '', description: '', key_type: 'DATABASE', repo_name: '' });
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setSaveMsg('❌ ' + (err.response?.data?.detail || 'Failed to save'));
    } finally { setSaving(false); }
  };

  const revealSecret = async () => {
    if (!revealId || !unlockInput) return;
    setRevealing(true);
    setRevealResult(null);
    setRevealError('');
    try {
      const res = await axios.post(`${API_URL}/api/secrets/${revealId}/reveal`,
        { unlock_key: unlockInput }, { headers: { 'X-API-Key': API_KEY } });
      setRevealResult(res.data.value);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setRevealError(err.response?.data?.detail || 'Invalid unlock key.');
    } finally { setRevealing(false); }
  };

  const openReveal = (id: string) => {
    setRevealId(id);
    setUnlockInput('');
    setRevealResult(null);
    setRevealError('');
  };

  const closeReveal = () => {
    setRevealId(null);
    setRevealResult(null);
    setRevealError('');
    setUnlockInput('');
  };

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">🔐 Secrets Vault</h1>
          <p className="text-gray-500 text-sm mt-1">
            Credentials stored encrypted. Unlock key is never stored — agents must ask you for it.
          </p>
        </div>
        <button onClick={() => setShowAdd(v => !v)}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-sm font-medium transition-colors">
          {showAdd ? '✕ Cancel' : '+ Store Secret'}
        </button>
      </div>

      {/* Security notice */}
      <div className="glass border-l-4 border-amber-500 p-4 text-sm text-amber-200 space-y-1">
        <div className="font-semibold">🔒 How this vault works</div>
        <ul className="text-xs text-amber-300/80 space-y-0.5 list-disc list-inside">
          <li>Credentials are encrypted with AES (Fernet) using a key derived from your unlock key + a random salt.</li>
          <li>The unlock key is <strong>never stored</strong> — not in the DB, not in logs, nowhere.</li>
          <li>To grant an agent access: tell them the unlock key verbally or via your preferred secure channel.</li>
          <li>Every successful and failed reveal attempt is logged in the Activity Feed.</li>
          <li>A wrong unlock key returns a 403 — the encrypted data is not exposed.</li>
        </ul>
      </div>

      {/* Add Secret Form */}
      {showAdd && (
        <div className="glass p-5 space-y-4">
          <h2 className="text-lg font-semibold text-gray-100">Store New Secret</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Label *</label>
              <input className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
                placeholder="e.g. Production Postgres DB"
                value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Type</label>
              <select className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
                value={form.key_type} onChange={e => setForm(f => ({ ...f, key_type: e.target.value }))}>
                {['DATABASE', 'API_KEY', 'SSH', 'OTHER'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="md:col-span-2 space-y-1">
              <label className="text-xs text-gray-400">Credential Value * (connection string, key, etc.)</label>
              <textarea className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200 font-mono resize-none"
                rows={3} placeholder="postgresql://user:password@host:5432/db"
                value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-amber-400 font-semibold">Unlock Key * (you will need to give this to agents — it will NOT be saved)</label>
              <input type="password" className="w-full bg-gray-900 border border-amber-600/40 rounded-lg p-2 text-sm text-gray-200"
                placeholder="Choose a strong unlock key"
                value={form.unlock_key} onChange={e => setForm(f => ({ ...f, unlock_key: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Repo (optional)</label>
              <input className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
                placeholder="repo-name"
                value={form.repo_name} onChange={e => setForm(f => ({ ...f, repo_name: e.target.value }))} />
            </div>
            <div className="md:col-span-2 space-y-1">
              <label className="text-xs text-gray-400">Description (what is this key for?)</label>
              <input className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-gray-200"
                placeholder="e.g. Railway Postgres for aiworkfor.me production"
                value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
          </div>
          {saveMsg && <div className={`text-sm ${saveMsg.startsWith('✅') ? 'text-green-400' : 'text-red-400'}`}>{saveMsg}</div>}
          <button onClick={saveSecret} disabled={saving || !form.label || !form.value || !form.unlock_key}
            className="px-6 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors">
            {saving ? 'Encrypting & Saving…' : '🔒 Encrypt & Store'}
          </button>
        </div>
      )}

      {/* Secrets List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading…</div>
      ) : secrets.length === 0 ? (
        <div className="glass p-12 text-center text-gray-500">No secrets stored yet.</div>
      ) : (
        <div className="glass divide-y divide-gray-800">
          {secrets.map(s => (
            <div key={s.id} className="p-4 flex items-center gap-4 hover:bg-white/5 transition-colors">
              <span className="text-2xl">{TYPE_ICONS[s.key_type] || '🔐'}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-100">{s.label}</div>
                {s.description && <div className="text-xs text-gray-500 mt-0.5">{s.description}</div>}
                <div className="flex gap-3 mt-1 text-xs text-gray-600 flex-wrap">
                  <span className="bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{s.key_type}</span>
                  {s.repo && <span className="text-cyan-300">{s.repo.display_name || s.repo.name}</span>}
                  <span>Added {formatDistanceToNow(new Date(s.created_at), { addSuffix: true })}</span>
                  {s.last_accessed_at && (
                    <span className="text-gray-500">
                      Last revealed by <span className="text-violet-300">{s.last_accessed_by}</span> {formatDistanceToNow(new Date(s.last_accessed_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-600 font-mono mt-0.5">ID: {s.id}</div>
              </div>
              <button onClick={() => openReveal(s.id)}
                className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/40 border border-amber-500/30 text-amber-300 rounded-lg text-xs font-medium transition-colors">
                🔓 Reveal
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Reveal Modal */}
      {revealId && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-gray-100">🔓 Reveal Secret</h2>
            <p className="text-sm text-gray-400">
              Enter the unlock key to decrypt this secret. This key was set by the human operator when the secret was stored.
            </p>
            <input type="password"
              className="w-full bg-gray-900 border border-amber-600/40 rounded-lg p-2 text-sm text-gray-200"
              placeholder="Enter unlock key…"
              value={unlockInput}
              onChange={e => setUnlockInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') revealSecret(); }}
              autoFocus />
            {revealError && <div className="text-sm text-red-400">❌ {revealError}</div>}
            {revealResult && (
              <div className="space-y-2">
                <div className="text-xs text-green-400 font-semibold">✅ Decrypted value:</div>
                <div className="bg-gray-900 border border-green-500/30 rounded-lg p-3 font-mono text-sm text-green-300 break-all select-all">
                  {revealResult}
                </div>
                <div className="text-xs text-amber-300">⚠️ Do not save this value to any file or log. Use it directly in your session.</div>
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={closeReveal} className="flex-1 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">
                Close
              </button>
              {!revealResult && (
                <button onClick={revealSecret} disabled={revealing || !unlockInput}
                  className="flex-1 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-sm font-medium transition-colors">
                  {revealing ? 'Decrypting…' : 'Decrypt'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
