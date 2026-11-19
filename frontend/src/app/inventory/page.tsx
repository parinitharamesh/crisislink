'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { inventoryApi, resourcesApi } from '@/lib/api';
import { PageHeader, LoadingState, Table } from '@/components/ui';
import { formatDateTime } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function InventoryPage() {
  const [txns,      setTxns]      = useState<Array<Record<string,unknown>>>([]);
  const [resources, setResources] = useState<Array<Record<string,unknown>>>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [form, setForm] = useState({ resource_id: '', quantity: 1, transaction_type: 'IN', notes: '' });

  const load = () =>
    inventoryApi.getAll()
      .then(r => setTxns(r.data.transactions))
      .catch(() => toast.error('Failed to load transactions'))
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
    resourcesApi.getAll().then(r => setResources(r.data.resources));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await inventoryApi.create({
        resource_id: parseInt(form.resource_id),
        quantity: parseInt(String(form.quantity)),
        transaction_type: form.transaction_type,
        notes: form.notes
      });
      toast.success('Transaction recorded');
      setShowForm(false); load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed';
      toast.error(msg);
    }
  };

  const TX_COLORS: Record<string, string> = {
    IN: 'bg-green-100 text-green-700',
    OUT: 'bg-red-100 text-red-700',
    TRANSFER: 'bg-blue-100 text-blue-700',
    ADJUSTMENT: 'bg-yellow-100 text-yellow-700',
  };

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="Inventory Transactions"
        subtitle="Track all resource IN/OUT/TRANSFER operations"
        action={<button onClick={() => setShowForm(s => !s)} className="btn-primary">{showForm ? 'Cancel' : '+ Record Transaction'}</button>}
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-6 grid grid-cols-2 gap-4">
          <div>
            <label className="label">Resource *</label>
            <select className="input" required value={form.resource_id}
              onChange={e => setForm(f => ({ ...f, resource_id: e.target.value }))}>
              <option value="">-- Select resource --</option>
              {resources.map(r => (
                <option key={r.resource_id as number} value={r.resource_id as number}>
                  {r.resource_name as string} (Stock: {r.quantity as number})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Transaction Type *</label>
            <select className="input" value={form.transaction_type}
              onChange={e => setForm(f => ({ ...f, transaction_type: e.target.value }))}>
              <option value="IN">IN – Receive stock</option>
              <option value="OUT">OUT – Dispatch stock</option>
              <option value="TRANSFER">TRANSFER – Move between locations</option>
              <option value="ADJUSTMENT">ADJUSTMENT – Audit correction</option>
            </select>
          </div>
          <div>
            <label className="label">Quantity *</label>
            <input type="number" min={1} className="input" required value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
          </div>
          <div>
            <label className="label">Notes</label>
            <input className="input" placeholder="Reason or context"
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="btn-primary">Record Transaction</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      <Table
        headers={['#','Type','Qty','Resource','Category','Organization','Notes','Time','By']}
        empty={txns.length === 0}
      >
        {txns.map((t) => (
          <tr key={t.transaction_id as number} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-gray-400 text-xs">#{t.transaction_id as number}</td>
            <td className="px-4 py-3">
              <span className={`badge border-transparent text-xs ${TX_COLORS[t.transaction_type as string] || ''}`}>
                {t.transaction_type as string}
              </span>
            </td>
            <td className="px-4 py-3 font-semibold">{t.quantity as number}</td>
            <td className="px-4 py-3 text-sm font-medium">{t.resource_name as string}</td>
            <td className="px-4 py-3 text-xs text-gray-500">{t.type_name as string}</td>
            <td className="px-4 py-3 text-xs text-gray-600">{t.org_name as string}</td>
            <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{(t.notes as string) || '—'}</td>
            <td className="px-4 py-3 text-xs text-gray-500">{formatDateTime(t.transaction_time as string)}</td>
            <td className="px-4 py-3 text-xs text-gray-600">{(t.performed_by_name as string) || '—'}</td>
          </tr>
        ))}
      </Table>
    </DashboardLayout>
  );
}
