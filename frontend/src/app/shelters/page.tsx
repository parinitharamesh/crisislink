'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { sheltersApi, orgsApi } from '@/lib/api';
import { PageHeader, StatusBadge, LoadingState, Table } from '@/components/ui';
import toast from 'react-hot-toast';

export default function SheltersPage() {
  const [shelters,  setShelters]  = useState<Array<Record<string,unknown>>>([]);
  const [orgs,      setOrgs]      = useState<Array<Record<string,unknown>>>([]);
  const [locations, setLocations] = useState<Array<Record<string,unknown>>>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [deltaMap,  setDeltaMap]  = useState<Record<number,number>>({});

  const [form, setForm] = useState({
    shelter_name: '', address: '', capacity: 100,
    has_medical_facility: false, location_id: '', org_id: ''
  });

  const load = () =>
    sheltersApi.getAll()
      .then(r => setShelters(r.data.shelters))
      .catch(() => toast.error('Failed to load shelters'))
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
    Promise.all([orgsApi.getAll(), orgsApi.locations()])
      .then(([og, lc]) => { setOrgs(og.data.organizations); setLocations(lc.data.locations); });
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sheltersApi.create({
        ...form,
        capacity: parseInt(String(form.capacity)),
        location_id: parseInt(form.location_id),
        org_id: parseInt(form.org_id)
      });
      toast.success('Shelter created');
      setShowForm(false); load();
    } catch { toast.error('Failed to create shelter'); }
  };

  const updateOccupancy = async (sid: number, delta: number) => {
    try {
      await sheltersApi.updateOccupancy(sid, delta);
      toast.success('Occupancy updated');
      load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Update failed';
      toast.error(msg);
    }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="Shelter Management"
        subtitle="Manage emergency shelter capacity and occupancy"
        action={<button onClick={() => setShowForm(s => !s)} className="btn-primary">{showForm ? 'Cancel' : '+ Add Shelter'}</button>}
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-6 grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label">Shelter Name *</label>
            <input className="input" required value={form.shelter_name}
              onChange={e => setForm(f => ({ ...f, shelter_name: e.target.value }))} />
          </div>
          <div className="col-span-2">
            <label className="label">Address *</label>
            <input className="input" required value={form.address}
              onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
          </div>
          <div>
            <label className="label">Capacity *</label>
            <input type="number" min={1} className="input" required value={form.capacity}
              onChange={e => setForm(f => ({ ...f, capacity: parseInt(e.target.value) }))} />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input type="checkbox" id="medical" className="w-4 h-4"
              checked={form.has_medical_facility}
              onChange={e => setForm(f => ({ ...f, has_medical_facility: e.target.checked }))} />
            <label htmlFor="medical" className="text-sm font-medium text-gray-700">Has Medical Facility</label>
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
            <button type="submit" className="btn-primary">Create Shelter</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      <Table
        headers={['Name','Capacity','Occupied','Available','Occupancy%','Medical','Status','Location','Update Occupancy']}
        empty={shelters.length === 0}
      >
        {shelters.map((s) => {
          const pct = Math.round(((s.current_occupancy as number) / (s.capacity as number)) * 100);
          return (
            <tr key={s.shelter_id as number} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium">{s.shelter_name as string}</td>
              <td className="px-4 py-3 text-center">{s.capacity as number}</td>
              <td className="px-4 py-3 text-center font-semibold">{s.current_occupancy as number}</td>
              <td className="px-4 py-3 text-center text-green-700 font-medium">{(s.capacity as number) - (s.current_occupancy as number)}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-16 bg-gray-200 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-orange-500' : 'bg-green-500'}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-gray-600">{pct}%</span>
                </div>
              </td>
              <td className="px-4 py-3 text-center">{s.has_medical_facility ? '🏥' : '—'}</td>
              <td className="px-4 py-3"><StatusBadge status={s.status as string} /></td>
              <td className="px-4 py-3 text-xs text-gray-600">{s.area_name as string}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1">
                  <input type="number" className="w-14 text-xs border rounded px-1.5 py-1"
                    placeholder="±"
                    onChange={e => setDeltaMap(m => ({ ...m, [s.shelter_id as number]: parseInt(e.target.value) || 0 }))} />
                  <button className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                    onClick={() => updateOccupancy(s.shelter_id as number, deltaMap[s.shelter_id as number] || 0)}>
                    Update
                  </button>
                </div>
              </td>
            </tr>
          );
        })}
      </Table>
    </DashboardLayout>
  );
}
