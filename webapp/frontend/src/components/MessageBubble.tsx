import type { ConversationNode } from '../types';

interface MessageBubbleProps {
  node: ConversationNode;
  isHead: boolean;
}

export default function MessageBubble({ node, isHead }: MessageBubbleProps) {
  const modelLabel = `${node.model_used} • local`;

  return (
    <div className="mb-6 flex flex-col gap-3">
      {/* User prompt — right-aligned */}
      <div className="flex justify-end">
        <div className="bg-gray-800 text-white rounded-2xl px-4 py-3 max-w-[70%] ml-auto">
          {node.prompt}
        </div>
      </div>

      {/* AI response — left-aligned, only if response exists */}
      {node.response && (
        <div className="flex flex-col items-start">
          {node.is_merge_node && (
            <span className="text-xs bg-tenet-teal/20 text-tenet-teal border border-tenet-teal/30 rounded-full px-2 py-0.5 mb-1">
              ⎇ Synthesis Commit
            </span>
          )}
          <div
            className={`bg-tenet-surface text-gray-200 rounded-2xl px-4 py-3 max-w-[75%] border-l-2 border-tenet-teal ${
              isHead ? 'ring-1 ring-tenet-teal/30' : ''
            }`}
          >
            {node.response}
          </div>
          <span className="text-xs text-gray-600 mt-1 ml-1">{modelLabel}</span>
        </div>
      )}
    </div>
  );
}
