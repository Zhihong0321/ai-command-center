'use client';
import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || '';

interface Setting {
  key: string;
  value: string;
  description?: string;
  updated_at: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [githubToken, setGithubToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/settings`, {
        headers: { 'X-API-Key': API_KEY }
      });
      setSettings(res.data);
      const ghToken = res.data.find((s: Setting) => s.key === 'github_token');
      if (ghToken) setGithubToken(ghToken.value);
    } catch (e) {
      console.error("Failed to load settings", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveGithubToken = async () => {
    setSaving(true);
    setMessage('');
    try {
      await axios.post(`${API_URL}/api/settings`, {
        key: 'github_token',
        value: githubToken,
        description: 'GitHub Personal Access Token for repository sync'
      }, {
        headers: { 'X-API-Key': API_KEY }
      });
      setMessage('✅ GitHub Token updated successfully.');
      await load();
    } catch (e) {
      setMessage('❌ Failed to update GitHub Token.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gray-100">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure global platform parameters and integrations.</p>
      </div>

      <div className="glass p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
            <span className="text-2xl">🐙</span> GitHub Connection
          </h2>
          <p className="text-sm text-gray-400 mb-4">
            Provide a GitHub Personal Access Token (PAT) with <code>repo</code> scope to enable repository synchronization, commit tracking, and PR status monitoring.
          </p>
          
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">GitHub Personal Access Token</label>
              <input
                type="password"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 font-mono"
                placeholder="ghp_xxxxxxxxxxxx"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-600 italic">
                {githubToken ? "Token is configured. You can update it above." : "No token configured. Sync will use backend environment variable if present."}
              </p>
              <button
                onClick={saveGithubToken}
                disabled={saving || !githubToken}
                className="px-6 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-all"
              >
                {saving ? 'Saving...' : 'Save Token'}
              </button>
            </div>
            {message && (
              <div className={`text-sm py-2 px-3 rounded-md ${message.startsWith('✅') ? 'bg-green-600/10 text-green-400 border border-green-600/20' : 'bg-red-600/10 text-red-400 border border-red-600/20'}`}>
                {message}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="glass p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
            <span className="text-2xl">📚</span> Developer Resources
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <a 
              href={`${API_URL}/docs`} 
              target="_blank" 
              className="group p-4 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all"
            >
              <div className="font-medium text-gray-200 group-hover:text-violet-400 transition-colors">API Documentation (Swagger)</div>
              <p className="text-xs text-gray-500 mt-1">Interactive API explorer for testing and development.</p>
            </a>
            <a 
              href={`${API_URL}/redoc`} 
              target="_blank" 
              className="group p-4 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all"
            >
              <div className="font-medium text-gray-200 group-hover:text-violet-400 transition-colors">ReDoc Documentation</div>
              <p className="text-xs text-gray-500 mt-1">Clean, documentation-focused API reference.</p>
            </a>
          </div>
        </div>
      </div>

      <div className="glass p-6">
        <h2 className="text-xl font-semibold text-gray-100 mb-4 flex items-center gap-2">
          <span className="text-2xl">📋</span> System Version
        </h2>
        <div className="text-sm text-gray-500">
          AI Command Center v1.0.0 — Build Beta
        </div>
      </div>
    </div>
  );
}
