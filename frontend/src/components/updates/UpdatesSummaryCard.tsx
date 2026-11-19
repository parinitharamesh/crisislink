'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Radio } from 'lucide-react';
import { mongoApi } from '@/lib/api';
import { PriorityBadge, Spinner } from '@/components/ui';
import { timeAgo } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { EmergencyUpdate } from './shared';

/** Dashboard widget. Fully self-contained: a MongoDB outage only affects this card. */
export default function UpdatesSummaryCard() {
  const { user } = useAuth();
  const [recent, setRecent]   = useState<EmergencyUpdate[]>([]);
  const [counts, setCounts]   = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [failed, setFailed]   = useState(false);

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      try {
        const u = await mongoApi.getUpdates({ limit: 4, status: 'ACTIVE' });
        setRecent(u.data.updates);

        // Analytics are staff-only; citizens can still read active updates.
        if (user.role === 'ADMIN' || user.role === 'COORDINATOR') {
          const a = await mongoApi.updatesAnalytics();
          setCounts(a.data.analytics.by_status || {});
        }
      } catch {
        setFailed(true);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [user]);

  return (
    <div className="card mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-gray-800 flex items-center gap-2">
          <Radio className="w-5 h-5 text-blue-600" /> Emergency Updates
        </h2>
        <Link href="/updates" className="text-xs text-blue-600 hover:underline">
          {user?.role === 'CITIZEN' ? 'View updates' : 'Manage updates'} →
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : failed ? (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
          Emergency updates are temporarily unavailable (MongoDB). The rest of the dashboard is unaffected.
        </p>
      ) : (
        <>
          {(user?.role === 'ADMIN' || user?.role === 'COORDINATOR') && (
            <div className="flex gap-4 text-xs text-gray-600 mb-3">
              {['ACTIVE', 'DRAFT', 'RESOLVED', 'ARCHIVED'].map(s => (
                <span key={s}><span className="font-semibold text-gray-800">{counts[s] || 0}</span> {s.toLowerCase()}</span>
              ))}
            </div>
          )}
          {recent.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">No active updates</p>
          ) : (
            <div className="space-y-2">
              {recent.map(u => (
                <Link key={u._id} href={`/updates/${u._id}`}
                  className="flex items-center justify-between p-3 bg-gray-50 border border-gray-100 rounded-lg hover:bg-blue-50/50">
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-gray-800 truncate">{u.title}</p>
                    <p className="text-xs text-gray-500">Incident #{u.incident_id} • {timeAgo(u.created_at)}</p>
                  </div>
                  <PriorityBadge priority={u.priority} />
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
