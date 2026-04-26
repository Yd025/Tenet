import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { stratify, tree as d3Tree } from 'd3-hierarchy';
import type { HierarchyPointNode } from 'd3-hierarchy';
import { zoom as d3Zoom, zoomIdentity } from 'd3-zoom';
import { select } from 'd3-selection';

import { useConversationStore } from '../store/useConversationStore';
import { fetchMerge } from '../api/client';
import type { MergeConflict, MergeResolution } from '../api/client';
import type { ConversationNode } from '../types';
import ConversationNodeSVG from '../components/ConversationNode';
import type { ConversationNodeData } from '../components/ConversationNode';

interface BranchHistoryViewProps {
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
  selectedModel: string;
}

const NODE_H_SPACING = 180;
const NODE_V_SPACING = 90;

interface TreeDatum {
  id: string;
  parentId: string | null;
  node: ConversationNode;
}

function buildTreeData(storeNodes: Record<string, ConversationNode>): TreeDatum[] {
  const active = Object.values(storeNodes).filter((n) => !n.pruned);
  return active.map((n) => ({
    id: n.node_id,
    parentId: n.parent_id,
    node: n,
  }));
}

function buildLabels(storeNodes: Record<string, ConversationNode>) {
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
      sublabelMap[node.node_id] = node.prompt.slice(0, 38) || node.branch_label;
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

function linkPath(sx: number, sy: number, tx: number, ty: number): string {
  const midY = (sy + ty) / 2;
  return `M${sx},${sy} C${sx},${midY} ${tx},${midY} ${tx},${ty}`;
}

export default function BranchHistoryView({ setActiveTab, selectedModel }: BranchHistoryViewProps) {
  const storeNodes = useConversationStore((s) => s.nodes);
  const headNodeId = useConversationStore((s) => s.headNodeId);
  const selectedNodeIds = useConversationStore((s) => s.selectedNodeIds);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const checkoutNode = useConversationStore((s) => s.checkoutNode);
  const branchFromNode = useConversationStore((s) => s.branchFromNode);
  const pruneNode = useConversationStore((s) => s.pruneNode);
  const selectNodeForMerge = useConversationStore((s) => s.selectNodeForMerge);
  const mergeNodes = useConversationStore((s) => s.mergeNodes);
  const clearMergeSelection = useConversationStore((s) => s.clearMergeSelection);

  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const ctxMenuRef = useRef<HTMLDivElement>(null);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergeError, setMergeError] = useState<string | null>(null);
  const [pendingMergePair, setPendingMergePair] = useState<{ a: string; b: string } | null>(null);
  const [mergeConflicts, setMergeConflicts] = useState<MergeConflict[]>([]);
  const [conflictResolutions, setConflictResolutions] = useState<Record<string, MergeResolution>>({});

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

  const { layoutNodes, mergeEdges } = useMemo(() => {
    const treeData = buildTreeData(storeNodes);
    if (treeData.length === 0) {
      return {
        layoutNodes: [] as HierarchyPointNode<TreeDatum>[],
        mergeEdges: [] as { source: HierarchyPointNode<TreeDatum>; target: HierarchyPointNode<TreeDatum> }[],
      };
    }

    const activeIds = new Set(treeData.map((d) => d.id));
    const cleaned = treeData.map((d) => ({
      ...d,
      parentId: d.parentId && activeIds.has(d.parentId) ? d.parentId : null,
    }));

    const roots = cleaned.filter((d) => d.parentId === null);
    if (roots.length === 0) return { layoutNodes: [], mergeEdges: [] };

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

  const zoomBehaviorRef = useRef<ReturnType<typeof d3Zoom<SVGSVGElement, unknown>> | null>(null);

  // Set up zoom once on mount
  useEffect(() => {
    const svg = svgRef.current;
    const g = gRef.current;
    if (!svg || !g) return;

    const zoomBehavior = d3Zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        select(g).attr('transform', event.transform.toString());
      });

    zoomBehaviorRef.current = zoomBehavior;
    select(svg).call(zoomBehavior);

    return () => {
      select(svg).on('.zoom', null);
    };
  }, []);

  // Fit view only when the node count changes (new nodes added or first load)
  const prevNodeCount = useRef(0);
  useEffect(() => {
    const svg = svgRef.current;
    const zoomBehavior = zoomBehaviorRef.current;
    if (!svg || !zoomBehavior || layoutNodes.length === 0) return;
    if (layoutNodes.length === prevNodeCount.current) return;
    prevNodeCount.current = layoutNodes.length;

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

    select(svg).call(
      zoomBehavior.transform,
      zoomIdentity.translate(svgW / 2 - cx * scale, svgH / 2 - cy * scale).scale(scale),
    );
  }, [layoutNodes]);

  const handleNodeContextMenu = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.preventDefault();
      setCtxMenu({ x: e.clientX, y: e.clientY, nodeId });
    },
    [],
  );

  async function handleMerge() {
    if (selectedNodeIds.length !== 2) return;
    const [a, b] = selectedNodeIds;
    const rootId = activeConversationId ?? storeNodes[a]?.root_id ?? 'default';

    setMergeLoading(true);
    setMergeError(null);
    try {
      const result = await fetchMerge({ node_id_a: a, node_id_b: b, root_id: rootId, model: selectedModel });
      if (result.requires_resolution) {
        const defaults: Record<string, MergeResolution> = {};
        for (const c of result.conflicts) {
          defaults[c.id] = { id: c.id, choice: 'left' };
        }
        setPendingMergePair({ a, b });
        setMergeConflicts(result.conflicts);
        setConflictResolutions(defaults);
        return;
      }
      if (!result.node_id) {
        throw new Error('Merge completed without node_id');
      }
      mergeNodes(a, b, result.response, result.node_id);
    } catch (err) {
      console.error('Merge failed:', err);
      setMergeError('Merge failed — check console for details.');
    } finally {
      setMergeLoading(false);
    }
  }

  async function handleResolveAndMerge() {
    if (!pendingMergePair) return;
    const rootId = activeConversationId ?? storeNodes[pendingMergePair.a]?.root_id ?? 'default';
    const resolutions = Object.values(conflictResolutions);
    if (resolutions.length !== mergeConflicts.length) {
      setMergeError('Please resolve all conflicts before merging.');
      return;
    }

    setMergeLoading(true);
    setMergeError(null);
    try {
      const result = await fetchMerge({
        node_id_a: pendingMergePair.a,
        node_id_b: pendingMergePair.b,
        root_id: rootId,
        model: selectedModel,
        conflict_resolutions: resolutions,
      });
      if (result.requires_resolution || !result.node_id) {
        throw new Error('Merge still requires resolution.');
      }
      mergeNodes(pendingMergePair.a, pendingMergePair.b, result.response, result.node_id);
      setPendingMergePair(null);
      setMergeConflicts([]);
      setConflictResolutions({});
    } catch (err) {
      console.error('Conflict-resolved merge failed:', err);
      setMergeError('Conflict-resolved merge failed — check console for details.');
    } finally {
      setMergeLoading(false);
    }
  }

  function handleBranchFromSelected() {
    if (selectedNodeIds.length !== 1) return;
    branchFromNode(selectedNodeIds[0], 'New Branch');
    clearMergeSelection();
    setActiveTab('chats');
  }

  const nodeCount = Object.values(storeNodes).filter((n) => !n.pruned).length;

  return (
    <div className="flex-1 flex flex-col relative" style={{ background: '#0B0B0C' }}>
      {/* Header bar */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between">
        <button
          onClick={() => setActiveTab('chats')}
          className="text-xs text-tenet-teal underline hover:opacity-80 transition-opacity"
        >
          &larr; Back to Chats
        </button>
        <span className="text-xs text-gray-600 font-mono">{nodeCount} node{nodeCount !== 1 ? 's' : ''}</span>
      </div>

      {/* Empty state */}
      {layoutNodes.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-600 text-sm">No conversation nodes yet. Start chatting to build your branch history.</p>
        </div>
      )}

      {/* SVG canvas */}
      <svg ref={svgRef} className="flex-1 w-full h-full" style={{ minHeight: 0 }}>
        <g ref={gRef}>
          {layoutNodes.map((node) => {
            if (!node.parent) return null;
            const isBranch = node.data.node.branch_label !== null || node.data.node.is_merge_node;
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

      {/* Context menu */}
      {ctxMenu && (
        <div
          ref={ctxMenuRef}
          className="fixed z-50 bg-tenet-surface border border-tenet-border rounded shadow-lg py-1 min-w-max"
          style={{ left: ctxMenu.x, top: ctxMenu.y, boxShadow: '0 4px 16px rgba(0,0,0,0.6)' }}
        >
          <button
            className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors"
            onClick={() => { handlers.onBranch(ctxMenu.nodeId); setCtxMenu(null); setActiveTab('chats'); }}
          >
            &#x238B; Branch from Here
          </button>
          <button
            className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            onClick={() => { handlers.onPrune(ctxMenu.nodeId); setCtxMenu(null); }}
          >
            &#x2702; Prune
          </button>
        </div>
      )}

      {/* Merge error toast */}
      {mergeError && (
        <div className="absolute top-12 left-1/2 -translate-x-1/2 z-30 bg-red-900/80 border border-red-700/50 rounded px-4 py-2 text-xs text-red-300">
          {mergeError}
          <button className="ml-3 text-red-400 hover:text-white" onClick={() => setMergeError(null)}>✕</button>
        </div>
      )}

      {/* Conflict resolver modal */}
      {mergeConflicts.length > 0 && pendingMergePair && (
        <div className="absolute inset-0 z-40 bg-black/60 flex items-center justify-center px-4">
          <div className="w-full max-w-3xl max-h-[80vh] overflow-auto bg-tenet-surface border border-tenet-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Resolve Merge Conflicts</h3>
              <button
                className="text-gray-400 hover:text-white"
                onClick={() => {
                  setPendingMergePair(null);
                  setMergeConflicts([]);
                  setConflictResolutions({});
                }}
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Conflicting ideas were detected. Choose how each conflict should be resolved before merge.
            </p>

            <div className="space-y-3">
              {mergeConflicts.map((conflict) => {
                const resolution = conflictResolutions[conflict.id];
                return (
                  <div key={conflict.id} className="border border-tenet-border rounded-lg p-3 bg-black/20">
                    <p className="text-xs text-gray-300 mb-2">{conflict.why_conflict || 'Potential contradiction detected.'}</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                      <div className="border border-teal-500/30 bg-teal-500/5 rounded-md p-2">
                        <div className="text-[11px] uppercase tracking-wide text-teal-300 mb-1">Left</div>
                        <div className="text-xs text-gray-100 leading-relaxed">{conflict.left_claim}</div>
                      </div>
                      <div className="border border-purple-500/30 bg-purple-500/5 rounded-md p-2">
                        <div className="text-[11px] uppercase tracking-wide text-purple-300 mb-1">Right</div>
                        <div className="text-xs text-gray-100 leading-relaxed">{conflict.right_claim}</div>
                      </div>
                    </div>

                    <div className="flex gap-2 mb-2">
                      <button
                        className={`px-2 py-1 text-xs rounded border ${resolution?.choice === 'left' ? 'border-teal-400 text-teal-300' : 'border-tenet-border text-gray-300'}`}
                        onClick={() => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'left' } }))}
                      >
                        Keep Left
                      </button>
                      <button
                        className={`px-2 py-1 text-xs rounded border ${resolution?.choice === 'right' ? 'border-purple-400 text-purple-300' : 'border-tenet-border text-gray-300'}`}
                        onClick={() => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'right' } }))}
                      >
                        Keep Right
                      </button>
                      <button
                        className={`px-2 py-1 text-xs rounded border ${resolution?.choice === 'custom' ? 'border-amber-400 text-amber-300' : 'border-tenet-border text-gray-300'}`}
                        onClick={() =>
                          setConflictResolutions((prev) => ({
                            ...prev,
                            [conflict.id]: {
                              id: conflict.id,
                              choice: 'custom',
                              custom_resolution: prev[conflict.id]?.custom_resolution ?? '',
                            },
                          }))
                        }
                      >
                        Custom
                      </button>
                    </div>

                    {resolution?.choice === 'custom' && (
                      <textarea
                        value={resolution.custom_resolution ?? ''}
                        onChange={(e) =>
                          setConflictResolutions((prev) => ({
                            ...prev,
                            [conflict.id]: {
                              id: conflict.id,
                              choice: 'custom',
                              custom_resolution: e.target.value,
                            },
                          }))
                        }
                        className="w-full text-xs bg-black/30 border border-tenet-border rounded p-2 text-gray-100"
                        placeholder="Describe your preferred merged truth for this conflict..."
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-1.5 text-xs rounded border border-tenet-border text-gray-300 hover:text-white"
                onClick={() => {
                  setPendingMergePair(null);
                  setMergeConflicts([]);
                  setConflictResolutions({});
                }}
              >
                Cancel
              </button>
              <button
                className="px-3 py-1.5 text-xs rounded bg-tenet-teal text-black font-semibold hover:opacity-90 disabled:opacity-50"
                onClick={handleResolveAndMerge}
                disabled={mergeLoading}
              >
                {mergeLoading ? 'Merging…' : 'Resolve and Merge'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating action bar */}
      {selectedNodeIds.length >= 1 && (
        <div
          className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-3 items-center bg-tenet-surface border border-tenet-border rounded-lg px-4 py-2 shadow-xl z-20"
          style={{ boxShadow: '0 4px 24px rgba(0,0,0,0.7)' }}
        >
          {/* Selection indicator */}
          <span className="text-xs text-gray-500 font-mono">
            {selectedNodeIds.length}/2 selected
          </span>

          {selectedNodeIds.length === 2 && (
            <button
              onClick={handleMerge}
              disabled={mergeLoading}
              className={`px-4 py-1.5 rounded bg-tenet-teal text-black font-semibold text-sm transition-opacity ${
                mergeLoading ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-90'
              }`}
            >
              {mergeLoading ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="w-3 h-3 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  Merging…
                </span>
              ) : (
                '⌥ Merge Nodes'
              )}
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
