import { useState, useEffect, useRef } from 'react';
import { useConversationStore } from '../store/useConversationStore';
import { fetchChat } from '../api/client';
import type { ModelId } from '../types';
import MessageBubble from '../components/MessageBubble';
import CommitInputBar from '../components/CommitInputBar';

interface ChatViewProps {
  selectedModel: string;
}

export default function ChatView({ selectedModel }: ChatViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const getThreadToHead = useConversationStore((s) => s.getThreadToHead);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const commitMessage = useConversationStore((s) => s.commitMessage);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);

  const thread = getThreadToHead();

  // Auto-scroll to bottom when thread changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thread.length]);

  const handleCommit = async (prompt: string, isSensitive: boolean) => {
    if (!activeConversationId) return;
    setIsLoading(true);
    try {
      const result = await fetchChat({
        prompt,
        conversation_id: activeConversationId,
        branch_id: headNodeId ?? '',
        model: selectedModel as ModelId,
        is_sensitive: isSensitive,
      });
      commitMessage(prompt, result.response, result.model_used, isSensitive);
    } catch (err) {
      console.error('fetchChat failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-tenet-bg">
      {/* Thread area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {thread.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-gray-600">Start your conversation...</span>
          </div>
        ) : (
          thread.map((node) => (
            <MessageBubble
              key={node.node_id}
              node={node}
              isHead={node.node_id === headNodeId}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <CommitInputBar onCommit={handleCommit} isLoading={isLoading} />
    </div>
  );
}
