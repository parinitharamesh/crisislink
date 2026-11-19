'use client';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { incidentsApi, mongoApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { PageHeader, LoadingState, EmptyState, PriorityBadge } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import {
  EmergencyUpdate, IncidentOption, UpdateForm, UpdateFormValues, UpdateStatusBadge, apiErrorMessage,
  UPDATE_TYPES, UPDATE_STATUSES, UPDATE_PRIORITIES,
} from '@/components/updates/shared';
import toast from 'react-hot-toast';

const PAGE_SIZE = 10;

export default function EmergencyUpdatesPage() {
  const { user } = useAuth();
  const canWrite  = user?.role === 'ADMIN' || user?.role === 'COORDINATOR';
  const isAdmin   = user?.role === 'ADMIN';

  const [updates, setUpdates]     = useState<EmergencyUpdate[]>([]);
  const [incidents, setIncidents] = useState<IncidentOption[]>([]);
  const [total, setTotal]         = useState(0);
  const [pages, setPages]         = useState(0);
  const [page, setPage]           = useState(1);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [showForm, setShowForm]   = useState(false);
  const [saving, setSaving]       = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const [filters, setFilters] = useState({ incident_id: '', status: '', priority: '', update_type: '', search: '' });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { page, limit: PAGE_SIZE };
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const res = await mongoApi.getUpdates(params);
      setUpdates(res.data.updates);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load emergency updates'));
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    incidentsApi.getAll({ limit: 100 })
      .then(r => setIncidents(r.data.incidents))
      .catch(() => toast.error('Failed to load incidents list'));
  }, []);

  const setFilter = (k: keyof typeof filters, v: string) => {
    setPage(1);
    setFilters(f => ({ ...f, [k]: v }));
  };

  const handleCreate = async (v: UpdateFormValues) => {
    setSaving(true);
    try {
      await mongoApi.createUpdate({ ...v, incident_id: parseInt(v.incident_id, 10) });
      toast.success('Update created');
      setShowForm(false);
      setPage(1);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to create update'));
    } finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    try {
      await mongoApi.deleteUpdate(id);
      toast.success('Update deleted');
      setConfirmId(null);
      if (updates.length === 1 && page > 1) setPage(p => p - 1); else load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to delete update'));
      setConfirmId(null);
    }
  };

  const incidentTitle = (id: number) => incidents.find(i => i.incident_id === id)?.title;

  return (
    <DashboardLayout>
      <PageHeader
        title="Emergency Updates"
        subtitle="Live situation updates for active incidents (stored in MongoDB)"
        action={canWrite && (
          <button onClick={() => setShowForm(s => !s)} className="btn-primary text-sm">
            {showForm ? 'Cancel' : '+ New Update'}
          </button>
        )}
      />

      {showForm && canWrite && (
        <UpdateForm incidents={incidents} submitLabel="Create Update" submitting={saving}
          onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
      )}

      {/* Filters */}
      <div className="card mb-5 grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="col-span-2 md:col-span-1">
          <label className="label">Incident</label>
          <select className="input" value={filters.incident_id} onChange={e => setFilter('incident_id', e.target.value)}>
            <option value="">All incidents</option>
            {incidents.map(i => <option key={i.incident_id} value={i.incident_id}>#{i.incident_id} – {i.title}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Status</label>
          <select className="input" value={filters.status} onChange={e => setFilter('status', e.target.value)}>
            <option value="">All</option>
            {UPDATE_STATUSES.filter(s => isAdmin || user?.role === 'COORDINATOR' || s !== 'DRAFT').map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Priority</label>
          <select className="input" value={filters.priority} onChange={e => setFilter('priority', e.target.value)}>
            <option value="">All</option>
            {UPDATE_PRIORITIES.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Type</label>
          <select className="input" value={filters.update_type} onChange={e => setFilter('update_type', e.target.value)}>
            <option value="">All</option>
            {UPDATE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
          </select>
        </div>
        <div className="col-span-2 md:col-span-1">
          <label className="label">Search</label>
          <input className="input" placeholder="Title or message…" value={filters.search}
            onChange={e => setFilter('search', e.target.value)} />
        </div>
      </div>

      {/* States */}
      {loading ? <LoadingState /> : error ? (
        <div className="card border-red-200 bg-red-50 text-center py-10">
          <p className="text-red-700 font-medium mb-3">{error}</p>
          <button onClick={load} className="btn-ghost text-sm">Retry</button>
        </div>
      ) : updates.length === 0 ? (
        <div className="card"><EmptyState message="No emergency updates match your filters" /></div>
      ) : (
        <>
          <div className="space-y-3">
            {updates.map(u => (
              <div key={u._id} className="card hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start gap-3 mb-1">
                  <Link href={`/updates/${u._id}`} className="font-semibold text-gray-800 hover:text-blue-600">
                    {u.title}
                  </Link>
                  <div className="flex gap-2 flex-shrink-0">
                    <PriorityBadge priority={u.priority} />
                    <UpdateStatusBadge status={u.status} />
                  </div>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2 mb-2">{u.message}</p>
                <div className="flex flex-wrap justify-between items-center gap-2 text-xs text-gray-500">
                  <span>
                    <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded mr-2">{u.update_type.replace('_', ' ')}</span>
                    Incident #{u.incident_id}{incidentTitle(u.incident_id) ? ` – ${incidentTitle(u.incident_id)}` : ''}
                    {' • '}{u.created_by_name || `User ${u.created_by}`} • {formatDateTime(u.created_at)}
                  </span>
                  <span className="flex gap-3">
                    <Link href={`/updates/${u._id}`} className="text-blue-600 hover:underline">View</Link>
                    {isAdmin && (confirmId === u._id ? (
                      <span className="flex gap-2 items-center">
                        <span className="text-red-700">Delete this update?</span>
                        <button onClick={() => handleDelete(u._id)} className="text-red-600 font-semibold hover:underline">Yes, delete</button>
                        <button onClick={() => setConfirmId(null)} className="text-gray-500 hover:underline">No</button>
                      </span>
                    ) : (
                      <button onClick={() => setConfirmId(u._id)} className="text-red-600 hover:underline">Delete</button>
                    ))}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center mt-5 text-sm text-gray-600">
            <span>{total} update{total === 1 ? '' : 's'} • page {page} of {Math.max(pages, 1)}</span>
            <div className="flex gap-2">
              <button className="btn-ghost text-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <button className="btn-ghost text-sm" disabled={page >= pages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
