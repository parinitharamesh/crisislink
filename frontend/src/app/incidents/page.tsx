'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { incidentsApi } from '@/lib/api';
import { PageHeader, StatusBadge, LoadingState, Table } from '@/components/ui';
import { formatDate } from '@/lib/utils';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Array<Record<string,unknown>>>([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [locations, setLocations] = useState<Array<Record<string,unknown>>>([]);

  const [form, setForm] = useState({
    incident_type: 'FLOOD', title: '', start_date: '', description: '',
    affected_area: '', severity: 'HIGH', location_id: ''
  });

  useEffect(() => {
    Promise.all([
      incidentsApi.getAll(),
      import('@/lib/api').then(m => m.orgsApi.locations()),
    ]).then(([iRes, lRes]) => {
      setIncidents(iRes.data.incidents);
      setLocations(lRes.data.locations);
    }).catch(() => toast.error('Failed to load incidents'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await incidentsApi.create({ ...form, location_id: parseInt(form.location_id) });
      toast.success('Incident created');
      setShowForm(false);
      const r = await incidentsApi.getAll();
      setIncidents(r.data.incidents);
    } catch { toast.error('Failed to create incident'); }
  };

  const updateStatus = async (id: number, status: string) => {
    try {
      await incidentsApi.update(id, { status });
      toast.success('Incident updated');
      const r = await incidentsApi.getAll();
      setIncidents(r.data.incidents);
    } catch { toast.error('Update failed'); }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  const TYPES = ['FLOOD','FIRE','EARTHQUAKE','CYCLONE','LANDSLIDE','DROUGHT','TSUNAMI','INDUSTRIAL','OTHER'];

  return (
    <DashboardLayout>
      <PageHeader
        title="Incident Management"
        subtitle="Track and manage active disaster incidents"
        action={
          <button onClick={() => setShowForm(s => !s)} className="btn-primary">
            {showForm ? 'Cancel' : '+ New Incident'}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-6 grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label">Incident Title *</label>
            <input className="input" required placeholder="e.g. Kerala Flood 2024"
              value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
          </div>
          <div>
            <label className="label">Incident Type</label>
            <select className="input" value={form.incident_type}
              onChange={e => setForm(f => ({ ...f, incident_type: e.target.value }))}>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Severity</label>
            <select className="input" value={form.severity}
              onChange={e => setForm(f => ({ ...f, severity: e.target.value }))}>
              {['LOW','MEDIUM','HIGH','CRITICAL'].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Start Date *</label>
            <input type="date" className="input" required
              value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
          </div>
          <div>
            <label className="label">Location *</label>
            <select className="input" required value={form.location_id}
              onChange={e => setForm(f => ({ ...f, location_id: e.target.value }))}>
              <option value="">-- Select --</option>
              {locations.map(l => (
                <option key={l.location_id as number} value={l.location_id as number}>
                  {l.area_name as string}, {l.state as string}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <label className="label">Description</label>
            <textarea className="input h-20 resize-none"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="btn-primary">Create Incident</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      <Table
        headers={['Title','Type','Severity','Status','Start Date','Location','Requests','Action']}
        empty={incidents.length === 0}
      >
        {incidents.map((inc) => (
          <tr key={inc.incident_id as number} className="hover:bg-gray-50">
            <td className="px-4 py-3 font-medium max-w-xs truncate">{inc.title as string}</td>
            <td className="px-4 py-3 text-sm text-gray-600">{inc.incident_type as string}</td>
            <td className="px-4 py-3">
              <span className={`badge border ${
                inc.severity === 'CRITICAL' ? 'bg-red-100 text-red-800 border-red-200' :
                inc.severity === 'HIGH' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                'bg-yellow-100 text-yellow-800 border-yellow-200'
              }`}>{inc.severity as string}</span>
            </td>
            <td className="px-4 py-3"><StatusBadge status={inc.status as string} /></td>
            <td className="px-4 py-3 text-sm text-gray-600">{formatDate(inc.start_date as string)}</td>
            <td className="px-4 py-3 text-xs text-gray-500">{inc.area_name as string}</td>
            <td className="px-4 py-3 text-center">
              <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                {(inc.request_count as number) || 0}
              </span>
            </td>
            <td className="px-4 py-3">
              <select className="text-xs border rounded px-2 py-1"
                defaultValue={inc.status as string}
                onChange={e => updateStatus(inc.incident_id as number, e.target.value)}>
                {['ACTIVE','MONITORING','RESOLVED'].map(s => <option key={s}>{s}</option>)}
              </select>
            </td>
          </tr>
        ))}
      </Table>
    </DashboardLayout>
  );
}
