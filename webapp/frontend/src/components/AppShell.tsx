import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useConversationStore } from '../store/useConversationStore';
import Sidebar from './Sidebar';
import TopNav from './TopNav';

// Placeholder views — will be replaced in later steps
function ChatView() {
  return (
    <div className="flex-1 flex items-center justify-center bg-tenet-bg">
      <span className="text-gray-500 text-sm">Chat View</span>
    </div>
  );
}

function BranchHistoryView({ setActiveTab }: { setActiveTab: (tab: 'chats' | 'branch-history') => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-tenet-bg gap-3">
      <span className="text-gray-500 text-sm">Branch History View</span>
      <button
        onClick={() => setActiveTab('chats')}
        className="text-xs text-tenet-teal underline"
      >
        Back to Chats
      </button>
    </div>
  );
}

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
          <ChatView />
        ) : (
          <BranchHistoryView setActiveTab={setActiveTab} />
        )}
      </div>
    </div>
  );
}
