'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { useAuth } from '@/lib/auth';
import { dashboardApi, requestsApi } from '@/lib/api';
import { StatCard, PriorityBadge, StatusBadge, LoadingState, Table } from '@/components/ui';
import { formatDateTime, timeAgo } from '@/lib/utils';
import Link from 'next/link';
import { AlertTriangle, FileText, CheckCircle, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import UpdatesSummaryCard from '@/components/updates/UpdatesSummaryCard';

export default function CitizenDashboard() {
  const { user } = useAuth();
  const [data, setData]     = useState<{ requests: unknown[]; stats: Record<string,number> } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      dashboardApi.citizen(user.user_id)
        .then(r => setData(r.data))
        .catch(() => toast.error('Failed to load dashboard'))
        .finally(() => setLoading(false));
    }
  }, [user]);

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  const stats = data?.stats || {};
  const requests = (data?.requests || []) as Array<Record<string,unknown>>;

  return (
    <DashboardLayout>
      <div className="max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Welcome, {user?.full_name} 👋</h1>
          <p className="text-gray-500 text-sm mt-1">Your emergency request dashboard</p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
          <StatCard label="Total Requests" value={stats.total || 0} icon={<FileText className="w-8 h-8"/>} color="blue" />
          <StatCard label="Pending"  value={stats.pending  || 0} icon={<Clock className="w-8 h-8"/>}       color="orange" />
          <StatCard label="Resolved" value={stats.resolved || 0} icon={<CheckCircle className="w-8 h-8"/>} color="green" />
        </div>

        {/* Quick actions */}
        <div className="card mb-6">
          <h2 className="font-semibold text-gray-800 mb-3">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            <Link href="/requests/submit" className="btn-primary flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Submit Emergency Request
            </Link>
            <Link href="/requests" className="btn-ghost flex items-center gap-2">
              <FileText className="w-4 h-4" /> View All My Requests
            </Link>
          </div>
        </div>

        <UpdatesSummaryCard />

        {/* Recent requests */}
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-4">My Recent Requests</h2>
          {requests.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <p className="text-4xl mb-2">📋</p>
              <p>No requests yet. Submit your first emergency request.</p>
              <Link href="/requests/submit" className="btn-primary mt-4 inline-block">Submit Request</Link>
            </div>
          ) : (
            <Table headers={['Type', 'Priority', 'Status', 'Location', 'Time', 'Assignments']}>
              {requests.map((r) => (
                <tr key={r.request_id as string} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.request_type as string}</td>
                  <td className="px-4 py-3"><PriorityBadge priority={r.priority as string} /></td>
                  <td className="px-4 py-3"><StatusBadge status={r.status as string} /></td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{r.area_name as string}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{timeAgo(r.request_time as string)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                      {r.assignment_count as number}
                    </span>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
