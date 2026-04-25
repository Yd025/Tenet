import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, X, HelpCircle } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import GX10TelemetryWidget from './GX10TelemetryWidget';

interface SidebarProps {
  onClose: () => void;
}

export default function Sidebar({ onClose }: SidebarProps) {
  const navigate = useNavigate();
  const conversations = useConversationStore((s) => s.conversations);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);

  const handleNewChat = () => {
    navigate('/');
  };

  return (
    <div className="w-60 flex-shrink-0 h-screen bg-tenet-surface border-r border-tenet-border flex flex-col">
      {/* Logo + close button */}
      <div className="px-4 pt-4 pb-3 flex items-center justify-between">
        <div className="flex flex-col leading-tight">
          <span className="text-tenet-teal font-bold text-base tracking-wide">TENET</span>
          <span className="text-gray-500 text-xs">v1.0.0</span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-white transition-colors p-1 rounded hover:bg-white/5"
        >
          <X size={16} />
        </button>
      </div>

      {/* Divider */}
      <div className="border-b border-tenet-border" />

      {/* New Chat button */}
      <div className="px-3 py-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 border border-tenet-border rounded-lg px-3 py-2 text-sm text-gray-300 hover:text-white hover:border-gray-500 hover:bg-white/5 transition-all"
        >
          <Plus size={15} />
          New Chat
        </button>
      </div>

      {/* Conversations label */}
      <p className="text-xs text-gray-500 uppercase tracking-widest px-4 mb-1">
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
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <MessageSquare size={14} className="flex-shrink-0 opacity-70" />
              <span className="truncate">{conv.title}</span>
            </button>
          );
        })}
      </div>

      {/* Bottom section */}
      <div className="border-t border-tenet-border">
        {/* Support link */}
        <button className="w-full flex items-center gap-2 px-4 py-3 text-sm text-gray-500 hover:text-white hover:bg-white/5 transition-colors">
          <HelpCircle size={14} className="flex-shrink-0" />
          <span>Support</span>
        </button>

        {/* GX10 widget */}
        <GX10TelemetryWidget />
      </div>
    </div>
  );
}
