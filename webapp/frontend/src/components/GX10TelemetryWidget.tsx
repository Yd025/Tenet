import { useEffect, useState } from 'react';
import { fetchTelemetry } from '../api/client';
import type { TelemetryStats } from '../types/index';

export default function GX10TelemetryWidget() {
  const [stats, setStats] = useState<TelemetryStats | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    // Fetch immediately on mount
    const fetchStats = async () => {
      try {
        const data = await fetchTelemetry();
        setStats(data);
        setIsOnline(true);
      } catch (error) {
        console.error('Failed to fetch telemetry:', error);
        setIsOnline(false);
      }
    };

    fetchStats();

    // Set up polling interval (3 seconds)
    const interval = setInterval(fetchStats, 3000);

    // Clean up interval on unmount
    return () => clearInterval(interval);
  }, []);

  // Calculate temperature percentage: 65°C→0%, 85°C→100%
  const tempPct = stats ? Math.min(100, Math.max(0, (stats.temp_c - 65) / 20 * 100)) : 0;

  // Skeleton/loading state
  if (stats === null) {
    return (
      <div className="px-4 py-3 border-t border-tenet-border">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-gray-700 animate-pulse" />
          <span className="text-xs font-mono tracking-widest text-gray-600">GX10 LIVE</span>
        </div>

        {/* Skeleton bars */}
        <div className="mb-2">
          <div className="flex justify-between mb-1">
            <span className="text-xs text-gray-600 uppercase tracking-wider">BLACKWELL TEMP</span>
          </div>
          <div className="h-1 bg-gray-800 rounded-full animate-pulse" />
        </div>

        <div className="mb-2">
          <div className="flex justify-between mb-1">
            <span className="text-xs text-gray-600 uppercase tracking-wider">PETAFLOPS UTIL</span>
          </div>
          <div className="h-1 bg-gray-800 rounded-full animate-pulse" />
        </div>

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
        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-tenet-teal animate-pulse' : 'bg-red-500'}`} />
        <span className="text-xs font-mono tracking-widest text-tenet-teal">GX10 LIVE</span>
      </div>

      {/* BLACKWELL TEMP stat row */}
      <StatRow
        label="BLACKWELL TEMP"
        value={`${stats.temp_c}°C`}
        pct={tempPct}
      />

      {/* PETAFLOPS UTIL stat row */}
      <StatRow
        label="PETAFLOPS UTIL"
        value={`${stats.petaflops_pct}%`}
        pct={stats.petaflops_pct}
      />

      {/* TPS big number */}
      <div className="mt-2">
        <div className="text-xs text-gray-600 uppercase tracking-wider mb-1">TOKENS / SEC</div>
        <div className="text-tenet-teal text-xl font-bold font-mono">
          {stats.tps} <span className="text-gray-600 text-xs font-normal">TPS</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-between mt-3 pt-2 border-t border-tenet-border">
        <span className="text-xs text-gray-600">☁ Cloud Sync</span>
        <span className="text-xs text-tenet-teal">● Local</span>
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
