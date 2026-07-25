import { Typography } from '@openhands/ui';

interface StatCardProps {
  label: string;
  value: number;
  variant?: 'default' | 'warning' | 'danger';
}

export function StatCard({ label, value, variant = 'default' }: StatCardProps) {
  const valueColors: Record<string, string> = {
    default: 'text-gray-900',
    warning: 'text-amber-600',
    danger: 'text-red-600',
  };

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <Typography.Text fontSize="s" className="text-gray-500">
        {label}
      </Typography.Text>
      <p className={`mt-1 text-2xl font-bold ${valueColors[variant]}`}>
        {value}
      </p>
    </div>
  );
}
