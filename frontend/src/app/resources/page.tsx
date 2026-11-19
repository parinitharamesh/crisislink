'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { resourcesApi, orgsApi } from '@/lib/api';
import { PageHeader, StatusBadge, LoadingState, Table } from '@/components/ui';
import toast from 'react-hot-toast';

export default function ResourcesPage() {
  const [resources, setResources] = useState<Array<Record<string,unknown>>>([]);
  const [rtypes,    setRtypes]    = useState<Array<Record<string,unknown>>>([]);
  const [orgs,      setOrgs]      = useState<Array<Record<string,unknown>>>([]);
  const [locations, setLocations] = useState<Array<Record<string,unknown>>>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [filter,    setFilter]    = useState('');

  const [form, setForm] = useState({
    resource_name: '', type_id: '', quantity: 1, unit: 'units',
    location_id: '', org_id: '', description: ''
  });

  const load = () =>
    resourcesApi.getAll(filter ? { status: filter } : undefined)
      .then(r => setResources(r.data.resources))
      .catch(() => toast.error('Failed to load resources'))
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
    Promise.all([resourcesApi.getTypes(), orgsApi.getAll(), orgsApi.locations()])
      .then(([rt, og, lc]) => {
        setRtypes(rt.data.resource_types);
        setOrgs(og.data.organizations);
        setLocations(lc.data.locations);
      });
  }, [filter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await resourcesApi.create({
        ...form,
        type_id: parseInt(form.type_id), quantity: parseInt(String(form.quantity)),
        location_id: parseInt(form.location_id), org_id: parseInt(form.org_id)
      });
      toast.success('Resource added');
      setShowForm(false);
      load();
    } catch { toast.error('Failed to add resource'); }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="Resource Management"
        subtitle="Track all available disaster response resources"
        action={<button onClick={() => setShowForm(s => !s)} className="btn-primary">{showForm ? 'Cancel' : '+ Add Resource'}</button>}
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-6 grid grid-cols-2 gap-4">
          <div>
            <label className="label">Resource Name *</label>
            <input className="input" required value={form.resource_name}
              onChange={e => setForm(f => ({ ...f, resource_name: e.target.value }))} />
          </div>
          <div>
            <label className="label">Resource Type *</label>
            <select className="input" required value={form.type_id}
              onChange={e => setForm(f => ({ ...f, type_id: e.target.value }))}>
              <option value="">-- Select --</option>
              {rtypes.map(rt => <option key={rt.type_id as number} value={rt.type_id as number}>{rt.type_name as string}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Quantity *</label>
            <input type="number" min={0} className="input" required value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
          </div>
          <div>
            <label className="label">Unit</label>
            <input className="input" placeholder="units / kits / vehicles" value={form.unit}
              onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} />
          </div>
          <div>
            <label className="label">Location *</label>
            <select className="input" required value={form.location_id}
              onChange={e => setForm(f => ({ ...f, location_id: e.target.value }))}>
              <option value="">-- Select --</option>
              {locations.map(l => <option key={l.location_id as number} value={l.location_id as number}>{l.area_name as string}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Organization *</label>
            <select className="input" required value={form.org_id}
              onChange={e => setForm(f => ({ ...f, org_id: e.target.value }))}>
              <option value="">-- Select --</option>
              {orgs.map(o => <option key={o.org_id as number} value={o.org_id as number}>{o.org_name as string}</option>)}
            </select>
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="btn-primary">Add Resource</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      <div className="flex gap-2 mb-4 flex-wrap">
        {['','AVAILABLE','DEPLOYED','EXHAUSTED','MAINTENANCE'].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              filter === s ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}>{s || 'All'}</button>
        ))}
      </div>

      <Table
        headers={['Name','Type','Quantity','Unit','Status','Location','Organization']}
        empty={resources.length === 0}
      >
        {resources.map((r) => (
          <tr key={r.resource_id as number} className="hover:bg-gray-50">
            <td className="px-4 py-3 font-medium">{r.resource_name as string}</td>
            <td className="px-4 py-3 text-sm text-gray-600">{r.type_name as string}</td>
            <td className="px-4 py-3 font-semibold">{r.quantity as number}</td>
            <td className="px-4 py-3 text-xs text-gray-500">{r.unit as string}</td>
            <td className="px-4 py-3"><StatusBadge status={r.status as string} /></td>
            <td className="px-4 py-3 text-xs text-gray-600">{r.area_name as string}</td>
            <td className="px-4 py-3 text-xs text-gray-600">{r.org_name as string}</td>
          </tr>
        ))}
      </Table>
    </DashboardLayout>
  );
}
