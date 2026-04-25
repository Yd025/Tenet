import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useConversationStore } from '../store/useConversationStore';
import Sidebar from './Sidebar';
import TopNav from './TopNav';
import ChatView from '../views/ChatView';
import BranchHistoryView from '../views/BranchHistoryView';

export default function AppShell() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const setActiveConversation = useConversationStore((s) => s.setActiveConversation);

  const [activeTab, setActiveTab] = useState<'chats' | 'branch-history'>('chats');
  const [selectedModel, setSelectedModel] = useState('deepseek');

  useEffect(() => {
    if (conversationId) {
      setActiveConversation(conversationId);
    }
  }, [conversationId, setActiveConversation]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left: sidebar */}
      <Sidebar />

      {/* Right: main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
        />
        {activeTab === 'chats' ? (
          <ChatView selectedModel={selectedModel} />
        ) : (
          <BranchHistoryView setActiveTab={setActiveTab} />
        )}
      </div>
    </div>
  );
}
