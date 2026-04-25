import { useEffect, useState } from 'react';
import { fetchTelemetry } from '../api/client';
import type { TelemetryStats } from '../types/index';

export default function GX10TelemetryWidget() {
  const [stats, setStats] = useState<TelemetryStats | null>(null);
  const [isOnline, setIsOnline] = useState(true);

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

  const tempPct = stats ? Math.min(100, Math.max(0, (stats.temp_c - 40) / 60 * 100)) : 0;
  const isActive = stats ? stats.utilization > 0 : false;

  if (stats === null) {
    return (
      <div className="px-4 py-3 border-t border-tenet-border">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-gray-700 animate-pulse" />
          <span className="text-xs font-mono tracking-widest text-gray-600">GX10 LIVE</span>
        </div>
        {['BLACKWELL TEMP', 'GPU UTILIZATION', 'VRAM'].map((label) => (
          <div key={label} className="mb-2">
            <span className="text-xs text-gray-600 uppercase tracking-wider">{label}</span>
            <div className="h-1 mt-1 bg-gray-800 rounded-full animate-pulse" />
          </div>
        ))}
        <div className="mt-2">
          <div className="text-xs text-gray-600 uppercase tracking-wider mb-1">TOKENS / SEC</div>
          <div className="h-4 bg-gray-800 rounded animate-pulse w-20" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-3 border-t border-tenet-border">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className={`w-2 h-2 rounded-full ${
            isOnline
              ? isActive
                ? 'bg-tenet-teal animate-ping'
                : 'bg-tenet-teal animate-pulse'
              : 'bg-red-500'
          }`}
        />
        <span className="text-xs font-mono tracking-widest text-tenet-teal">GX10 LIVE</span>
        {isActive && (
          <span className="ml-auto text-xs text-tenet-teal font-mono animate-pulse">● ACTIVE</span>
        )}
      </div>

      {/* Blackwell Temp */}
      <StatRow label="BLACKWELL TEMP" value={`${stats.temp_c}°C`} pct={tempPct} />

      {/* GPU Utilization — pulses when active */}
      <div className={`mb-2 ${isActive ? 'opacity-100' : 'opacity-70'}`}>
        <div className="flex justify-between mb-1">
          <span className="text-xs text-gray-600 uppercase tracking-wider">GPU UTILIZATION</span>
          <span className="text-xs text-white font-mono">{stats.utilization}%</span>
        </div>
        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isActive
                ? 'bg-gradient-to-r from-tenet-teal to-cyan-400 animate-pulse'
                : 'bg-gradient-to-r from-tenet-teal to-cyan-400'
            }`}
            style={{ width: `${stats.utilization}%` }}
          />
        </div>
      </div>

      {/* VRAM */}
      <StatRow label="VRAM" value={`${stats.vram_gb.toFixed(1)} GB`} pct={Math.min(100, stats.vram_gb / 80 * 100)} />

      {/* TPS */}
      <div className="mt-2">
        <div className="text-xs text-gray-600 uppercase tracking-wider mb-1">TOKENS / SEC</div>
        <div className="text-tenet-teal text-xl font-bold font-mono">
          {stats.tps} <span className="text-gray-600 text-xs font-normal">TPS</span>
        </div>
      </div>

      {/* Active nodes */}
      <div className="flex justify-between mt-3 pt-2 border-t border-tenet-border">
        <span className="text-xs text-gray-600">Active Nodes</span>
        <span className="text-xs text-tenet-teal font-mono">{stats.active_nodes}</span>
      </div>
    </div>
  );
}

interface StatRowProps {
  label: string;
  value: string;
  pct: number;
}

function StatRow({ label, value, pct }: StatRowProps) {
  return (
    <div className="mb-2">
      <div className="flex justify-between mb-1">
        <span className="text-xs text-gray-600 uppercase tracking-wider">{label}</span>
        <span className="text-xs text-white font-mono">{value}</span>
      </div>
      <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-tenet-teal to-cyan-400 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
