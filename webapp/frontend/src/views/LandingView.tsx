import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Sun, Moon, ArrowRight, GitMerge, Cpu } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
import Sidebar from '../components/Sidebar';
import AnimatedBackground from '../components/AnimatedBackground';

export default function LandingView() {
  const [inputValue, setInputValue] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const startConversation = useConversationStore((s) => s.startConversation);
  const setActiveConversation = useConversationStore((s) => s.setActiveConversation);
  const { isDark, toggle } = useThemeStore();

  useEffect(() => {
    setActiveConversation(null);
    inputRef.current?.focus();
  }, [setActiveConversation]);

  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    startConversation(inputValue.trim());
    const newId = useConversationStore.getState().activeConversationId;
    navigate(`/c/${newId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmit();
  };

  const teal = isDark ? '#2DD4BF' : '#0d9488';
  const bg = isDark ? '#1a1a1e' : '#f0f0f2';
  const surface = isDark ? '#111114' : '#ffffff';
  const border = isDark ? '#1e1e24' : '#e5e7eb';
  const textPrimary = isDark ? '#f3f4f6' : '#111827';
  const textMuted = isDark ? '#6b7280' : '#4b5563';

  const features = [
    { icon: GitBranch, label: 'Branch any message', desc: 'Explore alternate paths from any point in your conversation' },
    { icon: GitMerge, label: 'Merge branches', desc: 'Synthesize divergent threads into a unified response' },
    { icon: Cpu, label: 'Local AI', desc: 'Runs entirely on your hardware via Ollama — private by default' },
  ];

  return (
    <div className="min-h-screen flex overflow-hidden relative" style={{ background: bg }}>
      <AnimatedBackground />

      {/* Sidebar */}
      <div
        className="flex-shrink-0 transition-all duration-200 overflow-hidden relative z-10"
        style={{ width: sidebarOpen ? 240 : 0 }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col relative z-10 min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-6 py-4">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-3 rounded-xl border-2 transition-colors"
              style={{ borderColor: border, color: textMuted }}
            >
              ☰ Conversations
            </button>
          )}
          {sidebarOpen && <div />}
          <button
            onClick={toggle}
            className="p-3 rounded-xl border-2 transition-colors"
            style={{ borderColor: border, color: textMuted }}
            title="Toggle theme"
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>

        {/* Center content */}
        <div className="flex-1 flex flex-col items-center justify-center px-6 pb-16">
          <div className="w-full max-w-3xl flex flex-col items-center gap-10">

            {/* Logo mark */}
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${teal}20`, border: `1px solid ${teal}40` }}>
                  <GitBranch size={28} style={{ color: teal }} />
                </div>
                <h1 className="text-6xl font-bold tracking-widest" style={{ color: teal }}>
                  TENET
                </h1>
              </div>
              <p className="text-base" style={{ color: textMuted }}>
                Branch forward. Think backward.
              </p>
            </div>

            {/* Input card */}
            <div className="w-full rounded-2xl border p-8" style={{ background: surface, borderColor: border }}>
              <p className="text-sm font-medium uppercase tracking-widest mb-4" style={{ color: textMuted }}>
                Start a new conversation
              </p>
              <div className="flex items-center gap-4 rounded-xl border px-5 py-4 transition-colors focus-within:border-opacity-100"
                style={{ borderColor: teal + '60', background: isDark ? '#0d0d10' : '#f9fafb' }}>
                <GitBranch size={20} style={{ color: teal }} className="flex-shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  className="flex-1 bg-transparent text-base outline-none"
                  style={{ color: textPrimary }}
                  placeholder="Name your topic — e.g. 'Quantum computing basics'"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <button
                  onClick={handleSubmit}
                  disabled={!inputValue.trim()}
                  className="flex items-center gap-2 rounded-lg px-6 py-2.5 text-base font-medium transition-opacity disabled:opacity-40"
                  style={{ background: teal, color: isDark ? '#000' : '#fff' }}
                >
                  Open <ArrowRight size={16} />
                </button>
              </div>

              {inputValue.trim() && (
                <p className="mt-3 text-sm" style={{ color: teal }}>
                  ↳ Topic: <span className="font-medium">{inputValue.trim()}</span>
                </p>
              )}
            </div>

            {/* Feature pills */}
            <div className="w-full grid grid-cols-3 gap-4">
              {features.map(({ icon: Icon, label, desc }) => (
                <div key={label} className="rounded-xl border p-5 flex flex-col gap-2" style={{ background: surface, borderColor: border }}>
                  <div className="flex items-center gap-2">
                    <Icon size={16} style={{ color: teal }} />
                    <span className="text-sm font-semibold" style={{ color: textPrimary }}>{label}</span>
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: textMuted }}>{desc}</p>
                </div>
              ))}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
