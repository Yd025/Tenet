import { useState, useRef } from 'react';
import { GitBranch, Lock, Unlock } from 'lucide-react';

interface CommitInputBarProps {
  onCommit: (prompt: string, isSensitive: boolean) => Promise<void>;
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
  const [isSensitive, setIsSensitive] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    await onCommit(trimmed, isSensitive);
    setInput('');
    setIsSensitive(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-tenet-border bg-tenet-bg px-4 py-3">
      <div className="flex items-center gap-3 bg-tenet-surface rounded-xl px-4 py-2 border border-tenet-border">
        {/* Left: branch icon */}
        <GitBranch className="text-tenet-teal w-4 h-4 flex-shrink-0" />

        {/* Center: textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Commit Prompt..."
          className="flex-1 bg-transparent text-white placeholder-gray-600 outline-none resize-none text-sm leading-relaxed"
        />

        {/* Lock toggle */}
        <button
          onClick={() => setIsSensitive((s) => !s)}
          title="Mark as sensitive (routes to privacy model)"
          className={`flex-shrink-0 transition-colors ${
            isSensitive ? 'text-amber-400' : 'text-gray-600'
          }`}
        >
          {isSensitive ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
        </button>

        <button
          onClick={onToggleAutoBranching}
          type="button"
          title="Automatically pick the best node to branch from"
          className={`flex-shrink-0 rounded-md px-2 py-1 text-xs border transition-colors ${
            autoBranchingEnabled
              ? 'border-tenet-teal text-tenet-teal bg-tenet-teal/10'
              : 'border-tenet-border text-gray-400 hover:text-gray-200'
          }`}
        >
          Auto Branch
        </button>

        {/* Commit button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className={`flex-shrink-0 bg-tenet-teal text-black font-medium rounded-lg px-4 py-1.5 text-sm transition-opacity ${
            isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-90'
          }`}
        >
          Commit ↑
        </button>
      </div>
    </div>
  );
}
