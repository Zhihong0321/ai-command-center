import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const API_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || '';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'X-API-Key': API_KEY },
});

export interface Agent {
  id: string; name: string; type: string; status: string;
  current_task_id?: string; last_seen?: string; created_at: string;
}

export interface Repo {
  id: string; name: string; display_name?: string;
  github_url?: string; railway_url?: string; category?: string;
  description?: string; local_path?: string; created_at: string;
}

export interface Task {
  id: string; title: string; description?: string;
  status: string; priority: string;
  repo: { id: string; name: string; display_name?: string };
  creator?: { id: string; name: string; type: string };
  assignee?: { id: string; name: string; type: string };
  github_issue_url?: string; github_pr_url?: string;
  claimed_at?: string; completed_at?: string;
  created_at: string; updated_at?: string;
}

export interface ActivityLog {
  id: string; type: string; message: string;
  metadata?: Record<string, unknown>; created_at: string;
  agent?: { id: string; name: string; type: string };
  repo?: { id: string; name: string };
  task_id?: string;
}

export interface Broadcast {
  id: string; message: string; scope: string;
  is_active: boolean; created_at: string; expires_at?: string;
}

export interface Dashboard {
  active_agents: Array<{ id: string; name: string; type: string; status: string; last_seen: string }>;
  recent_activity: Array<{ id: string; type: string; message: string; created_at: string; agent_name?: string; repo_name?: string }>;
  repos: Array<{ id: string; name: string; display_name?: string; github_url?: string; railway_url?: string; tasks: { open: number; in_progress: number; done: number }; last_synced_at?: string; last_commit_date?: string; last_activity_at?: string }>;
  active_broadcasts: Array<{ id: string; message: string; scope: string; created_at: string }>;
  generated_at: string;
}

export const apiClient = {
  getDashboard: () => api.get<Dashboard>('/api/dashboard').then(r => r.data),
  getAgents: () => api.get<Agent[]>('/api/agents').then(r => r.data),
  getRepos: () => api.get<Repo[]>('/api/repos').then(r => r.data),
  getRepo: (name: string) => api.get<Repo>(`/api/repos/${name}`).then(r => r.data),
  getTasks: (params?: { repo?: string; status?: string; assigned_to?: string }) =>
    api.get<Task[]>('/api/tasks', { params }).then(r => r.data),
  getActivity: (params?: { repo?: string; agent?: string; type?: string; limit?: number }) =>
    api.get<ActivityLog[]>('/api/activity', { params }).then(r => r.data),
  getBroadcasts: () => api.get<Broadcast[]>('/api/broadcasts').then(r => r.data),
  getCommits: (repo: string) => api.get<unknown[]>(`/api/github/commits/${repo}`).then(r => r.data),
  getPRs: (repo: string) => api.get<unknown[]>(`/api/github/prs/${repo}`).then(r => r.data),
  syncRepo: (repo: string) => api.post(`/api/github/sync/${repo}`).then(r => r.data),
  createTask: (data: { repo_name: string; title: string; description?: string; priority?: string }) =>
    api.post<Task>('/api/tasks', data).then(r => r.data),
  postBroadcast: (message: string, scope = 'ALL') =>
    api.post('/api/broadcasts', { message, scope }).then(r => r.data),
};
