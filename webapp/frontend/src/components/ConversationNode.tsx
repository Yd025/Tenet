import { useState, useEffect, useRef } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';

export interface ConversationNodeData {
  label: string;
  sublabel: string;
  isHead: boolean;
  isBranch: boolean;
  isMerge: boolean;
  isSelected: boolean;
  nodeId: string;
  onCheckout: (id: string) => void;
  onBranch: (id: string) => void;
  onPrune: (id: string) => void;
  onSelect: (id: string) => void;
}

export default function ConversationNodeComponent({ data }: NodeProps<ConversationNodeData>) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  function handleClick() {
    data.onCheckout(data.nodeId);
    data.onSelect(data.nodeId);
  }

  function handleContextMenu(e: React.MouseEvent) {
    e.preventDefault();
    setMenuOpen(true);
  }

  function handleBranch() {
    data.onBranch(data.nodeId);
    setMenuOpen(false);
  }

  function handlePrune() {
    data.onPrune(data.nodeId);
    setMenuOpen(false);
  }

  // Dot styling
  let dotBg: string;
  let dotStyle: React.CSSProperties = { width: 14, height: 14, borderRadius: '50%', flexShrink: 0 };

  if (data.isMerge) {
    dotBg = '';
    dotStyle = {
      ...dotStyle,
      background: 'linear-gradient(135deg, #2DD4BF 50%, #7c3aed 50%)',
    };
  } else if (data.isBranch) {
    dotBg = 'bg-tenet-purple';
  } else {
    dotBg = 'bg-tenet-teal';
  }

  if (data.isHead) {
    dotStyle = { ...dotStyle, boxShadow: '0 0 12px 3px rgba(45, 212, 191, 0.4)' };
  }

  const ringClass = data.isSelected ? 'ring-2 ring-white' : '';

  return (
    <div style={{ position: 'relative' }}>
      {/* React Flow handles */}
      <Handle type="target" position={Position.Top}    id="top"    style={{ opacity: 0, width: 1, height: 1 }} />
      <Handle type="source" position={Position.Bottom} id="bottom" style={{ opacity: 0, width: 1, height: 1 }} />
      <Handle type="source" position={Position.Right}  id="right"  style={{ opacity: 0, width: 1, height: 1 }} />
      <Handle type="target" position={Position.Left}   id="left"   style={{ opacity: 0, width: 1, height: 1 }} />

      {/* Node body */}
      <div
        className="flex items-center gap-2 cursor-pointer select-none px-2 py-1 rounded hover:bg-white/5 transition-colors"
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Circle dot */}
        <div
          className={`${dotBg} ${ringClass} rounded-full`}
          style={dotStyle}
        />

        {/* Labels */}
        <div className="flex flex-col leading-tight">
          <span className="text-white font-bold text-sm">{data.label}</span>
          <span className="text-gray-500 text-xs">{data.sublabel}</span>
        </div>
      </div>

      {/* Context menu */}
      {menuOpen && (
        <div
          ref={menuRef}
          className="absolute z-50 left-8 top-0 bg-tenet-surface border border-tenet-border rounded shadow-lg py-1 min-w-max"
          style={{ boxShadow: '0 4px 16px rgba(0,0,0,0.6)' }}
        >
          <button
            className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors"
            onClick={handleBranch}
          >
            ⎇ Branch from Here
          </button>
          <button
            className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            onClick={handlePrune}
          >
            ✂ Prune
          </button>
        </div>
      )}
    </div>
  );
}
