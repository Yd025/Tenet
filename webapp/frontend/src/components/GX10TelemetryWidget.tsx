import { useEffect, useState } from 'react';
import { fetchTelemetry } from '../api/client';
import { useThemeStore } from '../store/useThemeStore';
import { useConversationStore } from '../store/useConversationStore';
import type { TelemetryStats } from '../types/index';

export default function GX10TelemetryWidget() {
  const [stats, setStats] = useState<TelemetryStats | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const isDark = useThemeStore((s) => s.isDark);
  const lastTps = useConversationStore((s) => s.lastTps);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await fetchTelemetry();
        setStats(data);
        setIsOnline(true);
      } catch {
        setIsOnline(false);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  const teal = isDark ? '#2DD4BF' : '#0d9488';
  const labelCls = isDark ? 'text-gray-500' : 'text-gray-600';
  const valueCls = isDark ? 'text-white' : 'text-gray-900';
  const trackCls = isDark ? 'bg-gray-800' : 'bg-gray-200';
  const borderCls = isDark ? 'border-[#1e1e24]' : 'border-gray-200';

  const tempPct = stats?.temp_c != null ? Math.min(100, Math.max(0, (stats.temp_c - 40) / 60 * 100)) : 0;
  const isActive = stats?.utilization != null ? stats.utilization > 0 : false;

  if (stats === null) {
    return (
      <div className={`px-4 py-3 border-t ${borderCls}`}>
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-2 h-2 rounded-full animate-pulse ${isDark ? 'bg-gray-700' : 'bg-gray-300'}`} />
          <span className={`text-xs font-mono tracking-widest ${labelCls}`}>GX10 LIVE</span>
        </div>
        {['BLACKWELL TEMP', 'GPU UTILIZATION', 'GPU CLOCK'].map((label) => (
          <div key={label} className="mb-2">
            <span className={`text-xs uppercase tracking-wider ${labelCls}`}>{label}</span>
            <div className={`h-1 mt-1 rounded-full animate-pulse ${trackCls}`} />
          </div>
        ))}
        <div className="mt-2">
          <div className={`text-xs uppercase tracking-wider mb-1 ${labelCls}`}>TOKENS / SEC</div>
          <div className={`h-4 rounded animate-pulse w-20 ${trackCls}`} />
        </div>
      </div>
    );
  }

  return (
    <div className={`px-4 py-3 border-t ${borderCls}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2 h-2 rounded-full ${isOnline ? (isActive ? 'animate-ping' : 'animate-pulse') : 'bg-red-500'}`}
          style={{ backgroundColor: isOnline ? teal : undefined }} />
        <span className="text-xs font-mono tracking-widest" style={{ color: teal }}>GX10 LIVE</span>
        {isActive && (
          <span className="ml-auto text-xs font-mono animate-pulse" style={{ color: teal }}>● ACTIVE</span>
        )}
      </div>

      <StatRow label="BLACKWELL TEMP" value={stats.temp_c != null ? `${stats.temp_c}°C` : 'N/A'} pct={tempPct} teal={teal} labelCls={labelCls} valueCls={valueCls} trackCls={trackCls} />

      <div className="mb-2">
        <div className="flex justify-between mb-1">
          <span className={`text-xs uppercase tracking-wider ${labelCls}`}>GPU UTILIZATION</span>
          <span className={`text-xs font-mono ${valueCls}`}>{stats.utilization ?? 'N/A'}{stats.utilization != null ? '%' : ''}</span>
        </div>
        <div className={`h-1 rounded-full overflow-hidden ${trackCls}`}>
          <div
            className={`h-full rounded-full transition-all duration-500 ${isActive ? 'animate-pulse' : ''}`}
            style={{ width: `${stats.utilization ?? 0}%`, background: `linear-gradient(to right, ${teal}, #22d3ee)` }}
          />
        </div>
      </div>

      <StatRow label="GPU CLOCK" value={stats.gpu_clock_mhz != null ? `${stats.gpu_clock_mhz} MHz` : 'N/A'} pct={stats.gpu_clock_mhz != null ? Math.min(100, stats.gpu_clock_mhz / 3000 * 100) : 0} teal={teal} labelCls={labelCls} valueCls={valueCls} trackCls={trackCls} />

      <div className="mt-2">
        <div className={`text-xs uppercase tracking-wider mb-1 ${labelCls}`}>TOKENS / SEC</div>
        <div className="text-xl font-bold font-mono" style={{ color: teal }}>
          {lastTps != null ? lastTps : '—'} <span className={`text-xs font-normal ${labelCls}`}>TPS</span>
        </div>
      </div>

      <div className={`flex justify-between mt-3 pt-2 border-t ${borderCls}`}>
        <span className={`text-xs ${labelCls}`}>Active Nodes</span>
        <span className="text-xs font-mono" style={{ color: teal }}>{stats.active_nodes}</span>
      </div>
    </div>
  );
}

interface StatRowProps {
  label: string;
  value: string;
  pct: number;
  teal: string;
  labelCls: string;
  valueCls: string;
  trackCls: string;
}

function StatRow({ label, value, pct, teal, labelCls, valueCls, trackCls }: StatRowProps) {
  return (
    <div className="mb-2">
      <div className="flex justify-between mb-1">
        <span className={`text-xs uppercase tracking-wider ${labelCls}`}>{label}</span>
        <span className={`text-xs font-mono ${valueCls}`}>{value}</span>
      </div>
      <div className={`h-1 rounded-full overflow-hidden ${trackCls}`}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: `linear-gradient(to right, ${teal}, #22d3ee)` }}
        />
      </div>
    </div>
  );
}
