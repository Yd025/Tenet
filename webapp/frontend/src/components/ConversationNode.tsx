import { useThemeStore } from '../store/useThemeStore';

export interface ConversationNodeData {
  label: string;
  sublabel: string;
  isHead: boolean;
  isBranch: boolean;
  isMerge: boolean;
  isSelected: boolean;
  isBookmarked: boolean;
  isFirstBranch: boolean;
  isInMergeMode: boolean; // when true, click = select for merge; otherwise click = checkout
  nodeId: string;
  onCheckout: (id: string) => void;
  onBranch: (id: string) => void;
  onPrune: (id: string) => void;
  onSelect: (id: string) => void;
  onPreview: (id: string) => void;
  onHoverStart: (id: string, event: React.MouseEvent) => void;
  onHoverMove: (id: string, event: React.MouseEvent) => void;
  onHoverEnd: () => void;
  onDoubleClick: (id: string) => void;
}

interface ConversationNodeSVGProps {
  data: ConversationNodeData;
  x: number;
  y: number;
  onContextMenu: (e: React.MouseEvent, nodeId: string) => void;
}

const NODE_RADIUS = 8;

// Color palette
const TEAL   = '#2DD4BF';
const PINK   = '#ec4899';
const PURPLE = '#7c3aed';

export default function ConversationNodeSVG({ data, x, y, onContextMenu }: ConversationNodeSVGProps) {
  const isDark = useThemeStore((s) => s.isDark);
  const labelColor = isDark ? '#e5e7eb' : '#111114';   // softer than pure white
  const sublabelColor = isDark ? '#6b7280' : '#9ca3af';
  function handleClick() {
    if (data.isInMergeMode) {
      data.onSelect(data.nodeId);
    } else {
      data.onCheckout(data.nodeId);
    }
  }
  function handleDblClick() { data.onDoubleClick(data.nodeId); }
  function handleCtx(e: React.MouseEvent) { e.preventDefault(); onContextMenu(e, data.nodeId); }

  let fill: string;
  let gradientId: string | undefined;

  if (data.isMerge) {
    gradientId = `merge-grad-${data.nodeId}`;
    fill = `url(#${gradientId})`;
  } else if (data.isBranch) {
    // First branch off a node = pink, subsequent = cyan (after prune promotes to main)
    fill = data.isFirstBranch ? PINK : TEAL;
  } else {
    fill = TEAL;
  }

  // Link color exported for use in BranchHistoryView
  const linkColor = data.isMerge ? PURPLE : data.isBranch ? (data.isFirstBranch ? PINK : TEAL) : TEAL;

  return (
    <g
      transform={`translate(${x},${y})`}
      onClick={handleClick}
      onDoubleClick={handleDblClick}
      onContextMenu={handleCtx}
      onMouseEnter={(e) => data.onHoverStart(data.nodeId, e)}
      onMouseMove={(e) => data.onHoverMove(data.nodeId, e)}
      onMouseLeave={data.onHoverEnd}
      style={{ cursor: 'pointer' }}
      data-link-color={linkColor}
    >
      {gradientId && (
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="50%" stopColor={TEAL} />
            <stop offset="50%" stopColor={PURPLE} />
          </linearGradient>
        </defs>
      )}

      {data.isHead && (
        <defs>
          <filter id={`glow-${data.nodeId}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      )}

      {/* Selection ring */}
      {data.isSelected && (
        <circle r={NODE_RADIUS + 4} fill="none" stroke="white" strokeWidth={2} />
      )}

      {/* Main circle */}
      <circle
        r={NODE_RADIUS}
        fill={fill}
        filter={data.isHead ? `url(#glow-${data.nodeId})` : undefined}
      />

      {/* Bookmark star indicator */}
      {data.isBookmarked && (
        <text
          x={-NODE_RADIUS - 2}
          y={-NODE_RADIUS - 2}
          fill="#f59e0b"
          fontSize={10}
          textAnchor="middle"
          dominantBaseline="auto"
        >★</text>
      )}

      {/* Head ring */}
      {data.isHead && (
        <circle r={NODE_RADIUS + 2} fill="none" stroke={fill} strokeWidth={1.5} opacity={0.6} />
      )}

      {/* Label — prefix in teal/accent, summary in normal color */}
      <text x={NODE_RADIUS + 8} y={-2} fontSize={11} fontWeight={600} dominantBaseline="auto" fontFamily="ui-monospace, monospace">
        {(() => {
          const colonIdx = data.label.indexOf(': ');
          if (colonIdx === -1) return <tspan fill={labelColor}>{data.label}</tspan>;
          const prefix = data.label.slice(0, colonIdx + 1);
          const title = data.label.slice(colonIdx + 2);
          return (
            <>
              <tspan fill={isDark ? '#2DD4BF' : '#0d9488'} fontWeight={700}>{prefix}</tspan>
              <tspan fill={labelColor} fontWeight={500} fontFamily="system-ui, sans-serif"> {title.slice(0, 22)}{title.length > 22 ? '…' : ''}</tspan>
            </>
          );
        })()}
      </text>

      {/* Sublabel */}
      <text x={NODE_RADIUS + 8} y={13} fill={sublabelColor} fontSize={9} fontWeight={400} dominantBaseline="auto" fontFamily="system-ui, sans-serif">
        {data.sublabel.slice(0, 30)}{data.sublabel.length > 30 ? '…' : ''}
      </text>

      {/* Hit area */}
      <rect
        x={-NODE_RADIUS - 4}
        y={-NODE_RADIUS - 4}
        width={180}
        height={NODE_RADIUS * 2 + 8}
        fill="transparent"
      />
    </g>
  );
}
