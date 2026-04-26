import { useMemo } from 'react';
import { useThemeStore } from '../store/useThemeStore';

interface Particle {
  id: number;
  size: number;
  top: string;
  left: string;
  speed: 'slow' | 'med' | 'fast';
  delay: string;
  color: string;
}

export default function AnimatedBackground() {
  const isDark = useThemeStore((s) => s.isDark);

  const particles = useMemo<Particle[]>(() => {
    const speeds: Array<'slow' | 'med' | 'fast'> = ['slow', 'med', 'fast'];
    const darkColors = ['#2DD4BF22', '#7c3aed18', '#ec489914', '#2DD4BF10'];
    const lightColors = ['#0d948820', '#6d28d915', '#db277712', '#0d948810'];
    const colors = isDark ? darkColors : lightColors;

    return Array.from({ length: 18 }, (_, i) => ({
      id: i,
      size: 4 + (i % 5) * 6,
      top: `${(i * 17 + 5) % 95}%`,
      left: `${(i * 23 + 3) % 95}%`,
      speed: speeds[i % 3],
      delay: `${(i * 0.7) % 4}s`,
      color: colors[i % colors.length],
    }));
  }, [isDark]);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {particles.map((p) => (
        <div
          key={p.id}
          className={`particle particle-${p.speed}`}
          style={{
            width: p.size,
            height: p.size,
            top: p.top,
            left: p.left,
            background: p.color,
            animationDelay: p.delay,
          }}
        />
      ))}
    </div>
  );
}
