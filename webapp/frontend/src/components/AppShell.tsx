import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useConversationStore } from '../store/useConversationStore';
import { fetchNodes } from '../api/client';
import Sidebar from './Sidebar';
import TopNav from './TopNav';
import ChatView from '../views/ChatView';
import BranchHistoryView from '../views/BranchHistoryView';

export default function AppShell() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const setActiveConversation = useConversationStore((s) => s.setActiveConversation);
  const loadNodes = useConversationStore((s) => s.loadNodes);

  const [activeTab, setActiveTab] = useState<'chats' | 'branch-history'>('chats');
  const [selectedModel, setSelectedModel] = useState('gemma4');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (!conversationId) return;
    setActiveConversation(conversationId);
    // Load existing nodes for this conversation from the backend
    fetchNodes(conversationId).then((nodes) => {
      if (nodes.length > 0) loadNodes(nodes);
    });
  }, [conversationId, setActiveConversation, loadNodes]);

  return (
    <div className="flex h-screen overflow-hidden bg-tenet-bg">
      {/* Left: sidebar — slides in/out */}
      <div
        className="flex-shrink-0 transition-all duration-200 overflow-hidden"
        style={{ width: sidebarOpen ? 240 : 0 }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Right: main panel — min-h-0 allows nested scroll containers to shrink */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
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
