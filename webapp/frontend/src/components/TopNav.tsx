import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';

interface TopNavProps {
  activeTab: 'chats' | 'branch-history';
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

const MODELS = ['deepseek', 'qwen'];

export default function TopNav({ activeTab, setActiveTab, selectedModel, setSelectedModel }: TopNavProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const { activeConversationId, conversations } = useConversationStore((s) => ({
    activeConversationId: s.activeConversationId,
    conversations: s.conversations,
  }));

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const conversationTitle = activeConversation?.title ?? 'Untitled';

  return (
    <div className="bg-tenet-surface border-b border-tenet-border h-12 flex items-center px-4 gap-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <span className="text-gray-500 text-sm">Conversations</span>
        <ChevronRight className="text-gray-600" size={12} />
        <span className="text-white text-sm font-medium">{conversationTitle}</span>
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
          className="flex items-center gap-1 text-sm border border-tenet-border rounded px-3 py-1 bg-tenet-bg text-gray-300 hover:text-white transition-colors"
        >
          {selectedModel}
          <ChevronDown size={14} />
        </button>
        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-1 bg-tenet-surface border border-tenet-border rounded shadow-lg z-10 min-w-full">
            {MODELS.map((model) => (
              <button
                key={model}
                onClick={() => {
                  setSelectedModel(model);
                  setDropdownOpen(false);
                }}
                className={`block w-full text-left px-3 py-2 text-sm hover:bg-tenet-bg transition-colors ${
                  model === selectedModel ? 'text-tenet-teal' : 'text-gray-300'
                }`}
              >
                {model}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
