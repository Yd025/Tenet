import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Menu } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import Sidebar from '../components/Sidebar';

export default function LandingView() {
  const [inputValue, setInputValue] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const startConversation = useConversationStore((s) => s.startConversation);

  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    startConversation(inputValue.trim());
    const newId = useConversationStore.getState().activeConversationId;
    navigate(`/c/${newId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div className="min-h-screen bg-tenet-bg flex overflow-hidden">
      {/* Sidebar drawer */}
      <div
        className="flex-shrink-0 transition-all duration-200 overflow-hidden"
        style={{ width: sidebarOpen ? 240 : 0 }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main centered content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 relative">
        {/* Hamburger button */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute top-4 left-4 text-gray-500 hover:text-white transition-colors p-2 rounded hover:bg-white/5"
          >
            <Menu size={20} />
          </button>
        )}

        <div className="flex flex-col items-center gap-3 w-full max-w-2xl">
        {/* Logo */}
        <h1 className="text-tenet-teal text-4xl font-bold tracking-widest">TENET</h1>

        {/* Tagline */}
        <p className="text-sm text-gray-500">Branch forward. Think backward.</p>

        {/* Input row */}
        <div className="mt-4 w-full flex items-center gap-3 bg-tenet-surface border border-tenet-border rounded-full px-5 py-3">
          <GitBranch className="text-tenet-teal flex-shrink-0" size={18} />
          <input
            type="text"
            className="flex-1 bg-transparent text-white text-sm outline-none placeholder-gray-600"
            placeholder="Start a new conversation..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSubmit}
            className="bg-tenet-teal text-black rounded-full px-5 py-2 text-sm font-medium hover:opacity-90 transition-opacity flex-shrink-0"
          >
            Commit ↑
          </button>
        </div>

        {/* Hint */}
        <p className="text-xs text-gray-600">
          Type '/' for quick commands or select a template
        </p>
      </div>
      </div>
    </div>
  );
}
