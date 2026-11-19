import { cn, PRIORITY_COLORS, STATUS_COLORS } from '@/lib/utils';

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={cn('badge', PRIORITY_COLORS[priority] || 'bg-gray-100 text-gray-700')}>
      {priority}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn('badge border-transparent', STATUS_COLORS[status] || 'bg-gray-100 text-gray-700')}>
      {status.replace('_', ' ')}
    </span>
  );
}

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const s = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }[size];
  return (
    <div className={cn('border-4 border-blue-600 border-t-transparent rounded-full animate-spin', s)} />
  );
}

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <Spinner size="lg" />
      <p className="text-gray-500">Loading…</p>
    </div>
  );
}

export function EmptyState({ message = 'No data found' }: { message?: string }) {
  return (
    <div className="text-center py-16 text-gray-400">
      <div className="text-5xl mb-3">📭</div>
      <p className="font-medium">{message}</p>
    </div>
  );
}

export function StatCard({
  label, value, sub, color = 'blue', icon
}: {
  label: string; value: string | number; sub?: string;
  color?: string; icon?: React.ReactNode;
}) {
  const colors: Record<string, string> = {
    blue:   'bg-blue-50 text-blue-700 border-blue-200',
    red:    'bg-red-50 text-red-700 border-red-200',
    green:  'bg-green-50 text-green-700 border-green-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };
  return (
    <div className={cn('rounded-xl border p-5', colors[color] || colors.blue)}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium opacity-75">{label}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
          {sub && <p className="text-xs mt-1 opacity-70">{sub}</p>}
        </div>
        {icon && <div className="opacity-60">{icon}</div>}
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: {
  title: string; subtitle?: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex justify-between items-start mb-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="text-gray-500 mt-0.5 text-sm">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Table({
  headers, children, empty
}: {
  headers: string[]; children: React.ReactNode; empty?: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="table-header">
          <tr>
            {headers.map(h => (
              <th key={h} className="px-4 py-3 text-left whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 text-sm">
          {empty
            ? <tr><td colSpan={headers.length} className="py-16 text-center text-gray-400">No records found</td></tr>
            : children
          }
        </tbody>
      </table>
    </div>
  );
}
