import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { stratify, tree as d3Tree } from 'd3-hierarchy';
import type { HierarchyPointNode } from 'd3-hierarchy';
import { zoom as d3Zoom, zoomIdentity } from 'd3-zoom';
import { select } from 'd3-selection';

import { useConversationStore } from '../store/useConversationStore';
import { fetchMerge } from '../api/client';
import type { ConversationNode } from '../types';
import ConversationNodeSVG from '../components/ConversationNode';
import type { ConversationNodeData } from '../components/ConversationNode';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface BranchHistoryViewProps {
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
}

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------
const NODE_H_SPACING = 180;
const NODE_V_SPACING = 90;

// ---------------------------------------------------------------------------
// Hierarchy builder
// ---------------------------------------------------------------------------

interface TreeDatum {
  id: string;
  parentId: string | null;
  node: ConversationNode;
}

function buildTreeData(
  storeNodes: Record<string, ConversationNode>,
): TreeDatum[] {
  const active = Object.values(storeNodes).filter((n) => !n.pruned);
  return active.map((n) => ({
    id: n.node_id,
    parentId: n.parent_id,
    node: n,
  }));
}

function buildLabels(
  storeNodes: Record<string, ConversationNode>,
): { labelMap: Record<string, string>; sublabelMap: Record<string, string> } {
  const activeNodes = Object.values(storeNodes)
    .filter((n) => !n.pruned)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

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
      sublabelMap[node.node_id] = '\u238B Merge';
    } else {
      trunkCount += 1;
      labelMap[node.node_id] = `v${trunkCount}`;
      sublabelMap[node.node_id] = node.prompt.slice(0, 38) || 'Node';
    }
  }

  return { labelMap, sublabelMap };
}

// ---------------------------------------------------------------------------
// Curved link path generator (vertical orientation)
// ---------------------------------------------------------------------------
function linkPath(
  sx: number,
  sy: number,
  tx: number,
  ty: number,
): string {
  const midY = (sy + ty) / 2;
  return `M${sx},${sy} C${sx},${midY} ${tx},${midY} ${tx},${ty}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function BranchHistoryView({ setActiveTab }: BranchHistoryViewProps) {
  const storeNodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const selectedNodeIds = useConversationStore((s) => s.selectedNodeIds);
  const checkoutNode = useConversationStore((s) => s.checkoutNode);
  const branchFromNode = useConversationStore((s) => s.branchFromNode);
  const pruneNode = useConversationStore((s) => s.pruneNode);
  const selectNodeForMerge = useConversationStore((s) => s.selectNodeForMerge);
  const mergeNodes = useConversationStore((s) => s.mergeNodes);
  const clearMergeSelection = useConversationStore((s) => s.clearMergeSelection);

  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);

  // Context menu state
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const ctxMenuRef = useRef<HTMLDivElement>(null);

  // Close context menu on outside click
  useEffect(() => {
    if (!ctxMenu) return;
    function handleClickOutside(e: MouseEvent) {
      if (ctxMenuRef.current && !ctxMenuRef.current.contains(e.target as Node)) {
        setCtxMenu(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [ctxMenu]);

  const handlers = useMemo(
    () => ({
      onCheckout: checkoutNode,
      onBranch: (id: string) => {
        branchFromNode(id, 'New Branch');
        clearMergeSelection();
      },
      onPrune: pruneNode,
      onSelect: selectNodeForMerge,
    }),
    [checkoutNode, branchFromNode, pruneNode, selectNodeForMerge, clearMergeSelection],
  );

  // ---------------------------------------------------------------------------
  // D3 hierarchy layout
  // ---------------------------------------------------------------------------
  const { layoutNodes, mergeEdges } = useMemo(() => {
    const treeData = buildTreeData(storeNodes);
    if (treeData.length === 0) {
      return { layoutNodes: [] as HierarchyPointNode<TreeDatum>[], mergeEdges: [] as { source: HierarchyPointNode<TreeDatum>; target: HierarchyPointNode<TreeDatum> }[] };
    }

    // Orphan guard: ensure every parentId points to an active node
    const activeIds = new Set(treeData.map((d) => d.id));
    const cleaned = treeData.map((d) => ({
      ...d,
      parentId: d.parentId && activeIds.has(d.parentId) ? d.parentId : null,
    }));

    // Ensure exactly one root
    const roots = cleaned.filter((d) => d.parentId === null);
    if (roots.length === 0) return { layoutNodes: [], mergeEdges: [] };

    // If multiple roots, attach extras to first root
    if (roots.length > 1) {
      const primaryRoot = roots[0];
      for (let i = 1; i < roots.length; i++) {
        const orphan = cleaned.find((d) => d.id === roots[i].id);
        if (orphan) orphan.parentId = primaryRoot.id;
      }
    }

    const stratifier = stratify<TreeDatum>()
      .id((d) => d.id)
      .parentId((d) => d.parentId);

    const root = stratifier(cleaned);
    const layout = d3Tree<TreeDatum>().nodeSize([NODE_H_SPACING, NODE_V_SPACING]);
    const laidOut = layout(root);

    const nodes = laidOut.descendants();

    // Build merge edges (not part of tree hierarchy)
    const nodeById = new Map(nodes.map((n) => [n.data.id, n]));
    const mEdges: { source: HierarchyPointNode<TreeDatum>; target: HierarchyPointNode<TreeDatum> }[] = [];
    for (const n of nodes) {
      const mergeParentId = n.data.node.merge_parent_id;
      if (mergeParentId && nodeById.has(mergeParentId)) {
        mEdges.push({ source: nodeById.get(mergeParentId)!, target: n });
      }
    }

    return { layoutNodes: nodes, mergeEdges: mEdges };
  }, [storeNodes]);

  const { labelMap, sublabelMap } = useMemo(() => buildLabels(storeNodes), [storeNodes]);

  // ---------------------------------------------------------------------------
  // Zoom setup
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const svg = svgRef.current;
    const g = gRef.current;
    if (!svg || !g) return;

    const zoomBehavior = d3Zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        select(g).attr('transform', event.transform.toString());
      });

    const svgSel = select(svg);
    svgSel.call(zoomBehavior);

    // Fit view on data change
    if (layoutNodes.length > 0) {
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const n of layoutNodes) {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }

      const padding = 80;
      const treeWidth = maxX - minX + padding * 2;
      const treeHeight = maxY - minY + padding * 2;

      const svgRect = svg.getBoundingClientRect();
      const svgW = svgRect.width || 800;
      const svgH = svgRect.height || 600;

      const scale = Math.min(svgW / treeWidth, svgH / treeHeight, 1.5);
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      const tx = svgW / 2 - cx * scale;
      const ty = svgH / 2 - cy * scale;

      svgSel.call(
        zoomBehavior.transform,
        zoomIdentity.translate(tx, ty).scale(scale),
      );
    }

    return () => {
      svgSel.on('.zoom', null);
    };
  }, [layoutNodes]);

  // ---------------------------------------------------------------------------
  // Context menu handler (from SVG node)
  // ---------------------------------------------------------------------------
  const handleNodeContextMenu = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.preventDefault();
      setCtxMenu({ x: e.clientX, y: e.clientY, nodeId });
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Floating action bar handlers
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex-1 flex flex-col relative" style={{ background: '#0B0B0C' }}>
      {/* Back button */}
      <div className="absolute top-3 left-3 z-10">
        <button
          onClick={() => setActiveTab('chats')}
          className="text-xs text-tenet-teal underline hover:opacity-80 transition-opacity"
        >
          &larr; Back to Chats
        </button>
      </div>

      {/* SVG canvas */}
      <svg
        ref={svgRef}
        className="flex-1 w-full h-full"
        style={{ minHeight: 0 }}
      >
        <g ref={gRef}>
          {/* Tree links */}
          {layoutNodes.map((node) => {
            if (!node.parent) return null;
            const isBranch =
              node.data.node.branch_label !== null || node.data.node.is_merge_node;
            return (
              <path
                key={`link-${node.data.id}`}
                d={linkPath(node.parent.x, node.parent.y, node.x, node.y)}
                fill="none"
                stroke={isBranch ? '#7c3aed' : '#2DD4BF'}
                strokeWidth={1.5}
                strokeDasharray={isBranch ? '6 3' : undefined}
                opacity={isBranch ? 0.7 : 0.35}
              />
            );
          })}

          {/* Merge links */}
          {mergeEdges.map((edge) => (
            <path
              key={`merge-${edge.source.data.id}-${edge.target.data.id}`}
              d={linkPath(edge.source.x, edge.source.y, edge.target.x, edge.target.y)}
              fill="none"
              stroke="#7c3aed"
              strokeWidth={1.5}
              strokeDasharray="6 3"
              opacity={0.7}
            />
          ))}

          {/* Nodes */}
          {layoutNodes.map((node) => {
            const d = node.data.node;
            const nodeData: ConversationNodeData = {
              label: labelMap[d.node_id] ?? d.node_id.slice(0, 8),
              sublabel: sublabelMap[d.node_id] ?? '',
              isHead: d.node_id === headNodeId,
              isBranch: d.branch_label !== null,
              isMerge: d.is_merge_node,
              isSelected: selectedNodeIds.includes(d.node_id),
              nodeId: d.node_id,
              ...handlers,
            };
            return (
              <ConversationNodeSVG
                key={node.data.id}
                data={nodeData}
                x={node.x}
                y={node.y}
                onContextMenu={handleNodeContextMenu}
              />
            );
          })}
        </g>
      </svg>

      {/* Context menu (HTML overlay) */}
      {ctxMenu && (
        <div
          ref={ctxMenuRef}
          className="fixed z-50 bg-tenet-surface border border-tenet-border rounded shadow-lg py-1 min-w-max"
          style={{
            left: ctxMenu.x,
            top: ctxMenu.y,
            boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
          }}
        >
          <button
            className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors"
            onClick={() => {
              handlers.onBranch(ctxMenu.nodeId);
              setCtxMenu(null);
            }}
          >
            &#x238B; Branch from Here
          </button>
          <button
            className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            onClick={() => {
              handlers.onPrune(ctxMenu.nodeId);
              setCtxMenu(null);
            }}
          >
            &#x2702; Prune
          </button>
        </div>
      )}

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
              &#x238B; Branch from Here
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
