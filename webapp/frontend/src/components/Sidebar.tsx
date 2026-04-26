import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, X, Trash2 } from 'lucide-react';
import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
import { fetchConversations, deleteConversation } from '../api/client';
import GX10TelemetryWidget from './GX10TelemetryWidget';

interface SidebarProps {
  onClose: () => void;
}

interface DbConv { root_id: string; title: string; created_at: string; }

export default function Sidebar({ onClose }: SidebarProps) {
  const navigate = useNavigate();
  const conversations = useConversationStore((s) => s.conversations);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const setActiveConversation = useConversationStore((s) => s.setActiveConversation);
  const lastMessageAt = useConversationStore((s) => s.lastMessageAt);
  const isDark = useThemeStore((s) => s.isDark);
  const [dbConversations, setDbConversations] = useState<DbConv[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadConversations = () => {
    fetchConversations()
      .then((data) => {
        const sorted = [...data].sort((a, b) => {
          const ta = new Date((a as any).last_active_at ?? a.created_at ?? 0).getTime();
          const tb = new Date((b as any).last_active_at ?? b.created_at ?? 0).getTime();
          return tb - ta;
        });
        setDbConversations(sorted);
      })
      .catch(() => {});
  };

  // Load once on mount
  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (!activeConversationId || !lastMessageAt) return;
    // Optimistically move the active conversation to the top immediately
    setDbConversations((prev) => {
      const idx = prev.findIndex((c) => c.root_id === activeConversationId);
      if (idx <= 0) return prev;
      const updated = [...prev];
      const [item] = updated.splice(idx, 1);
      return [item, ...updated];
    });
  }, [lastMessageAt]);

  const handleDelete = async (rootId: string, e: React.MouseEvent, isLocalOnly = false) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation and all its nodes?')) return;
    setDeletingId(rootId);
    try {
      if (!isLocalOnly) {
        await deleteConversation(rootId);
      }
      const remaining = dbConversations.filter((c) => c.root_id !== rootId);
      setDbConversations(remaining);
      useConversationStore.getState().deleteLocalConversation(rootId);
      if (activeConversationId === rootId) {
        setActiveConversation(null);
        const next = remaining[0];
        if (next) {
          navigate(`/c/${next.root_id}`);
        }
      }
    } catch {
      alert('Failed to delete conversation.');
    } finally {
      setDeletingId(null);
    }
  };

  // Only show local conversations that don't exist in the DB yet
  const dbIds = new Set(dbConversations.map((c) => c.root_id));
  const localOnlyConvs = conversations.filter((c) => !dbIds.has(c.id));

  const surface = isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200';
  const textMuted = isDark ? 'text-gray-500' : 'text-gray-600';
  const textBase = isDark ? 'text-gray-300' : 'text-gray-700';
  const hoverBg = isDark ? 'hover:bg-white/5 hover:text-white' : 'hover:bg-gray-100 hover:text-gray-900';
  const activeStyle = isDark ? 'bg-[#2DD4BF]/10 text-[#2DD4BF]' : 'bg-[#0d9488]/10 text-[#0d9488]';
  const teal = isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]';

  return (
    <div className={`w-60 flex-shrink-0 h-screen border-r flex flex-col ${surface}`}>
      {/* Logo + close */}
      <div className="px-4 pt-4 pb-3 flex items-center justify-between">
        <div className="flex flex-col leading-tight">
          <span className={`font-bold text-base tracking-wide ${teal}`}>TENET</span>
          <span className={`text-xs ${textMuted}`}>v1.0.0</span>
        </div>
        <button onClick={onClose} className={`${textMuted} ${hoverBg} transition-colors p-1 rounded`}>
          <X size={16} />
        </button>
      </div>

      <div className={`border-b ${isDark ? 'border-[#1e1e24]' : 'border-gray-200'}`} />

      {/* New Chat */}
      <div className="px-3 py-3">
        <button
          onClick={() => navigate('/')}
          className={`w-full flex items-center justify-center gap-2 border rounded-lg px-3 py-2 text-sm transition-all ${
            isDark
              ? 'border-[#1e1e24] text-gray-300 hover:text-white hover:border-gray-500 hover:bg-white/5'
              : 'border-gray-200 text-gray-600 hover:text-gray-900 hover:border-gray-400 hover:bg-gray-50'
          }`}
        >
          <Plus size={15} />
          New Chat
        </button>
      </div>

      <p className={`text-xs uppercase tracking-widest px-4 mb-1 ${textMuted}`}>
        Conversations
      </p>

      {/* Conversation list — sorted by time */}
      <div className="flex-1 overflow-y-auto">
        {/* Local-only (not yet in DB) conversations */}
        {localOnlyConvs.map((conv) => {
          const isActive = conv.id === activeConversationId;
          return (
            <div key={conv.id} className="group flex items-center">
              <button
                onClick={() => navigate(`/c/${conv.id}`)}
                className={`flex-1 flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors min-w-0 ${
                  isActive ? activeStyle : `${textBase} ${hoverBg}`
                }`}
              >
                <MessageSquare size={14} className="flex-shrink-0 opacity-70" />
                <span className="truncate">{conv.title}</span>
              </button>
              <button
                onClick={(e) => handleDelete(conv.id, e, true)}
                disabled={deletingId === conv.id}
                className={`opacity-0 group-hover:opacity-100 mr-2 p-1 rounded transition-all ${
                  isDark ? 'text-gray-600 hover:text-red-400' : 'text-gray-400 hover:text-red-500'
                }`}
                title="Delete conversation"
              >
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}

        {/* DB conversations */}
        {dbConversations.map((conv) => {
          const isActive = conv.root_id === activeConversationId;
          return (
            <div key={conv.root_id} className="group flex items-center">
              <button
                onClick={() => navigate(`/c/${conv.root_id}`)}
                className={`flex-1 flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors min-w-0 ${
                  isActive ? activeStyle : `${textBase} ${hoverBg}`
                }`}
              >
                <MessageSquare size={14} className="flex-shrink-0 opacity-70" />
                <span className="truncate">{conv.title}</span>
              </button>
              <button
                onClick={(e) => handleDelete(conv.root_id, e)}
                disabled={deletingId === conv.root_id}
                className={`opacity-0 group-hover:opacity-100 mr-2 p-1 rounded transition-all ${
                  isDark ? 'text-gray-600 hover:text-red-400' : 'text-gray-400 hover:text-red-500'
                }`}
                title="Delete conversation"
              >
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Bottom */}
      <div className={`border-t ${isDark ? 'border-[#1e1e24]' : 'border-gray-200'}`}>
        <GX10TelemetryWidget />
      </div>
    </div>
  );
}
