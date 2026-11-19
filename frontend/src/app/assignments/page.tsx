'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { assignmentsApi, requestsApi, resourcesApi, sheltersApi, inventoryApi } from '@/lib/api';
import { PageHeader, StatusBadge, LoadingState, Table } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Array<Record<string,unknown>>>([]);
  const [requests,    setRequests]    = useState<Array<Record<string,unknown>>>([]);
  const [resources,   setResources]   = useState<Array<Record<string,unknown>>>([]);
  const [shelters,    setShelters]    = useState<Array<Record<string,unknown>>>([]);
  const [loading,     setLoading]     = useState(true);
  const [showForm,    setShowForm]    = useState(false);

  const [form, setForm] = useState({
    request_id: '', resource_id: '', shelter_id: '', quantity: '1', remarks: ''
  });

  const refreshInventory = () =>
    Promise.all([
      resourcesApi.getAll({ status: 'AVAILABLE' }),
      inventoryApi.getAll(),
    ]).then(([rs]) => setResources(rs.data.resources));

  const load = () =>
    assignmentsApi.getAll()
      .then(r => setAssignments(r.data.assignments))
      .catch(() => toast.error('Failed to load assignments'))
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
    Promise.all([requestsApi.getAll({ status: 'PENDING', limit: 100 }), resourcesApi.getAll({ status: 'AVAILABLE' }), sheltersApi.getAll({ status: 'OPEN' })])
      .then(([rq, rs, sh]) => {
        setRequests(rq.data.requests);
        setResources(rs.data.resources);
        setShelters(sh.data.shelters);
      });
  }, []);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.request_id) { toast.error('Select a request'); return; }
    if (!form.resource_id && !form.shelter_id) { toast.error('Select at least a resource or shelter'); return; }

    if (form.resource_id) {
      const selectedResource = resources.find(r => String(r.resource_id) === String(form.resource_id));
      const requestedQty = Number(form.quantity) || 1;
      if (!selectedResource) {
        toast.error('Selected resource is no longer available');
        return;
      }
      if (requestedQty < 1) {
        toast.error('Quantity must be at least 1');
        return;
      }
      if (Number(selectedResource.quantity) < requestedQty) {
        toast.error(`Insufficient stock. Available: ${selectedResource.quantity}, requested: ${requestedQty}`);
        return;
      }
    }

    try {
      await assignmentsApi.create({
        request_id: parseInt(form.request_id),
        resource_id: form.resource_id ? parseInt(form.resource_id) : undefined,
        shelter_id: form.shelter_id ? parseInt(form.shelter_id) : undefined,
        quantity: form.resource_id ? parseInt(form.quantity || '1') : undefined,
        remarks: form.remarks
      });
      toast.success('Assignment created! Inventory updated.');
      setShowForm(false);
      setForm({ request_id: '', resource_id: '', shelter_id: '', quantity: '1', remarks: '' });
      load();
      refreshInventory();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Assignment failed';
      toast.error(msg);
    }
  };

  const updateStatus = async (id: number, status: string) => {
    try {
      await assignmentsApi.updateStatus(id, status);
      toast.success('Status updated'); load();
    } catch { toast.error('Update failed'); }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="Assignment Management"
        subtitle="Assign resources and shelters to emergency requests"
        action={<button onClick={() => setShowForm(s => !s)} className="btn-primary">{showForm ? 'Cancel' : '+ New Assignment'}</button>}
      />

      {showForm && (
        <form onSubmit={handleAssign} className="card mb-6 grid grid-cols-2 gap-4">
          <div>
            <label className="label">Emergency Request *</label>
            <select className="input" required value={form.request_id}
              onChange={e => setForm(f => ({ ...f, request_id: e.target.value }))}>
              <option value="">-- Select pending request --</option>
              {requests.map(r => (
                <option key={r.request_id as number} value={r.request_id as number}>
                  #{r.request_id} – {r.request_type as string} [{r.priority as string}] – {r.requester_name as string}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Resource (optional)</label>
            <select className="input" value={form.resource_id}
              onChange={e => setForm(f => ({ ...f, resource_id: e.target.value }))}>
              <option value="">-- No resource --</option>
              {resources.map(r => (
                <option key={r.resource_id as number} value={r.resource_id as number}>
                  {r.resource_name as string} ({r.quantity as number} {r.unit as string})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Quantity</label>
            <input type="number" min={1} className="input" value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} />
          </div>
          <div>
            <label className="label">Shelter (optional)</label>
            <select className="input" value={form.shelter_id}
              onChange={e => setForm(f => ({ ...f, shelter_id: e.target.value }))}>
              <option value="">-- No shelter --</option>
              {shelters.map(s => (
                <option key={s.shelter_id as number} value={s.shelter_id as number}>
                  {s.shelter_name as string} ({(s.capacity as number) - (s.current_occupancy as number)} spots free)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Remarks</label>
            <input className="input" placeholder="Optional notes"
              value={form.remarks}
              onChange={e => setForm(f => ({ ...f, remarks: e.target.value }))} />
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="btn-primary">Create Assignment</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      <Table
        headers={['#','Request','Priority','Request Status','Resource','Shelter','Assign Status','Time','Update']}
        empty={assignments.length === 0}
      >
        {assignments.map((a) => (
          <tr key={a.assignment_id as number} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-gray-500 text-xs">#{a.assignment_id as number}</td>
            <td className="px-4 py-3 text-xs">
              <span className="font-medium">#{a.request_id as number}</span>
              <span className="text-gray-500 ml-1">{a.request_type as string}</span>
            </td>
            <td className="px-4 py-3">
              <span className={`badge text-xs border ${
                a.priority === 'CRITICAL' ? 'bg-red-100 text-red-800 border-red-200' : 'bg-orange-100 text-orange-800 border-orange-200'
              }`}>{a.priority as string}</span>
            </td>
            <td className="px-4 py-3"><StatusBadge status={a.request_status as string} /></td>
            <td className="px-4 py-3 text-xs text-gray-600">{(a.resource_name as string) || '—'}</td>
            <td className="px-4 py-3 text-xs text-gray-600">{(a.shelter_name as string) || '—'}</td>
            <td className="px-4 py-3"><StatusBadge status={a.status as string} /></td>
            <td className="px-4 py-3 text-xs text-gray-500">{formatDateTime(a.assigned_time as string)}</td>
            <td className="px-4 py-3">
              <select className="text-xs border rounded px-2 py-1"
                defaultValue={a.status as string}
                onChange={e => updateStatus(a.assignment_id as number, e.target.value)}>
                {['PENDING','ACTIVE','COMPLETED','CANCELLED'].map(s => <option key={s}>{s}</option>)}
              </select>
            </td>
          </tr>
        ))}
      </Table>
    </DashboardLayout>
  );
}
