import { useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Position,
  ReactFlowProvider,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';

import { useConversationStore } from '../store/useConversationStore';
import { fetchMerge } from '../api/client';
import type { ConversationNode } from '../types';
import ConversationNodeComponent from '../components/ConversationNode';
import type { ConversationNodeData } from '../components/ConversationNode';

interface BranchHistoryViewProps {
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
}

const nodeTypes = { conversationNode: ConversationNodeComponent };
const NODE_WIDTH = 260;
const TRUNK_X = 260;
const BRANCH_X = 680;
const START_Y = 80;
const ROW_GAP = 170;
const BRANCH_ROW_GAP = 120;

function getBranchLaneY(
  node: ConversationNode,
  fallbackY: number,
  posMap: Record<string, { x: number; y: number }>,
  branchCountsByParent: Record<string, number>,
) {
  const parentId = node.parent_id ?? 'root';
  const siblingIndex = branchCountsByParent[parentId] ?? 0;
  branchCountsByParent[parentId] = siblingIndex + 1;

  const parentY = node.parent_id ? posMap[node.parent_id]?.y : undefined;
  if (parentY === undefined) {
    return fallbackY;
  }

  return parentY + siblingIndex * BRANCH_ROW_GAP;
}

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------
const Y_STEP = 110;
const Y_START = 60;
const TRUNK_X = 160;
const BRANCH_BASE_X = 420;
const BRANCH_X_GAP = 220;

// ---------------------------------------------------------------------------
// Graph builder — layer-based layout (no node overlap)
// ---------------------------------------------------------------------------
function buildFlowGraph(
  storeNodes: Record<string, ConversationNode>,
  headNodeId: string | null,
  selectedNodeIds: string[],
  handlers: {
    onCheckout: (id: string) => void;
    onBranch: (id: string) => void;
    onPrune: (id: string) => void;
    onSelect: (id: string) => void;
  },
): { nodes: Node[]; edges: Edge[] } {
  // Filter pruned, sort by timestamp so parents are always processed before children
  const activeNodes = Object.values(storeNodes)
    .filter((n) => !n.pruned)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // --- Layer assignment: depth from root ---
  // Each node's layer = max(parent_layer, merge_parent_layer) + 1
  const layerMap: Record<string, number> = {};
  for (const node of activeNodes) {
    let layer = 0;
    if (node.parent_id && layerMap[node.parent_id] !== undefined) {
      layer = Math.max(layer, layerMap[node.parent_id] + 1);
    }
    if (node.merge_parent_id && layerMap[node.merge_parent_id] !== undefined) {
      layer = Math.max(layer, layerMap[node.merge_parent_id] + 1);
    }
    layerMap[node.node_id] = layer;
  }

  // --- Labels ---
  let trunkCount = 0;
  let branchCount = 0;
  const labelMap: Record<string, string> = {};
  const sublabelMap: Record<string, string> = {};

  for (const node of activeNodes) {
    if (node.branch_label) {
      branchCount += 1;
      const parentLabel = node.parent_id ? (labelMap[node.parent_id] ?? '?') : '?';
      labelMap[node.node_id] = `b${branchCount}/${parentLabel}`;
      sublabelMap[node.node_id] = node.branch_label;
    } else if (node.is_merge_node) {
      trunkCount += 1;
      labelMap[node.node_id] = `v${trunkCount}`;
      sublabelMap[node.node_id] = '⎇ Merge';
    } else {
      trunkCount += 1;
      labelMap[node.node_id] = `v${trunkCount}`;
      sublabelMap[node.node_id] = node.prompt.slice(0, 38) || 'Node';
    }
  }

  // Position assignment: keep the primary conversation and branches in
  // separate lanes so labels have enough room to breathe.
  let trunkY = START_Y;
  let fallbackBranchY = START_Y;

  const posMap: Record<string, { x: number; y: number }> = {};
  const branchCountsByParent: Record<string, number> = {};

    if (isBranch) {
      const branchY = getBranchLaneY(node, fallbackBranchY, posMap, branchCountsByParent);
      posMap[node.node_id] = { x: BRANCH_X, y: branchY };
      fallbackBranchY = Math.max(fallbackBranchY + ROW_GAP, branchY + ROW_GAP);
    } else {
      posMap[node.node_id] = { x: TRUNK_X, y: trunkY };
      trunkY += ROW_GAP;
    }
  }

  const occupiedRows = new Set<string>();
  for (const node of sorted) {
    const pos = posMap[node.node_id];
    const rowKey = `${pos.x}:${Math.round(pos.y / 20)}`;
    if (!occupiedRows.has(rowKey)) {
      occupiedRows.add(rowKey);
      continue;
    }

    let nextY = pos.y + BRANCH_ROW_GAP;
    let nextKey = `${pos.x}:${Math.round(nextY / 20)}`;
    while (occupiedRows.has(nextKey)) {
      nextY += BRANCH_ROW_GAP;
      nextKey = `${pos.x}:${Math.round(nextY / 20)}`;
    }
    posMap[node.node_id] = { ...pos, y: nextY };
    occupiedRows.add(nextKey);
  }

  // --- Flow nodes ---
  const flowNodes: Node[] = activeNodes.map((node) => {
    const data: ConversationNodeData = {
      label: labelMap[node.node_id] ?? node.node_id.slice(0, 8),
      sublabel: sublabelMap[node.node_id] ?? '',
      isHead: node.node_id === headNodeId,
      isBranch: node.branch_label !== null,
      isMerge: node.is_merge_node,
      isSelected: selectedNodeIds.includes(node.node_id),
      nodeId: node.node_id,
      ...handlers,
    };
    return {
      id: node.node_id,
      type: 'conversationNode',
      position: posMap[node.node_id] ?? { x: TRUNK_X, y: Y_START },
      data,
      style: { width: NODE_WIDTH },
      targetPosition: isBranch ? Position.Left : Position.Top,
      sourcePosition: isBranch ? Position.Right : Position.Bottom,
    });
  }

  // --- Flow edges ---
  // Trunk→trunk: straight down  (source bottom → target top)
  // Trunk→branch: curve right   (source right  → target left)
  // Branch→branch: straight down (source bottom → target top)
  const flowEdges: Edge[] = [];

  for (const node of activeNodes) {
    if (node.parent_id && storeNodes[node.parent_id] && !storeNodes[node.parent_id].pruned) {
      const edgeStyle = isBranch
        ? { stroke: '#555', strokeWidth: 1, strokeDasharray: '5 3' }
        : { stroke: '#333', strokeWidth: 1 };
      const sourcePos = posMap[node.parent_id];
      const targetPos = posMap[node.node_id];
      const isLateralEdge = sourcePos && targetPos && Math.abs(sourcePos.x - targetPos.x) > NODE_WIDTH;

      flowEdges.push({
        id: `e-${node.parent_id}-${node.node_id}`,
        source: node.parent_id,
        target: node.node_id,
        sourceHandle: isLateralEdge ? 'right' : 'bottom',
        targetHandle: isLateralEdge ? 'left' : 'top',
        animated: false,
        style: thisIsBranch
          ? { stroke: '#7c3aed', strokeWidth: 1.5, strokeDasharray: '6 3', opacity: 0.7 }
          : { stroke: '#2DD4BF', strokeWidth: 1.5, opacity: 0.35 },
      });
    }

    // Merge second-parent edge
    if (
      node.is_merge_node &&
      node.merge_parent_id &&
      storeNodes[node.merge_parent_id] &&
      !storeNodes[node.merge_parent_id].pruned
    ) {
      flowEdges.push({
        id: `e-merge-${node.merge_parent_id}-${node.node_id}`,
        source: node.merge_parent_id,
        target: node.node_id,
        sourceHandle: 'right',
        targetHandle: 'left',
        animated: false,
        style: { stroke: '#7c3aed', strokeWidth: 1.5, strokeDasharray: '6 3', opacity: 0.7 },
      });
    }
  }

  return { nodes: flowNodes, edges: flowEdges };
}

// ---------------------------------------------------------------------------
// Inner component (needs ReactFlowProvider context)
// ---------------------------------------------------------------------------
function BranchHistoryInner({ setActiveTab }: BranchHistoryViewProps) {
  const storeNodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const selectedNodeIds = useConversationStore((s) => s.selectedNodeIds);
  const checkoutNode = useConversationStore((s) => s.checkoutNode);
  const branchFromNode = useConversationStore((s) => s.branchFromNode);
  const pruneNode = useConversationStore((s) => s.pruneNode);
  const selectNodeForMerge = useConversationStore((s) => s.selectNodeForMerge);
  const mergeNodes = useConversationStore((s) => s.mergeNodes);
  const clearMergeSelection = useConversationStore((s) => s.clearMergeSelection);

  const handlers = {
    onCheckout: useCallback((id: string) => checkoutNode(id), [checkoutNode]),
    onBranch: useCallback(
      (id: string) => { branchFromNode(id, 'New Branch'); clearMergeSelection(); },
      [branchFromNode, clearMergeSelection],
    ),
    onPrune: useCallback((id: string) => pruneNode(id), [pruneNode]),
    onSelect: useCallback((id: string) => selectNodeForMerge(id), [selectNodeForMerge]),
  };

  const { nodes: builtNodes, edges: builtEdges } = buildFlowGraph(
    storeNodes,
    headNodeId,
    selectedNodeIds,
    handlers,
  );

  // Floating action bar handlers
  async function handleMerge() {
    if (selectedNodeIds.length !== 2) return;
    const [a, b] = selectedNodeIds;
    try {
      const result = await fetchMerge({ node_id_a: a, node_id_b: b });
      mergeNodes(a, b, result.response);
    } catch (err) {
      console.error('Merge failed:', err);
    }
  }

  function handleBranchFromSelected() {
    if (selectedNodeIds.length !== 1) return;
    branchFromNode(selectedNodeIds[0], 'New Branch');
    clearMergeSelection();
  }

  return (
    <div className="flex-1 flex flex-col relative" style={{ background: '#0B0B0C' }}>
      {/* Back button */}
      <div className="absolute top-3 left-3 z-10">
        <button
          onClick={() => setActiveTab('chats')}
          className="text-xs text-tenet-teal underline hover:opacity-80 transition-opacity"
        >
          ← Back to Chats
        </button>
      </div>

      {/* React Flow canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={builtNodes}
          edges={builtEdges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background color="#1e1e24" gap={20} />
          <Controls />
        </ReactFlow>
      </div>

      {/* Floating action bar */}
      {selectedNodeIds.length >= 1 && (
        <div
          className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-3 items-center bg-tenet-surface border border-tenet-border rounded-lg px-4 py-2 shadow-xl z-20"
          style={{ boxShadow: '0 4px 24px rgba(0,0,0,0.7)' }}
        >
          {selectedNodeIds.length === 2 && (
            <button
              onClick={handleMerge}
              className="px-4 py-1.5 rounded bg-tenet-teal text-black font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              Merge (Select 2)
            </button>
          )}
          {selectedNodeIds.length === 1 && (
            <button
              onClick={handleBranchFromSelected}
              className="px-4 py-1.5 rounded bg-tenet-purple text-white font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              ⎇ Branch from Here
            </button>
          )}
          <button
            onClick={clearMergeSelection}
            className="text-gray-400 text-xs hover:text-white transition-colors"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exported component (wrapped in ReactFlowProvider)
// ---------------------------------------------------------------------------
export default function BranchHistoryView({ setActiveTab }: BranchHistoryViewProps) {
  return (
    <ReactFlowProvider>
      <BranchHistoryInner setActiveTab={setActiveTab} />
    </ReactFlowProvider>
  );
}
