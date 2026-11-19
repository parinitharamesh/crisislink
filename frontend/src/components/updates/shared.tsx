'use client';
import { useState } from 'react';
import { cn } from '@/lib/utils';

export const UPDATE_TYPES = ['GENERAL', 'STATUS', 'WARNING', 'EVACUATION', 'RESOURCE', 'WEATHER', 'ROAD_CLOSURE'];
export const UPDATE_STATUSES = ['DRAFT', 'ACTIVE', 'RESOLVED', 'ARCHIVED'];
export const UPDATE_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export interface EmergencyUpdate {
  _id: string;
  incident_id: number;
  title: string;
  message: string;
  update_type: string;
  status: string;
  priority: string;
  created_by: number;
  created_by_name?: string;
  updated_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentOption { incident_id: number; title: string; }

export const UPDATE_STATUS_COLORS: Record<string, string> = {
  DRAFT:    'bg-gray-100 text-gray-700 border-gray-200',
  ACTIVE:   'bg-green-100 text-green-800 border-green-200',
  RESOLVED: 'bg-blue-100 text-blue-800 border-blue-200',
  ARCHIVED: 'bg-gray-200 text-gray-600 border-gray-300',
};

export function UpdateStatusBadge({ status }: { status: string }) {
  return <span className={cn('badge', UPDATE_STATUS_COLORS[status] || 'bg-gray-100 text-gray-700')}>{status}</span>;
}

/** Extract a human-friendly message from an axios error (never shows raw stack/credentials). */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const e = err as { response?: { status?: number; data?: { error?: string; details?: Record<string, string> } }; code?: string };
  const data = e?.response?.data;
  if (e?.response?.status === 503) return 'MongoDB is currently unavailable. Please try again shortly.';
  if (data?.details && typeof data.details === 'object') {
    return Object.values(data.details).join('; ');
  }
  return data?.error || fallback;
}

export interface UpdateFormValues {
  incident_id: string;
  title: string;
  message: string;
  update_type: string;
  status: string;
  priority: string;
}

export const EMPTY_FORM: UpdateFormValues = {
  incident_id: '', title: '', message: '', update_type: 'GENERAL', status: 'ACTIVE', priority: 'MEDIUM',
};

export function UpdateForm({
  initial = EMPTY_FORM, incidents, submitLabel, submitting, onSubmit, onCancel,
}: {
  initial?: UpdateFormValues;
  incidents: IncidentOption[];
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (v: UpdateFormValues) => void | Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<UpdateFormValues>(initial);
  const set = (k: keyof UpdateFormValues, v: string) => setForm(f => ({ ...f, [k]: v }));

  return (
    <form
      onSubmit={e => { e.preventDefault(); onSubmit(form); }}
      className="card mb-6 grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      <div>
        <label className="label">Incident *</label>
        <select className="input" required value={form.incident_id}
          onChange={e => set('incident_id', e.target.value)}>
          <option value="">Select incident…</option>
          {incidents.map(i => (
            <option key={i.incident_id} value={i.incident_id}>#{i.incident_id} – {i.title}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Title * (3–200 chars)</label>
        <input className="input" required minLength={3} maxLength={200} value={form.title}
          onChange={e => set('title', e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <label className="label">Message * (max 5000 chars)</label>
        <textarea className="input h-28 resize-none" required maxLength={5000} value={form.message}
          onChange={e => set('message', e.target.value)} />
      </div>
      <div>
        <label className="label">Update type</label>
        <select className="input" value={form.update_type} onChange={e => set('update_type', e.target.value)}>
          {UPDATE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Status</label>
          <select className="input" value={form.status} onChange={e => set('status', e.target.value)}>
            {UPDATE_STATUSES.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Priority</label>
          <select className="input" value={form.priority} onChange={e => set('priority', e.target.value)}>
            {UPDATE_PRIORITIES.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>
      </div>
      <div className="md:col-span-2 flex gap-3">
        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? 'Saving…' : submitLabel}
        </button>
        <button type="button" onClick={onCancel} className="btn-ghost">Cancel</button>
      </div>
    </form>
  );
}
