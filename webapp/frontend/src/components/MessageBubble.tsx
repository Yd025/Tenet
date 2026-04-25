import type { ConversationNode } from '../types';

interface MessageBubbleProps {
  node: ConversationNode;
  isHead: boolean;
}

export default function MessageBubble({ node, isHead }: MessageBubbleProps) {
  const modelLabel = node.model_used === 'deepseek' ? 'DeepSeek R1 • local' : 'Qwen 2.5 • local';

  // Skip nodes that are empty branch stubs (no prompt yet)
  if (!node.prompt && !node.response) return null;

  return (
    <div className="mb-6 flex flex-col gap-3">
      {/* User prompt — right-aligned */}
      {node.prompt && (
        <div className="flex justify-end">
          <div className="bg-gray-800 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[72%] text-sm leading-relaxed">
            {node.prompt}
          </div>
        </div>
      )}

      {/* AI response — left-aligned with avatar */}
      {node.response && (
        <div className="flex items-start gap-3">
          {/* Bot avatar */}
          <div className="w-7 h-7 rounded-full bg-tenet-teal/20 border border-tenet-teal/30 flex items-center justify-center flex-shrink-0 mt-1">
            <span className="text-tenet-teal text-xs font-bold">T</span>
          </div>

          <div className="flex flex-col items-start flex-1 min-w-0">
            {node.is_merge_node && (
              <span className="text-xs bg-tenet-teal/20 text-tenet-teal border border-tenet-teal/30 rounded-full px-2 py-0.5 mb-1.5">
                ⎇ Synthesis Commit
              </span>
            )}
            <div
              className={`bg-tenet-surface text-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[90%] text-sm leading-relaxed whitespace-pre-wrap ${
                isHead ? 'ring-1 ring-tenet-teal/30' : ''
              }`}
            >
              {node.response}
            </div>
            <span className="text-xs text-gray-600 mt-1 ml-1">{modelLabel}</span>
          </div>
        </div>
      )}
    </div>
  );
}
