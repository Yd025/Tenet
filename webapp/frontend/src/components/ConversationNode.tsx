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

interface ConversationNodeSVGProps {
  data: ConversationNodeData;
  x: number;
  y: number;
  onContextMenu: (e: React.MouseEvent, nodeId: string) => void;
}

const NODE_RADIUS = 8;

export default function ConversationNodeSVG({
  data,
  x,
  y,
  onContextMenu,
}: ConversationNodeSVGProps) {
  function handleClick() {
    data.onCheckout(data.nodeId);
    data.onSelect(data.nodeId);
  }

  function handleCtx(e: React.MouseEvent) {
    e.preventDefault();
    onContextMenu(e, data.nodeId);
  }

  let fill: string;
  let gradientId: string | undefined;

  if (data.isMerge) {
    gradientId = `merge-grad-${data.nodeId}`;
    fill = `url(#${gradientId})`;
  } else if (data.isBranch) {
    fill = '#7c3aed';
  } else {
    fill = '#2DD4BF';
  }

  return (
    <g
      transform={`translate(${x},${y})`}
      onClick={handleClick}
      onContextMenu={handleCtx}
      style={{ cursor: 'pointer' }}
    >
      {gradientId && (
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="50%" stopColor="#2DD4BF" />
            <stop offset="50%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
      )}

      {/* Glow filter for head node */}
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
        <circle
          r={NODE_RADIUS + 4}
          fill="none"
          stroke="white"
          strokeWidth={2}
        />
      )}

      {/* Main circle */}
      <circle
        r={NODE_RADIUS}
        fill={fill}
        filter={data.isHead ? `url(#glow-${data.nodeId})` : undefined}
      />

      {/* Head indicator ring */}
      {data.isHead && (
        <circle
          r={NODE_RADIUS + 2}
          fill="none"
          stroke="#2DD4BF"
          strokeWidth={1.5}
          opacity={0.6}
        />
      )}

      {/* Label */}
      <text
        x={NODE_RADIUS + 8}
        y={-2}
        fill="white"
        fontSize={12}
        fontWeight={700}
        dominantBaseline="auto"
      >
        {data.label}
      </text>

      {/* Sublabel */}
      <text
        x={NODE_RADIUS + 8}
        y={12}
        fill="#6b7280"
        fontSize={10}
        dominantBaseline="auto"
      >
        {data.sublabel}
      </text>

      {/* Invisible hit area for easier clicking */}
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
