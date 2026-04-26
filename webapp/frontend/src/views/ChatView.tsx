import { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
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
  const [failedPrompt, setFailedPrompt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const nodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const commitMessage = useConversationStore((s) => s.commitMessage);
  const autoBranchingEnabled = useConversationStore((s) => s.autoBranchingEnabled);
  const setAutoBranchingEnabled = useConversationStore((s) => s.setAutoBranchingEnabled);
  const setLastTps = useConversationStore((s) => s.setLastTps);
  const bumpLastMessageAt = () => useConversationStore.setState((s) => ({ lastMessageAt: Date.now() }));
  const isDark = useThemeStore((s) => s.isDark);

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
    if (isStreamingRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'instant' });
    } else {
      const id = setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 50);
      return () => clearTimeout(id);
    }
  }, [thread, streamingText, pendingPrompt]);

  // Abort any in-flight stream when the conversation changes
  useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
    setStreamingText('');
    setPendingPrompt(null);
    setFailedPrompt(null);
    setError(null);
  }, [activeConversationId]);

  const handleCommit = async (prompt: string) => {
    if (!activeConversationId) return;

    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setStreamingText('');
    setPendingPrompt(prompt);
    setError(null);
    isStreamingRef.current = true;
    bumpLastMessageAt(); // move conversation to top of sidebar immediately

    let fullText = '';
    let backendNodeId: string | null = null;
    let backendParentId: string | null = null;
    let lastChunkTps = 0;

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
          if (chunk.tps > 0) lastChunkTps = chunk.tps;
        },
      );
      backendNodeId = streamResult.nodeId;
      backendParentId = streamResult.parentId;

      if (lastChunkTps > 0) setLastTps(lastChunkTps);
      backendNodeId = streamResult.nodeId;
      backendParentId = streamResult.parentId;

      // Use the backend's node_id so parent_id on the next message matches MongoDB
      commitMessage(
        prompt,
        fullText,
        selectedModel as ModelId,
        backendNodeId ?? undefined,
        backendParentId,
      );
      setStreamingText('');
      setPendingPrompt(null);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      console.error('Chat failed:', err);
      setError(`Failed to get a response. The model may not be available. Your prompt: "${prompt}"`);
      setFailedPrompt(prompt);
      setPendingPrompt(null);
    } finally {
      isStreamingRef.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div className={`flex-1 flex flex-col min-h-0 ${isDark ? 'bg-[#1a1a1e]' : 'bg-[#f0f0f2]'}`}>
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
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${isDark ? 'bg-[#2DD4BF]/20 border border-[#2DD4BF]/30' : 'bg-[#0d9488]/20 border border-[#0d9488]/30'}`}>
                <span className={`text-xs font-bold ${isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]'}`}>T</span>
              </div>
              <div className={`rounded-2xl rounded-tl-sm px-4 py-3 flex-1 min-w-0 border-l-2 ${isDark ? 'bg-[#111114] border-[#2DD4BF]' : 'bg-white border-[#0d9488] shadow-sm'}`}>
                {streamingText ? (
                  <div className={`text-sm leading-relaxed prose prose-sm max-w-none ${isDark ? 'text-gray-200 prose-invert' : 'text-gray-800'}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
                    <span className={`inline-block w-1.5 h-4 ml-0.5 animate-pulse align-middle ${isDark ? 'bg-[#2DD4BF]' : 'bg-[#0d9488]'}`} />
                  </div>
                ) : (
                  <span className="inline-flex gap-1 items-center">
                    <span className={`w-1.5 h-1.5 rounded-full animate-bounce ${isDark ? 'bg-[#2DD4BF]' : 'bg-[#0d9488]'}`} style={{ animationDelay: '0ms' }} />
                    <span className={`w-1.5 h-1.5 rounded-full animate-bounce ${isDark ? 'bg-[#2DD4BF]' : 'bg-[#0d9488]'}`} style={{ animationDelay: '150ms' }} />
                    <span className={`w-1.5 h-1.5 rounded-full animate-bounce ${isDark ? 'bg-[#2DD4BF]' : 'bg-[#0d9488]'}`} style={{ animationDelay: '300ms' }} />
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mx-auto max-w-lg bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-3 text-sm text-red-300">
            <p className="mb-1">Model unavailable or request failed.</p>
            {failedPrompt && (
              <div className={`mt-2 rounded px-3 py-2 text-xs font-mono ${isDark ? 'bg-black/30 text-gray-300' : 'bg-red-50 text-gray-700'}`}>
                {failedPrompt}
              </div>
            )}
            <div className="flex gap-2 mt-2">
              {failedPrompt && (
                <button
                  onClick={() => { navigator.clipboard.writeText(failedPrompt); }}
                  className="text-xs text-red-400 hover:text-red-200 underline"
                >
                  Copy prompt
                </button>
              )}
              <button onClick={() => { setError(null); setFailedPrompt(null); }} className="text-xs text-red-400 hover:text-red-200 underline ml-auto">
                Dismiss
              </button>
            </div>
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
