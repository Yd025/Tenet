import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import GX10TelemetryWidget from './GX10TelemetryWidget';

export default function Sidebar() {
  const navigate = useNavigate();
  const { conversations, activeConversationId } = useConversationStore((s) => ({
    conversations: s.conversations,
    activeConversationId: s.activeConversationId,
  }));

  const handleNewChat = () => {
    navigate('/');
  };

  return (
    <div className="w-60 flex-shrink-0 h-screen bg-tenet-surface border-r border-tenet-border flex flex-col">
      {/* Logo */}
      <div className="px-4 pt-4 pb-2">
        <span className="text-tenet-teal font-bold text-lg">TENET</span>
      </div>

      {/* Divider */}
      <div className="border-b border-tenet-border mx-0" />

      {/* New Chat button */}
      <button
        onClick={handleNewChat}
        className="flex items-center gap-2 border border-tenet-border rounded mx-4 my-2 px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
      >
        <Plus size={16} />
        New Chat
      </button>

      {/* Conversations label */}
      <p className="text-xs text-gray-500 uppercase tracking-wider px-4 mt-3 mb-1">
        Conversations
      </p>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => {
          const isActive = conv.id === activeConversationId;
          return (
            <button
              key={conv.id}
              onClick={() => navigate(`/c/${conv.id}`)}
              className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors ${
                isActive
                  ? 'bg-tenet-teal/10 text-tenet-teal'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <MessageSquare size={14} className="flex-shrink-0" />
              <span className="truncate">{conv.title}</span>
            </button>
          );
        })}
      </div>

      {/* Bottom widget */}
      <div className="mt-auto">
        <GX10TelemetryWidget />
      </div>
    </div>
  );
}
