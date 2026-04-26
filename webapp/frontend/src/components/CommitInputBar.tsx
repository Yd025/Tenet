import { useState, useRef } from 'react';
import { GitBranch } from 'lucide-react';
import { useThemeStore } from '../store/useThemeStore';

interface CommitInputBarProps {
  onCommit: (prompt: string) => Promise<void>;
  isLoading: boolean;
  autoBranchingEnabled: boolean;
  onToggleAutoBranching: () => void;
}

export default function CommitInputBar({
  onCommit,
  isLoading,
  autoBranchingEnabled,
  onToggleAutoBranching,
}: CommitInputBarProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isDark = useThemeStore((s) => s.isDark);

  const handleSubmit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput('');
    await onCommit(trimmed);
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const teal = isDark ? '#2DD4BF' : '#0d9488';

  return (
    <div className={`border-t px-4 py-3 ${isDark ? 'border-[#1e1e24] bg-[#1a1a1e]' : 'border-gray-200 bg-[#f0f0f2]'}`}>
      <div className={`flex items-center gap-3 rounded-xl px-4 py-2 border ${
        isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200 shadow-sm'
      }`}>
        <GitBranch style={{ color: teal }} className="w-4 h-4 flex-shrink-0" />

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Commit Prompt..."
          className={`flex-1 bg-transparent outline-none resize-none text-sm leading-relaxed ${
            isDark ? 'text-white placeholder-gray-600' : 'text-gray-900 placeholder-gray-500'
          }`}
        />

        <button
          onClick={onToggleAutoBranching}
          type="button"
          title="Automatically pick the best node to branch from"
          className={`flex-shrink-0 rounded-md px-2 py-1 text-xs border transition-colors ${
            autoBranchingEnabled
              ? ''
              : isDark
                ? 'border-[#1e1e24] text-gray-400 hover:text-gray-200'
                : 'border-gray-400 text-gray-600 hover:text-gray-900'
          }`}
          style={autoBranchingEnabled ? { borderColor: teal, color: teal, backgroundColor: `${teal}18` } : {}}
        >
          Auto Branch
        </button>

        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className={`flex-shrink-0 font-medium rounded-lg px-4 py-1.5 text-sm transition-opacity ${
            isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-90'
          }`}
          style={{ backgroundColor: teal, color: isDark ? '#000' : '#fff' }}
        >
          Commit ↑
        </button>
      </div>
    </div>
  );
}
