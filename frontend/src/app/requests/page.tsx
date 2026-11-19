'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { requestsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { PriorityBadge, StatusBadge, PageHeader, Table, LoadingState } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function RequestsPage() {
  const { user } = useAuth();
  const [requests, setRequests] = useState<Array<Record<string,unknown>>>([]);
  const [loading, setLoading]   = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const isAdmin = user?.role !== 'CITIZEN';

  const load = () => {
    const params: Record<string,string> = {};
    if (statusFilter) params.status = statusFilter;
    requestsApi.getAll(params)
      .then(r => setRequests(r.data.requests))
      .catch(() => toast.error('Failed to load requests'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const updateStatus = async (id: number, status: string) => {
    try {
      await requestsApi.updateStatus(id, status);
      toast.success('Status updated');
      load();
    } catch { toast.error('Update failed'); }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title={isAdmin ? 'All Emergency Requests' : 'My Requests'}
        subtitle="View and manage emergency requests"
        action={
          user?.role === 'CITIZEN'
            ? <Link href="/requests/submit" className="btn-primary">+ New Request</Link>
            : undefined
        }
      />

      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {['','PENDING','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              statusFilter === s ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}>
            {s || 'All'}
          </button>
        ))}
      </div>

      <Table
        headers={['#','Type','Priority','Status','People','Medical','Location','Time', isAdmin ? 'Requester' : 'Action']}
        empty={requests.length === 0}
      >
        {requests.map((r) => (
          <tr key={r.request_id as number} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-gray-500 text-xs">#{r.request_id as number}</td>
            <td className="px-4 py-3 font-medium">{r.request_type as string}</td>
            <td className="px-4 py-3"><PriorityBadge priority={r.priority as string} /></td>
            <td className="px-4 py-3"><StatusBadge status={r.status as string} /></td>
            <td className="px-4 py-3 text-center">{r.people_count as number}</td>
            <td className="px-4 py-3 text-center">{r.medical_needed ? '🏥 Yes' : '—'}</td>
            <td className="px-4 py-3 text-xs text-gray-600">{r.area_name as string}</td>
            <td className="px-4 py-3 text-xs text-gray-500">{formatDateTime(r.request_time as string)}</td>
            <td className="px-4 py-3">
              {isAdmin ? (
                <div className="flex gap-2">
                  <select className="text-xs border rounded px-2 py-1"
                    defaultValue={r.status as string}
                    onChange={e => updateStatus(r.request_id as number, e.target.value)}>
                    {['PENDING','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED'].map(s =>
                      <option key={s}>{s}</option>
                    )}
                  </select>
                </div>
              ) : (
                <span className="text-xs text-blue-600">{(r.status as string).replace('_',' ')}</span>
              )}
            </td>
          </tr>
        ))}
      </Table>
    </DashboardLayout>
  );
}
