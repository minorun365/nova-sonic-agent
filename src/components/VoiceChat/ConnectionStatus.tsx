import type { ConnectionStatus as Status } from './types.ts';

const statusConfig = {
  disconnected: { label: '未接続', color: 'bg-gray-400' },
  connecting: { label: '接続中...', color: 'bg-yellow-400 animate-pulse' },
  connected: { label: '接続済み', color: 'bg-green-500' },
} as const;

export function ConnectionStatus({ status }: { status: Status }) {
  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <span className={`w-2 h-2 rounded-full ${config.color}`} />
      {config.label}
    </div>
  );
}
