import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
import { fetchNodes } from '../api/client';
import Sidebar from './Sidebar';
import TopNav from './TopNav';
import ChatView from '../views/ChatView';
import BranchHistoryView from '../views/BranchHistoryView';
import AnimatedBackground from './AnimatedBackground';

export default function AppShell() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const setActiveConversation = useConversationStore((s) => s.setActiveConversation);
  const loadNodes = useConversationStore((s) => s.loadNodes);
  const isDark = useThemeStore((s) => s.isDark);

  const [activeTab, setActiveTab] = useState<'chats' | 'branch-history'>('chats');
  const [selectedModel, setSelectedModel] = useState('gemma4:latest');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (!conversationId) return;
    setActiveConversation(conversationId);
    fetchNodes(conversationId).then((nodes) => {
      loadNodes(nodes);
    });
  }, [conversationId, setActiveConversation, loadNodes]);

  return (
    <div className={`flex h-screen overflow-hidden relative ${isDark ? 'bg-[#1a1a1e]' : 'bg-[#f0f0f2]'}`}>
      <AnimatedBackground />

      {/* Left: sidebar */}
      <div
        className="flex-shrink-0 transition-all duration-200 overflow-hidden relative z-10"
        style={{ width: sidebarOpen ? 240 : 0 }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Right: main panel */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 relative z-10">
        <TopNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
        />
        {activeTab === 'chats' ? (
          <ChatView selectedModel={selectedModel} />
        ) : (
          <BranchHistoryView setActiveTab={setActiveTab} selectedModel={selectedModel} />
        )}
      </div>
    </div>
  );
}
