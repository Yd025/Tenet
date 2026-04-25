import { useState, useEffect, useRef, useMemo } from 'react';
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

  const nodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const commitMessage = useConversationStore((s) => s.commitMessage);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);

  // Build thread inline so it's driven by reactive subscriptions, not get()
  const thread = useMemo(() => {
    if (!headNodeId) return [];
    const result: ConversationNode[] = [];
    let currentId: string | null = headNodeId;
    while (currentId !== null) {
      const node: ConversationNode | undefined = nodes[currentId];
      if (!node || node.pruned) break;
      result.push(node);
      currentId = node.parent_id;
    }
    return result.reverse();
  }, [nodes, headNodeId]);

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
      console.error('Chat failed:', err);
      setError('Something went wrong. Check the console for details.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // min-h-0 is required at every flex-col level so the scroll container
    // gets a real constrained height instead of expanding to content size
    <div className="flex-1 flex flex-col min-h-0 bg-tenet-bg">
      {/* Thread scroll area */}
      <div className="flex-1 overflow-y-auto min-h-0 px-6 py-6 space-y-2">
        {thread.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-600 text-sm">Start your conversation...</p>
              <p className="text-gray-700 text-xs mt-1">Type a message below and press Commit ↑</p>
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
            <div className="w-7 h-7 rounded-full bg-tenet-teal/20 border border-tenet-teal/30 flex items-center justify-center flex-shrink-0 mt-1">
              <span className="text-tenet-teal text-xs font-bold">T</span>
            </div>
            <div className="bg-tenet-surface border-l-2 border-tenet-teal rounded-2xl px-4 py-3">
              <span className="inline-flex gap-1 items-center">
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

      {/* Input bar — flex-shrink-0 prevents it from being squashed */}
      <div className="flex-shrink-0">
        <CommitInputBar onCommit={handleCommit} isLoading={isLoading} />
      </div>
    </div>
  );
}
