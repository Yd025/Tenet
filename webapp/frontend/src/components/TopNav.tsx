import { useState } from 'react';
import { ChevronRight, ChevronDown, PanelLeft } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';

interface TopNavProps {
  activeTab: 'chats' | 'branch-history';
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const MODEL_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek R1',
  qwen: 'Qwen 2.5',
};

const MODELS = ['deepseek', 'qwen'];

export default function TopNav({
  activeTab,
  setActiveTab,
  selectedModel,
  setSelectedModel,
  sidebarOpen,
  onToggleSidebar,
}: TopNavProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const { activeConversationId, conversations } = useConversationStore((s) => ({
    activeConversationId: s.activeConversationId,
    conversations: s.conversations,
  }));

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const conversationTitle = activeConversation?.title ?? 'Untitled';

  return (
    <div className="bg-tenet-surface border-b border-tenet-border h-12 flex items-center px-3 gap-3 flex-shrink-0">
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className={`p-1.5 rounded transition-colors ${
          sidebarOpen
            ? 'text-gray-500 hover:text-white hover:bg-white/5'
            : 'text-tenet-teal hover:bg-tenet-teal/10'
        }`}
        title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        <PanelLeft size={16} />
      </button>

      {/* Breadcrumb */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <span className="text-gray-500 text-sm">Conversations</span>
        <ChevronRight className="text-gray-600" size={12} />
        <span className="text-white text-sm font-medium truncate max-w-[200px]">
          {conversationTitle}
        </span>
      </div>

      {/* Tab switcher — centered */}
      <div className="flex items-center gap-1 mx-auto">
        <button
          onClick={() => setActiveTab('chats')}
          className={`text-sm px-3 py-1 pb-0.5 border-b-2 transition-colors ${
            activeTab === 'chats'
              ? 'border-tenet-teal text-tenet-teal'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Chats
        </button>
        <button
          onClick={() => setActiveTab('branch-history')}
          className={`text-sm px-3 py-1 pb-0.5 border-b-2 transition-colors ${
            activeTab === 'branch-history'
              ? 'border-tenet-teal text-tenet-teal'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Branch History
        </button>
      </div>

      {/* Model selector */}
      <div className="relative flex-shrink-0">
        <button
          onClick={() => setDropdownOpen((o) => !o)}
          className="flex items-center gap-1.5 text-xs border border-tenet-border rounded-lg px-3 py-1.5 bg-tenet-bg text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
        >
          <span className="text-gray-500 mr-0.5">Model:</span>
          {MODEL_LABELS[selectedModel] ?? selectedModel}
          <ChevronDown size={12} />
        </button>
        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-1 bg-tenet-surface border border-tenet-border rounded-lg shadow-lg z-10 min-w-[140px] overflow-hidden">
            {MODELS.map((model) => (
              <button
                key={model}
                onClick={() => {
                  setSelectedModel(model);
                  setDropdownOpen(false);
                }}
                className={`block w-full text-left px-3 py-2 text-sm hover:bg-white/5 transition-colors ${
                  model === selectedModel ? 'text-tenet-teal' : 'text-gray-300'
                }`}
              >
                {MODEL_LABELS[model]}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
