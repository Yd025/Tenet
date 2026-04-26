import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ConversationNode } from '../types';
import { useThemeStore } from '../store/useThemeStore';

interface MessageBubbleProps {
  node: ConversationNode;
  isHead: boolean;
  // When true, only render the user prompt (used for the optimistic bubble while streaming)
  promptOnly?: boolean;
}

const modelLabels: Record<string, string> = {
  system: 'System',
  gemma4: 'Gemma 4 • local',
  'gemma4:latest': 'Gemma 4 • local',
  'gemma4:e4b': 'Gemma 4 E4B • local',
  deepseek: 'DeepSeek R1 • local',
  'deepseek-r1:latest': 'DeepSeek R1 • local',
  qwen: 'Qwen 2.5 • local',
  'qwen2.5:latest': 'Qwen 2.5 • local',
  'qwen2.5-7b': 'Qwen 2.5 7B • local',
  'qwen3.6:latest': 'Qwen 3.6 • local',
  'qwen3.5:9b': 'Qwen 3.5 9B • local',
  'mistral-small3.2:24b': 'Mistral Small 3.2 24B • local',
  'ministral-3:8b': 'Ministral 3 8B • local',
};

export default function MessageBubble({ node, isHead, promptOnly = false }: MessageBubbleProps) {
  const raw = node.model_used ?? '';
  const modelLabel = modelLabels[raw] ?? (raw ? `${raw} • local` : 'local');
  const isDark = useThemeStore((s) => s.isDark);

  if (!node.prompt && !node.response) return null;

  return (
    <div className="mb-6 flex flex-col gap-3">
      {/* User prompt bubble */}
      {node.prompt && (
        <div className="flex justify-end">
          <div className={`rounded-2xl rounded-tr-sm px-4 py-3 max-w-[72%] text-sm leading-relaxed ${
            isDark ? 'bg-gray-800 text-white' : 'bg-gray-200 text-gray-900'
          }`}>
            {node.prompt}
          </div>
        </div>
      )}

      {/* AI response */}
      {!promptOnly && node.response && (
        <div className="flex items-start gap-3">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
            isDark ? 'bg-[#2DD4BF]/20 border border-[#2DD4BF]/30' : 'bg-[#0d9488]/20 border border-[#0d9488]/30'
          }`}>
            <span className={`text-xs font-bold ${isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]'}`}>T</span>
          </div>

          <div className="flex flex-col items-start flex-1 min-w-0">
            {node.is_merge_node && (
              <span className={`text-xs rounded-full px-2 py-0.5 mb-1.5 border ${
                isDark ? 'bg-[#2DD4BF]/20 text-[#2DD4BF] border-[#2DD4BF]/30' : 'bg-[#0d9488]/20 text-[#0d9488] border-[#0d9488]/30'
              }`}>
                ⎇ Synthesis Commit
              </span>
            )}
            <div className={`rounded-2xl rounded-tl-sm px-4 py-3 w-full text-sm leading-relaxed prose prose-sm max-w-none ${
              isDark
                ? `bg-[#111114] text-gray-200 prose-invert ${isHead ? 'ring-1 ring-[#2DD4BF]/30' : ''}`
                : `bg-white text-gray-800 shadow-sm ${isHead ? 'ring-1 ring-[#0d9488]/30' : ''}`
            }`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{node.response}</ReactMarkdown>
            </div>
            <span className={`text-xs mt-1 ml-1 ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>{modelLabel}</span>
          </div>
        </div>
      )}
    </div>
  );
}
