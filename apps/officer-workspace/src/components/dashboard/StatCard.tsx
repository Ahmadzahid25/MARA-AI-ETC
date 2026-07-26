import { Typography } from '@openhands/ui';

interface StatCardProps {
  label: string;
  value: number;
  variant?: 'default' | 'warning' | 'danger';
}

export function StatCard({ label, value, variant = 'default' }: StatCardProps) {
  const valueColors: Record<string, string> = {
    default: 'text-slate-900 dark:text-white',
    warning: 'text-amber-600 dark:text-amber-400',
    danger: 'text-rose-600 dark:text-rose-400',
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] p-4 shadow-xs transition-all hover:shadow-sm">
      <Typography.Text fontSize="xs" className="font-medium text-slate-500 dark:text-slate-400">
        {label}
      </Typography.Text>
      <p className={`mt-2 text-2xl font-semibold ${valueColors[variant]}`}>
        {value}
      </p>
    </div>
  );
}

