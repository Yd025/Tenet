import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, PanelLeft, Sun, Moon } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
import { fetchConversation } from '../api/client';

interface TopNavProps {
  activeTab: 'chats' | 'branch-history';
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const MODEL_LABELS: Record<string, string> = {
  'gemma4:latest': 'Gemma 4',
  'gemma4:e4b': 'Gemma 4 E4B',
  'qwen3.6:latest': 'Qwen 3.6',
  'qwen3.5:9b': 'Qwen 3.5 9B',
  'mistral-small3.2:24b': 'Mistral Small 3.2 24B',
  'ministral-3:8b': 'Ministral 3 8B',
};

const MODELS = [
  'gemma4:latest',
  'gemma4:e4b',
  'qwen3.6:latest',
  'qwen3.5:9b',
  'mistral-small3.2:24b',
  'ministral-3:8b',
];

export default function TopNav({
  activeTab, setActiveTab, selectedModel, setSelectedModel, sidebarOpen, onToggleSidebar,
}: TopNavProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [dbTitle, setDbTitle] = useState<string | null>(null);
  const { isDark, toggle } = useThemeStore();

  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const conversations = useConversationStore((s) => s.conversations);
  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  // Fetch title from DB for conversations not in local store
  useEffect(() => {
    if (!activeConversationId) { setDbTitle(null); return; }
    if (activeConversation) { setDbTitle(null); return; } // local store has it
    fetchConversation(activeConversationId)
      .then((data) => setDbTitle(data.title))
      .catch(() => setDbTitle(null));
  }, [activeConversationId, activeConversation]);

  const conversationTitle = activeConversation?.title ?? dbTitle ?? '';

  const surface = isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200';
  const teal = isDark ? 'text-[#2DD4BF] border-[#2DD4BF]' : 'text-[#0d9488] border-[#0d9488]';
  const textMuted = isDark ? 'text-gray-500' : 'text-gray-600';
  const textBase = isDark ? 'text-white' : 'text-gray-800';
  const hoverBg = isDark ? 'hover:bg-white/5 hover:text-white' : 'hover:bg-gray-100 hover:text-gray-900';

  return (
    <div className={`border-b h-12 flex items-center px-3 gap-2 flex-shrink-0 relative z-20 ${surface}`}>
      {/* Left: sidebar toggle + breadcrumb */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <button
          onClick={onToggleSidebar}
          className={`p-1.5 rounded transition-colors flex-shrink-0 ${sidebarOpen ? `${textMuted} ${hoverBg}` : `${teal} ${isDark ? 'hover:bg-[#2DD4BF]/10' : 'hover:bg-[#0d9488]/10'}`}`}
          title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          <PanelLeft size={16} />
        </button>
        {conversationTitle && (
          <div className="flex items-center gap-1 min-w-0">
            <span className={`text-sm flex-shrink-0 ${textMuted}`}>Conversations</span>
            <ChevronRight className={`flex-shrink-0 ${textMuted}`} size={12} />
            <span className={`text-sm font-semibold truncate ${isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]'}`}>
              {conversationTitle}
            </span>
          </div>
        )}
      </div>

      {/* Center: tabs — absolutely centered so left/right content never shifts them */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-1">
        {(['chats', 'branch-history'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-sm px-3 py-1 pb-0.5 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab
                ? `${isDark ? 'border-[#2DD4BF] text-[#2DD4BF]' : 'border-[#0d9488] text-[#0d9488]'}`
                : `border-transparent ${textMuted} ${hoverBg}`
            }`}
          >
            {tab === 'chats' ? 'Chats' : 'Branch History'}
          </button>
        ))}
      </div>

      {/* Right: theme toggle + model selector */}
      <div className="flex items-center gap-2 flex-shrink-0 ml-auto">
        <button
          onClick={toggle}
          className={`p-1.5 rounded transition-colors flex-shrink-0 ${textMuted} ${hoverBg}`}
          title="Toggle light/dark"
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <div className="relative flex-shrink-0">
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className={`flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 transition-colors whitespace-nowrap ${
              isDark
                ? 'border-[#1e1e24] bg-[#1a1a1e] text-gray-300 hover:text-white hover:border-gray-500'
                : 'border-gray-200 bg-gray-50 text-gray-600 hover:text-gray-900 hover:border-gray-400'
            }`}
          >
            <span className={`mr-0.5 ${textMuted}`}>Model:</span>
            {MODEL_LABELS[selectedModel] ?? selectedModel}
            <ChevronDown size={12} />
          </button>
          {dropdownOpen && (
            <div className={`absolute right-0 top-full mt-1 border rounded-lg shadow-lg z-50 min-w-max overflow-hidden ${
              isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200'
            }`}>
              {MODELS.map((model) => (
                <button
                  key={model}
                  onClick={() => { setSelectedModel(model); setDropdownOpen(false); }}
                  className={`block w-full text-left px-3 py-2 text-sm transition-colors whitespace-nowrap ${
                    model === selectedModel
                      ? isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]'
                      : `${textBase} ${hoverBg}`
                  }`}
                >
                  {MODEL_LABELS[model]}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
