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
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Subscribe to nodes + headNodeId directly so re-renders fire on every commit
  const nodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const commitMessage = useConversationStore((s) => s.commitMessage);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const getThreadToHead = useConversationStore((s) => s.getThreadToHead);

  // Recompute thread whenever nodes or headNodeId change
  const thread = getThreadToHead();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [nodes, headNodeId]);

  const handleCommit = async (prompt: string, isSensitive: boolean) => {
    if (!activeConversationId) return;
    setIsLoading(true);
    setError(null);
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
      setError('Could not reach the backend. Is Ollama running on :11434?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-tenet-bg">
      {/* Thread area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-2">
        {thread.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-600 text-sm">Start your conversation...</p>
              <p className="text-gray-700 text-xs mt-1">
                Type a message below and press Commit ↑
              </p>
            </div>
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

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 mb-6">
            <div className="w-7 h-7 rounded-full bg-tenet-teal/20 flex items-center justify-center flex-shrink-0 mt-1">
              <span className="text-tenet-teal text-xs font-bold">T</span>
            </div>
            <div className="bg-tenet-surface border-l-2 border-tenet-teal rounded-2xl px-4 py-3">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mx-auto max-w-lg bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <CommitInputBar onCommit={handleCommit} isLoading={isLoading} />
    </div>
  );
}
