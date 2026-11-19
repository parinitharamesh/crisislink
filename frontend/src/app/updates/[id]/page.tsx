'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { incidentsApi, mongoApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { LoadingState, PriorityBadge } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import {
  EmergencyUpdate, IncidentOption, UpdateForm, UpdateFormValues, UpdateStatusBadge, apiErrorMessage,
} from '@/components/updates/shared';
import toast from 'react-hot-toast';

export default function UpdateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();

  const [update, setUpdate]       = useState<EmergencyUpdate | null>(null);
  const [incidents, setIncidents] = useState<IncidentOption[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [editing, setEditing]     = useState(false);
  const [saving, setSaving]       = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isAdmin  = user?.role === 'ADMIN';
  const canEdit  = !!update && (isAdmin || (user?.role === 'COORDINATOR' && update.created_by === user.user_id));

  useEffect(() => {
    setLoading(true);
    Promise.all([mongoApi.getUpdate(id), incidentsApi.getAll({ limit: 100 }).catch(() => null)])
      .then(([uRes, iRes]) => {
        setUpdate(uRes.data.update);
        if (iRes) setIncidents(iRes.data.incidents);
      })
      .catch(err => setError(apiErrorMessage(err, 'Failed to load update')))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async (v: UpdateFormValues) => {
    setSaving(true);
    try {
      const res = await mongoApi.editUpdate(id, { ...v, incident_id: parseInt(v.incident_id, 10) });
      setUpdate(res.data.update);
      setEditing(false);
      toast.success('Update saved');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to save update'));
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    try {
      await mongoApi.deleteUpdate(id);
      toast.success('Update deleted');
      router.push('/updates');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to delete update'));
      setConfirmDelete(false);
    }
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  if (error || !update) {
    return (
      <DashboardLayout>
        <div className="card border-red-200 bg-red-50 text-center py-10">
          <p className="text-red-700 font-medium mb-3">{error || 'Update not found'}</p>
          <Link href="/updates" className="btn-ghost text-sm">← Back to updates</Link>
        </div>
      </DashboardLayout>
    );
  }

  const incident = incidents.find(i => i.incident_id === update.incident_id);

  return (
    <DashboardLayout>
      <Link href="/updates" className="text-sm text-blue-600 hover:underline">← All emergency updates</Link>

      <div className="flex justify-between items-start my-4 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{update.title}</h1>
          <div className="flex gap-2 mt-2">
            <PriorityBadge priority={update.priority} />
            <UpdateStatusBadge status={update.status} />
            <span className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded">{update.update_type.replace('_', ' ')}</span>
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          {canEdit && !editing && <button className="btn-primary text-sm" onClick={() => setEditing(true)}>Edit</button>}
          {isAdmin && !confirmDelete && <button className="btn-danger text-sm" onClick={() => setConfirmDelete(true)}>Delete</button>}
        </div>
      </div>

      {confirmDelete && (
        <div className="card border-red-200 bg-red-50 mb-5 flex items-center justify-between">
          <p className="text-sm text-red-800">Permanently delete this update? This cannot be undone.</p>
          <div className="flex gap-2">
            <button className="btn-danger text-sm" onClick={handleDelete}>Yes, delete</button>
            <button className="btn-ghost text-sm" onClick={() => setConfirmDelete(false)}>Cancel</button>
          </div>
        </div>
      )}

      {editing ? (
        <UpdateForm
          initial={{
            incident_id: String(update.incident_id), title: update.title, message: update.message,
            update_type: update.update_type, status: update.status, priority: update.priority,
          }}
          incidents={incidents} submitLabel="Save Changes" submitting={saving}
          onSubmit={handleSave} onCancel={() => setEditing(false)}
        />
      ) : (
        <div className="card space-y-4">
          <p className="text-gray-800 whitespace-pre-wrap">{update.message}</p>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm border-t border-gray-100 pt-4">
            <div><dt className="text-gray-500">Incident</dt>
              <dd className="font-medium">
                <Link href={`/incidents/${update.incident_id}`} className="text-blue-600 hover:underline">
                  #{update.incident_id}{incident ? ` – ${incident.title}` : ''}
                </Link>
              </dd></div>
            <div><dt className="text-gray-500">Created by</dt>
              <dd className="font-medium">{update.created_by_name || `User ${update.created_by}`}</dd></div>
            <div><dt className="text-gray-500">Created</dt><dd className="font-medium">{formatDateTime(update.created_at)}</dd></div>
            <div><dt className="text-gray-500">Last updated</dt><dd className="font-medium">{formatDateTime(update.updated_at)}</dd></div>
          </dl>
          <p className="text-xs text-gray-400 font-mono">_id: {update._id}</p>
        </div>
      )}
    </DashboardLayout>
  );
}
