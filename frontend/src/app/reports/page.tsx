'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { incidentsApi, mongoApi } from '@/lib/api';
import { PageHeader, LoadingState } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { IncidentOption } from '@/components/updates/shared';
import { useAuth } from '@/lib/auth';

export default function ReportsPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'ADMIN' || user?.role === 'COORDINATOR';
  const isAdmin = user?.role === 'ADMIN';
  const [reports,   setReports]   = useState<Array<Record<string,unknown>>>([]);
  const [analytics, setAnalytics] = useState<Array<Record<string,unknown>>>([]);
  const [updates,   setUpdates]   = useState<Array<Record<string,unknown>>>([]);
  const [incidents, setIncidents] = useState<IncidentOption[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showForm,  setShowForm]  = useState(false);
  const [tab, setTab] = useState<'reports'|'analytics'|'updates'>('reports');
  // Set NEXT_PUBLIC_MONGODB_ENABLED=false in frontend/.env.local to run in MySQL-only demo mode.
  const demoDisabled = process.env.NEXT_PUBLIC_MONGODB_ENABLED === 'false';

  const [form, setForm] = useState({
    incident_id: '', title: '', content: '', severity: 'HIGH',
    deaths: 0, injured: 0, missing: 0, tags: ''
  });

  const load = async () => {
    if (demoDisabled) return;
    setLoading(true);
    setLoadError(null);
    try {
      const [rRes, aRes, uRes] = await Promise.all([
        mongoApi.getReports(),
        mongoApi.analytics(),
        mongoApi.getUpdates({ limit: 20 }),
      ]);
      setReports(rRes.data.reports);
      setAnalytics(aRes.data.analytics);
      setUpdates(uRes.data.updates);
    } catch (err) {
      const response = (err as { response?: { status?: number; data?: { error?: string } } })?.response;
      const message = response?.status === 503
        ? 'MongoDB is currently unavailable'
        : response?.data?.error || 'Could not load reports, updates, and analytics';
      setLoadError(message);
      toast.error(message);
    }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (demoDisabled) return;
    load();
  }, [demoDisabled]);

  useEffect(() => {
    if (demoDisabled) return;
    incidentsApi.getAll({ limit: 100 })
      .then(r => setIncidents(r.data.incidents))
      .catch(() => toast.error('Failed to load incidents list'));
  }, [demoDisabled]);

  const initMongo = async () => {
    if (demoDisabled) return;
    try { await mongoApi.init(); toast.success('MongoDB initialized with seed data'); load(); }
    catch { toast.error('Init failed'); }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (demoDisabled) return;
    try {
      await mongoApi.createReport({
        incident_id: parseInt(form.incident_id),
        title: form.title, content: form.content,
        severity: form.severity,
        casualties: { deaths: form.deaths, injured: form.injured, missing: form.missing },
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean)
      });
      toast.success('Report created'); setShowForm(false); load();
    } catch (err) {
      const message = (err as { response?: { data?: { error?: string } } })?.response?.data?.error;
      toast.error(message || 'Failed to create report');
    }
  };

  if (demoDisabled) {
    return (
      <DashboardLayout>
        <div className="card border-dashed border-amber-300 bg-amber-50">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">MongoDB Reports are disabled for this demo</h1>
          <p className="text-sm text-gray-600">This project is being demonstrated in MySQL-first mode without MongoDB. The core emergency request, incident, resource, shelter, and inventory workflows remain active.</p>
        </div>
      </DashboardLayout>
    );
  }

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="MongoDB – Incident Reports"
        subtitle="Document-oriented reports, situation updates, and aggregation analytics (Unit 4 – NoSQL)"
        action={canWrite && (
          <div className="flex gap-2">
            {isAdmin && <button onClick={initMongo} className="btn-ghost text-sm">Seed Data</button>}
            <button onClick={() => setShowForm(s => !s)} className="btn-primary text-sm">
              {showForm ? 'Cancel' : '+ New Report'}
            </button>
          </div>
        )}
      />

      {loadError && (
        <div className="card border-red-200 bg-red-50 text-red-700 flex items-center justify-between gap-3 mb-5">
          <p className="text-sm">{loadError}</p>
          <button onClick={load} className="btn-ghost text-sm">Retry</button>
        </div>
      )}

      {/* MongoDB explanation box */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5 text-sm text-green-800">
        <p className="font-semibold mb-1">📚 Unit 4 – NoSQL (MongoDB)</p>
        <p>MongoDB stores detailed incident reports as flexible JSON documents. Unlike MySQL, documents can have nested fields
        (casualties object, tags array, resources_deployed array) without a fixed schema.
        This page demonstrates: <strong>INSERT, FIND, UPDATE, DELETE, Filtering, Projection, Sorting, and Aggregation Pipeline</strong>.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-5 border-b border-gray-200">
        {([['reports','📄 Reports'],['analytics','📊 Aggregation'],['updates','📡 Updates']] as const).map(([t, l]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>{l}</button>
        ))}
      </div>

      {showForm && tab === 'reports' && (
        <form onSubmit={handleCreate} className="card mb-6 grid grid-cols-2 gap-4">
          <div>
            <label className="label">Incident *</label>
            <select className="input" required value={form.incident_id}
              onChange={e => setForm(f => ({ ...f, incident_id: e.target.value }))}>
              <option value="">Select incident...</option>
              {incidents.map(i => (
                <option key={i.incident_id} value={i.incident_id}>#{i.incident_id} - {i.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Title *</label>
            <input className="input" required value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
          </div>
          <div className="col-span-2">
            <label className="label">Report Content</label>
            <textarea className="input h-24 resize-none" value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))} />
          </div>
          <div>
            <label className="label">Severity</label>
            <select className="input" value={form.severity}
              onChange={e => setForm(f => ({ ...f, severity: e.target.value }))}>
              {['LOW','MEDIUM','HIGH','CRITICAL'].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Tags (comma-separated)</label>
            <input className="input" placeholder="flood, rescue, medical" value={form.tags}
              onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} />
          </div>
          <div className="col-span-2 grid grid-cols-3 gap-3">
            {(['deaths','injured','missing'] as const).map(k => (
              <div key={k}>
                <label className="label capitalize">{k}</label>
                <input type="number" min={0} className="input" value={form[k]}
                  onChange={e => setForm(f => ({ ...f, [k]: parseInt(e.target.value) || 0 }))} />
              </div>
            ))}
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="btn-primary">Create Report</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      {tab === 'reports' && (
        <div className="space-y-3">
          {reports.length === 0 ? (
            <div className="card text-center py-10 text-gray-400">
              No reports. Click &quot;Seed Data&quot; to populate MongoDB with sample reports.
            </div>
          ) : reports.map((r) => (
            <div key={r._id as string} className="card hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-800">{r.title as string}</h3>
                <span className={`badge border ${
                  r.severity === 'CRITICAL' ? 'bg-red-100 text-red-800 border-red-200' :
                  r.severity === 'HIGH' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                  'bg-yellow-100 text-yellow-800 border-yellow-200'
                }`}>{r.severity as string}</span>
              </div>
              <p className="text-xs text-gray-500 mb-2">
                Incident #{r.incident_id as number} • {formatDateTime(r.report_date as string)}
              </p>
              <div className="flex gap-2 flex-wrap">
                {((r.tags as string[]) || []).map(tag => (
                  <span key={tag} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">#{tag}</span>
                ))}
              </div>
              <div className="text-xs text-gray-500 mt-1 font-mono">_id: {r._id as string}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'analytics' && (
        <div>
          <p className="text-sm text-gray-600 mb-4 bg-gray-50 p-3 rounded-lg font-mono">
            db.incident_reports.aggregate([&#123;$group&#125;, &#123;$project&#125;, &#123;$sort&#125;]) – Aggregation Pipeline
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {analytics.map((a, i) => (
              <div key={i} className="card">
                <h3 className="font-bold text-lg text-gray-800 mb-3">{a.severity as string}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-600">Reports</span><span className="font-semibold">{a.report_count as number}</span></div>
                  <div className="flex justify-between"><span className="text-gray-600">Deaths</span><span className="font-semibold text-red-700">{a.total_deaths as number}</span></div>
                  <div className="flex justify-between"><span className="text-gray-600">Injured</span><span className="font-semibold text-orange-700">{a.total_injured as number}</span></div>
                  <div className="flex justify-between"><span className="text-gray-600">Missing</span><span className="font-semibold text-yellow-700">{a.total_missing as number}</span></div>
                </div>
              </div>
            ))}
          </div>
          {analytics.length === 0 && (
            <div className="card text-center py-10 text-gray-400">No analytics data. Seed MongoDB first.</div>
          )}
        </div>
      )}

      {tab === 'updates' && (
        <div className="space-y-3">
          <div className="flex justify-between items-center text-sm text-gray-600">
            <span>Latest emergency updates (full create / edit / delete is on the Emergency Updates page)</span>
            <Link href="/updates" className="text-blue-600 hover:underline">Open Emergency Updates →</Link>
          </div>
          {updates.length === 0
            ? <div className="card text-center py-10 text-gray-400">No emergency updates.</div>
            : updates.map(u => (
              <Link key={u._id as string} href={`/updates/${u._id as string}`}
                className="card flex justify-between items-start hover:shadow-md transition-shadow">
                <div>
                  <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded mr-2">{(u.update_type as string).replace('_', ' ')}</span>
                  <span className="text-sm font-medium text-gray-800">{u.title as string}</span>
                  <p className="text-sm text-gray-600 mt-1">{u.message as string}</p>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap ml-4">{formatDateTime(u.created_at as string)}</span>
              </Link>
            ))
          }
        </div>
      )}
    </DashboardLayout>
  );
}
