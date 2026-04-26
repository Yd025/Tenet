import { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useConversationStore } from '../store/useConversationStore';
import { streamChat } from '../api/client';
import type { ModelId, ConversationNode } from '../types';
import MessageBubble from '../components/MessageBubble';
import CommitInputBar from '../components/CommitInputBar';

interface ChatViewProps {
  selectedModel: string;
}

export default function ChatView({ selectedModel }: ChatViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const nodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const commitMessage = useConversationStore((s) => s.commitMessage);
  const autoBranchingEnabled = useConversationStore((s) => s.autoBranchingEnabled);
  const setAutoBranchingEnabled = useConversationStore((s) => s.setAutoBranchingEnabled);

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
  }, [thread, streamingText]);

  const handleCommit = async (prompt: string, isSensitive: boolean) => {
    if (!activeConversationId) return;

    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setStreamingText('');
    setPendingPrompt(prompt);
    setError(null);

    let fullText = '';
    let backendNodeId: string | null = null;
    let backendParentId: string | null = null;

    try {
      const streamResult = await streamChat(
        {
          prompt,
          parent_id: headNodeId,
          root_id: activeConversationId,
          model: selectedModel as ModelId,
          auto_branching: autoBranchingEnabled,
        },
        controller.signal,
        (chunk) => {
          fullText += chunk.token;
          setStreamingText(fullText);
        },
      );
      backendNodeId = streamResult.nodeId;
      backendParentId = streamResult.parentId;

      // Use the backend's node_id so parent_id on the next message matches MongoDB
      commitMessage(
        prompt,
        fullText,
        selectedModel as ModelId,
        isSensitive,
        backendNodeId ?? undefined,
        backendParentId,
      );
      setStreamingText('');
      setPendingPrompt(null);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      console.error('Chat failed:', err);
      setError('Something went wrong. Check the console.');
      setPendingPrompt(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-tenet-bg">
      <div className="flex-1 overflow-y-auto min-h-0 px-6 py-6 space-y-2">
        {thread.length === 0 && !isLoading ? (
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
              isHead={node.node_id === headNodeId && !isLoading}
            />
          ))
        )}

        {/* Live streaming bubble */}
        {isLoading && (
          <div className="flex flex-col gap-3 mb-6">
            {/* Optimistic user prompt bubble */}
            {pendingPrompt && (
              <div className="flex justify-end">
                <div className="bg-gray-800 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[72%] text-sm leading-relaxed">
                  {pendingPrompt}
                </div>
              </div>
            )}

            {/* Streaming response bubble */}
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-tenet-teal/20 border border-tenet-teal/30 flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-tenet-teal text-xs font-bold">T</span>
              </div>
              <div className="bg-tenet-surface border-l-2 border-tenet-teal rounded-2xl px-4 py-3 max-w-2xl flex-1">
                {streamingText ? (
                  <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
                    <span className="inline-block w-1.5 h-4 bg-tenet-teal ml-0.5 animate-pulse align-middle" />
                  </div>
                ) : (
                  <span className="inline-flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-tenet-teal animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mx-auto max-w-lg bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="flex-shrink-0">
        <CommitInputBar
          onCommit={handleCommit}
          isLoading={isLoading}
          autoBranchingEnabled={autoBranchingEnabled}
          onToggleAutoBranching={() => setAutoBranchingEnabled(!autoBranchingEnabled)}
        />
      </div>
    </div>
  );
}
