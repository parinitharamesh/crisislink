'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { dashboardApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { StatCard, LoadingState, PriorityBadge, StatusBadge } from '@/components/ui';
import { formatDate } from '@/lib/utils';
import Link from 'next/link';
import UpdatesSummaryCard from '@/components/updates/UpdatesSummaryCard';
import {
  AlertTriangle, Users, Package, Building2,
  Activity, ClipboardList, TrendingUp
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats]   = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.stats()
      .then(r => setStats(r.data))
      .catch(() => toast.error('Failed to load dashboard stats'))
      .finally(() => setLoading(false));
  }, []);

  const dashboardTitle = user?.role === 'ADMIN' ? 'Admin Dashboard' : 'Coordinator Dashboard';

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  const reqStats  = (stats?.request_stats  as Array<Record<string,unknown>>) || [];
  const incidents = (stats?.active_incidents as Array<Record<string,unknown>>) || [];
  const shelterOv = (stats?.shelter_overview as Record<string,number>) || {};
  const resSumm   = (stats?.resource_summary as Array<Record<string,unknown>>) || [];
  const critReqs  = (stats?.critical_requests as Array<Record<string,unknown>>) || [];
  const pending   = stats?.pending_count as number || 0;

  const totalReq  = reqStats.reduce((s: number, r) => s + (r.count as number), 0);
  const resolved  = reqStats.find(r => r.status === 'RESOLVED');

  return (
    <DashboardLayout>
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{dashboardTitle}</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time disaster response overview</p>
        </div>

        {/* Top stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Requests"  value={totalReq}                 icon={<ClipboardList className="w-8 h-8"/>} color="blue" />
          <StatCard label="Pending"         value={pending}                  icon={<AlertTriangle className="w-8 h-8"/>} color="orange"
            sub="Needs immediate action" />
          <StatCard label="Active Incidents" value={incidents.length}        icon={<Activity className="w-8 h-8"/>}     color="red" />
          <StatCard label="Resolved"        value={(resolved?.count as number) || 0} icon={<TrendingUp className="w-8 h-8"/>} color="green" />
        </div>

        {/* Shelter + Resource overview */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Shelter overview */}
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold text-gray-800 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-600" /> Shelter Overview
              </h2>
              <Link href="/shelters" className="text-xs text-blue-600 hover:underline">View all →</Link>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-blue-700">{shelterOv.total_shelters || 0}</p>
                <p className="text-xs text-blue-600">Total Shelters</p>
              </div>
              <div className="bg-green-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-green-700">{shelterOv.open_shelters || 0}</p>
                <p className="text-xs text-green-600">Open</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-gray-700">{shelterOv.total_capacity || 0}</p>
                <p className="text-xs text-gray-600">Total Capacity</p>
              </div>
              <div className="bg-orange-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-orange-700">{shelterOv.total_occupied || 0}</p>
                <p className="text-xs text-orange-600">Occupied</p>
              </div>
            </div>
          </div>

          {/* Resource summary */}
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold text-gray-800 flex items-center gap-2">
                <Package className="w-5 h-5 text-green-600" /> Resource Inventory
              </h2>
              <Link href="/resources" className="text-xs text-blue-600 hover:underline">View all →</Link>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {resSumm.map((r, i) => (
                <div key={i} className="flex justify-between items-center text-sm py-1.5 border-b border-gray-100">
                  <span className="font-medium text-gray-700">{r.type_name as string}</span>
                  <div className="flex gap-3 text-xs">
                    <span className="text-green-700 font-semibold">{r.avail_qty as number} avail</span>
                    <span className="text-blue-600">{r.deployed_qty as number} deployed</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Active Incidents */}
        <div className="card mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <Activity className="w-5 h-5 text-red-600" /> Active Incidents
            </h2>
            <Link href="/incidents" className="text-xs text-blue-600 hover:underline">Manage incidents →</Link>
          </div>
          {incidents.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">No active incidents</p>
          ) : (
            <div className="space-y-2">
              {incidents.map((inc) => (
                <div key={inc.incident_id as number}
                  className="flex items-center justify-between p-3 bg-red-50/60 border border-red-100 rounded-lg">
                  <div>
                    <p className="font-medium text-sm text-gray-800">{inc.title as string}</p>
                    <p className="text-xs text-gray-500">{inc.area_name as string} • Started {formatDate(inc.start_date as string)}</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="font-semibold text-orange-700">{inc.request_count as number} requests</span>
                    <span className={`badge ${
                      inc.severity === 'CRITICAL' ? 'bg-red-100 text-red-800 border-red-200' :
                      inc.severity === 'HIGH' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                      'bg-yellow-100 text-yellow-800 border-yellow-200'
                    }`}>{inc.severity as string}</span>
                    <Link href={`/incidents/${inc.incident_id}`}
                      className="text-blue-600 hover:underline">View →</Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Emergency updates (MongoDB, Phase B) */}
        <UpdatesSummaryCard />

        {/* Critical unassigned requests */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" /> Priority Requests (Action Needed)
            </h2>
            <Link href="/requests" className="text-xs text-blue-600 hover:underline">All requests →</Link>
          </div>
          {critReqs.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">No pending priority requests ✅</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="table-header">
                    <th className="px-3 py-2 text-left">Type</th>
                    <th className="px-3 py-2 text-left">Priority</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">People</th>
                    <th className="px-3 py-2 text-left">Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {critReqs.map((r) => (
                    <tr key={r.request_id as number} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium">{r.request_type as string}</td>
                      <td className="px-3 py-2"><PriorityBadge priority={r.priority as string} /></td>
                      <td className="px-3 py-2"><StatusBadge status={r.status as string} /></td>
                      <td className="px-3 py-2">{r.people_count as number}</td>
                      <td className="px-3 py-2 text-gray-500">#{r.priority_rank as number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Quick nav */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mt-6">
          {[
            { href: '/requests',    label: 'Requests',   icon: '📋' },
            { href: '/resources',   label: 'Resources',  icon: '📦' },
            { href: '/shelters',    label: 'Shelters',   icon: '🏠' },
            { href: '/assignments', label: 'Assign',     icon: '🔗' },
            { href: '/inventory',   label: 'Inventory',  icon: '📊' },
            { href: '/updates',     label: 'Updates',    icon: '📡' },
          ].map(n => (
            <Link key={n.href} href={n.href}
              className="card text-center hover:shadow-md transition-shadow cursor-pointer p-4">
              <div className="text-2xl mb-1">{n.icon}</div>
              <p className="text-sm font-medium text-gray-700">{n.label}</p>
            </Link>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
