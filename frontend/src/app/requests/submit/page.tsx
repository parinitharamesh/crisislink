'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { orgsApi, requestsApi, resourcesApi } from '@/lib/api';
import { PageHeader } from '@/components/ui';
import toast from 'react-hot-toast';

export default function SubmitRequestPage() {
  const router = useRouter();
  const [locations, setLocations] = useState<Array<Record<string,unknown>>>([]);
  const [rtypes,    setRtypes]    = useState<Array<Record<string,unknown>>>([]);
  const [incidents, setIncidents] = useState<Array<Record<string,unknown>>>([]);
  const [loading, setLoading]     = useState(false);

  const [form, setForm] = useState({
    request_type: 'RESCUE',
    description: '',
    people_count: 1,
    medical_needed: false,
    priority: 'MEDIUM',
    location_id: '',
    incident_id: '',
    resource_types: [] as Array<{type_id: string; quantity_required: number}>
  });

  useEffect(() => {
    Promise.all([
      orgsApi.locations(),
      resourcesApi.getTypes(),
    ]).then(([lRes, rRes]) => {
      setLocations(lRes.data.locations);
      setRtypes(rRes.data.resource_types);
    }).catch(() => toast.error('Failed to load form data'));
  }, []);

  const toggleResourceType = (typeId: string) => {
    setForm(f => {
      const exists = f.resource_types.find(r => r.type_id === typeId);
      if (exists) return { ...f, resource_types: f.resource_types.filter(r => r.type_id !== typeId) };
      return { ...f, resource_types: [...f.resource_types, { type_id: typeId, quantity_required: 1 }] };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.location_id) { toast.error('Please select a location'); return; }
    if (!form.description.trim()) { toast.error('Please describe the emergency'); return; }
    setLoading(true);
    try {
      await requestsApi.create({
        ...form,
        location_id: parseInt(form.location_id),
        incident_id: form.incident_id ? parseInt(form.incident_id) : null,
        people_count: parseInt(String(form.people_count)),
      });
      toast.success('Emergency request submitted! Help is on the way.');
      router.push('/requests');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Submission failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const TYPES = ['RESCUE','MEDICAL','SHELTER','FOOD','WATER','EVACUATION','OTHER'];
  const PRIORITIES = ['LOW','MEDIUM','HIGH','CRITICAL'];

  return (
    <DashboardLayout>
      <div className="max-w-2xl">
        <PageHeader
          title="Submit Emergency Request"
          subtitle="Fill in the details below. Help will be dispatched as soon as possible."
        />

        <form onSubmit={handleSubmit} className="card space-y-5">
          {/* Request Type */}
          <div>
            <label className="label">Type of Emergency *</label>
            <div className="grid grid-cols-4 gap-2">
              {TYPES.map(t => (
                <button key={t} type="button"
                  onClick={() => setForm(f => ({ ...f, request_type: t }))}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    form.request_type === t
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-gray-300 text-gray-700 hover:border-blue-400'
                  }`}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="label">Describe the Emergency *</label>
            <textarea className="input h-28 resize-none" required
              placeholder="Describe your situation in detail: location, condition, what kind of help is needed…"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* People count */}
            <div>
              <label className="label">Number of People Affected *</label>
              <input type="number" min={1} max={10000} className="input" required
                value={form.people_count}
                onChange={e => setForm(f => ({ ...f, people_count: parseInt(e.target.value) || 1 }))} />
            </div>

            {/* Priority */}
            <div>
              <label className="label">Priority Level</label>
              <select className="input" value={form.priority}
                onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                {PRIORITIES.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>

          {/* Medical needed */}
          <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-100">
            <input type="checkbox" id="medical" className="w-4 h-4 text-red-600"
              checked={form.medical_needed}
              onChange={e => setForm(f => ({ ...f, medical_needed: e.target.checked }))} />
            <label htmlFor="medical" className="text-sm font-medium text-red-700 cursor-pointer">
              🏥 Medical assistance required (injured/sick persons present)
            </label>
          </div>

          {/* Location */}
          <div>
            <label className="label">Your Location *</label>
            <select className="input" required value={form.location_id}
              onChange={e => setForm(f => ({ ...f, location_id: e.target.value }))}>
              <option value="">-- Select your location --</option>
              {locations.map(l => (
                <option key={l.location_id as number} value={l.location_id as number}>
                  {l.area_name as string}, {l.district as string}, {l.state as string}
                </option>
              ))}
            </select>
          </div>

          {/* Resource types needed */}
          <div>
            <label className="label">Resources Needed (optional)</label>
            <div className="grid grid-cols-2 gap-2">
              {rtypes.map(rt => {
                const selected = form.resource_types.find(r => r.type_id === String(rt.type_id));
                return (
                  <label key={rt.type_id as number}
                    className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                      selected ? 'bg-blue-50 border-blue-300 text-blue-800' : 'border-gray-200 hover:border-gray-300'
                    }`}>
                    <input type="checkbox" className="w-3.5 h-3.5"
                      checked={!!selected}
                      onChange={() => toggleResourceType(String(rt.type_id))} />
                    {rt.type_name as string}
                  </label>
                );
              })}
            </div>
          </div>

          <button type="submit" disabled={loading}
            className="btn-primary w-full py-3 text-base flex items-center justify-center gap-2">
            {loading
              ? <><span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Submitting…</>
              : '🆘 Submit Emergency Request'
            }
          </button>
        </form>
      </div>
    </DashboardLayout>
  );
}
