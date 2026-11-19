import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('crisislink_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('crisislink_token');
      localStorage.removeItem('crisislink_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login:    (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }),
  register: (data: Record<string, unknown>) =>
    api.post('/api/auth/register', data),
  me: () => api.get('/api/auth/me'),
};

// ── Requests ─────────────────────────────────────────────────────────────────
export const requestsApi = {
  getAll:       (params?: Record<string, unknown>) => api.get('/api/requests', { params }),
  getOne:       (id: number) => api.get(`/api/requests/${id}`),
  create:       (data: Record<string, unknown>) => api.post('/api/requests', data),
  updateStatus: (id: number, status: string)    => api.put(`/api/requests/${id}/status`, { status }),
  stats:        () => api.get('/api/requests/stats/summary'),
};

// ── Incidents ─────────────────────────────────────────────────────────────────
export const incidentsApi = {
  getAll:   (params?: Record<string, unknown>) => api.get('/api/incidents', { params }),
  getOne:   (id: number) => api.get(`/api/incidents/${id}`),
  create:   (data: Record<string, unknown>) => api.post('/api/incidents', data),
  update:   (id: number, data: Record<string, unknown>) => api.put(`/api/incidents/${id}`, data),
  summary:  () => api.get('/api/incidents/summary'),
};

// ── Resources ─────────────────────────────────────────────────────────────────
export const resourcesApi = {
  getAll:       (params?: Record<string, unknown>) => api.get('/api/resources', { params }),
  create:       (data: Record<string, unknown>) => api.post('/api/resources', data),
  update:       (id: number, data: Record<string, unknown>) => api.put(`/api/resources/${id}`, data),
  getTypes:     () => api.get('/api/resources/types'),
  createType:   (data: Record<string, unknown>) => api.post('/api/resources/types', data),
  availability: () => api.get('/api/resources/availability'),
};

// ── Shelters ─────────────────────────────────────────────────────────────────
export const sheltersApi = {
  getAll:           (params?: Record<string, unknown>) => api.get('/api/shelters', { params }),
  create:           (data: Record<string, unknown>) => api.post('/api/shelters', data),
  updateOccupancy:  (id: number, delta: number)     => api.put(`/api/shelters/${id}/occupancy`, { delta }),
  status:           () => api.get('/api/shelters/status'),
};

// ── Assignments ───────────────────────────────────────────────────────────────
export const assignmentsApi = {
  getAll:         (params?: Record<string, unknown>) => api.get('/api/assignments', { params }),
  create:         (data: Record<string, unknown>) => api.post('/api/assignments', data),
  updateStatus:   (id: number, status: string)    => api.put(`/api/assignments/${id}/status`, { status }),
  findResources:  (reqId: number) => api.get(`/api/assignments/find-resources/${reqId}`),
};

// ── Inventory ─────────────────────────────────────────────────────────────────
export const inventoryApi = {
  getAll:   (params?: Record<string, unknown>) => api.get('/api/inventory', { params }),
  create:   (data: Record<string, unknown>) => api.post('/api/inventory', data),
  audit:    () => api.get('/api/inventory/audit'),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardApi = {
  stats:   () => api.get('/api/dashboard/stats'),
  citizen: (uid: number) => api.get(`/api/dashboard/citizen/${uid}`),
};

// ── Organizations ─────────────────────────────────────────────────────────────
export const orgsApi = {
  getAll:     () => api.get('/api/organizations'),
  create:     (data: Record<string, unknown>) => api.post('/api/organizations', data),
  locations:  () => api.get('/api/organizations/locations'),
};

// ── MongoDB ────────────────────────────────────────────────────────────────────
export const mongoApi = {
  getReports:  (params?: Record<string, unknown>) => api.get('/api/mongo/reports', { params }),
  getReport:   (id: string) => api.get(`/api/mongo/reports/${id}`),
  createReport:(data: Record<string, unknown>) => api.post('/api/mongo/reports', data),
  updateReport:(id: string, data: Record<string, unknown>) => api.put(`/api/mongo/reports/${id}`, data),
  deleteReport:(id: string) => api.delete(`/api/mongo/reports/${id}`),
  // Emergency updates (Phase B CRUD)
  getUpdates:      (params?: Record<string, unknown>) => api.get('/api/mongo/updates', { params }),
  getUpdate:       (id: string) => api.get(`/api/mongo/updates/${id}`),
  createUpdate:    (data: Record<string, unknown>) => api.post('/api/mongo/updates', data),
  postUpdate:      (data: Record<string, unknown>) => api.post('/api/mongo/updates', data), // legacy alias
  editUpdate:      (id: string, data: Record<string, unknown>) => api.put(`/api/mongo/updates/${id}`, data),
  deleteUpdate:    (id: string) => api.delete(`/api/mongo/updates/${id}`),
  updatesAnalytics:() => api.get('/api/mongo/updates/analytics'),
  status:          () => api.get('/api/mongo/status'),
  analytics:   () => api.get('/api/mongo/reports/analytics'),
  init:        () => api.post('/api/mongo/init'),
};

// ── Neo4j ─────────────────────────────────────────────────────────────────────
export const neo4jApi = {
  sync:             () => api.post('/api/graph/sync'),
  traceIncident:    (id: number) => api.get(`/api/graph/incident/${id}/trace`),
  requestResources: (id: number) => api.get(`/api/graph/request/${id}/resources`),
  orgsByIncident:   (id: number) => api.get(`/api/graph/incident/${id}/organizations`),
  connectedLocations: () => api.get('/api/graph/locations/connected'),
  stats:            () => api.get('/api/graph/stats'),
};

// ── ChromaDB ─────────────────────────────────────────────────────────────────
export const chromaApi = {
  search:     (q: string, n?: number, category?: string) =>
    api.get('/api/search/search', { params: { q, n, category } }),
  addDoc:     (data: Record<string, unknown>) => api.post('/api/search/documents', data),
  deleteDoc:  (id: string) => api.delete(`/api/search/documents/${id}`),
  stats:      () => api.get('/api/search/stats'),
  init:       () => api.post('/api/search/init'),
};
