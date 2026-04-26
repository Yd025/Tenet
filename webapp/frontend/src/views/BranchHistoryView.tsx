import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { stratify, tree as d3Tree } from 'd3-hierarchy';
import type { HierarchyPointNode } from 'd3-hierarchy';
import { zoom as d3Zoom, zoomIdentity } from 'd3-zoom';
import { select } from 'd3-selection';
import 'd3-transition';

import { useConversationStore } from '../store/useConversationStore';
import { useThemeStore } from '../store/useThemeStore';
import { fetchMerge, fetchNodeSummaries } from '../api/client';
import type { MergeConflict, MergeResolution } from '../api/client';
import type { ConversationNode, ModelId } from '../types';
import ConversationNodeSVG from '../components/ConversationNode';
import type { ConversationNodeData } from '../components/ConversationNode';

interface BranchHistoryViewProps {
  setActiveTab: (tab: 'chats' | 'branch-history') => void;
  selectedModel: string;
}

const NODE_H_SPACING = 200;
const NODE_V_SPACING = 70;

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
    const metadata = node.metadata ?? {};
    const promptSnippet = (node.prompt || '').trim().split(/\s+/).slice(0, 5).join(' ');
    const responseSnippet = (node.response || '').trim().split(/\s+/).slice(0, 12).join(' ');

    if (node.is_merge_node) {
      trunkCount += 1;
      const prefix = `v${trunkCount}`;
      const summary = (metadata.summary_title as string) || 'Merge Synthesis';
      labelMap[node.node_id] = `${prefix}: ${summary}`;
      sublabelMap[node.node_id] = (metadata.summary_subtitle as string) || promptSnippet || '';
    } else if (node.branch_label) {
      branchCount += 1;
      const parentLabel = node.parent_id ? (labelMap[node.parent_id]?.split(':')[0] ?? '?') : '?';
      const prefix = `b${branchCount}/${parentLabel}`;
      const summary = (metadata.summary_title as string) || promptSnippet || node.branch_label;
      labelMap[node.node_id] = `${prefix}: ${summary}`;
      sublabelMap[node.node_id] = (metadata.summary_subtitle as string) || responseSnippet || '';
    } else {
      trunkCount += 1;
      const prefix = `v${trunkCount}`;
      const summary = (metadata.summary_title as string) || promptSnippet || 'Node';
      labelMap[node.node_id] = `${prefix}: ${summary}`;
      sublabelMap[node.node_id] = (metadata.summary_subtitle as string) || responseSnippet || '';
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
  const isDark = useThemeStore((s) => s.isDark);

  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const ctxMenuRef = useRef<HTMLDivElement>(null);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergeError, setMergeError] = useState<string | null>(null);
  const [pendingMergePair, setPendingMergePair] = useState<{ a: string; b: string } | null>(null);
  const [mergeConflicts, setMergeConflicts] = useState<MergeConflict[]>([]);
  const [conflictResolutions, setConflictResolutions] = useState<Record<string, MergeResolution>>({});
  const [mergeMode, setMergeMode] = useState(false);
  const [bookmarkedNodeIds, setBookmarkedNodeIds] = useState<Set<string>>(new Set());
  const [bookmarksExpanded, setBookmarksExpanded] = useState(true);
  const [hoverPreview, setHoverPreview] = useState<{ nodeId: string; x: number; y: number } | null>(null);

  const toggleBookmark = useCallback((nodeId: string) => {
    setBookmarkedNodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

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
      onDoubleClick: (id: string) => {
        checkoutNode(id);
        setActiveTab('chats');
      },
      onPreview: () => undefined,
      onHoverStart: (id: string, event: React.MouseEvent) => {
        setHoverPreview({ nodeId: id, x: event.clientX + 14, y: event.clientY + 14 });
      },
      onHoverMove: (id: string, event: React.MouseEvent) => {
        setHoverPreview({ nodeId: id, x: event.clientX + 14, y: event.clientY + 14 });
      },
      onHoverEnd: () => {
        setHoverPreview(null);
      },
    }),
    [checkoutNode, branchFromNode, pruneNode, selectNodeForMerge, clearMergeSelection, setActiveTab],
  );

  useEffect(() => {
    if (!activeConversationId) return;
    const activeNodes = Object.values(storeNodes).filter((n) => !n.pruned);
    if (activeNodes.length === 0) return;
    const missingIds = activeNodes
      .filter((n) => !(n.metadata?.summary_title && n.metadata?.summary_subtitle))
      .map((n) => n.node_id);
    if (missingIds.length === 0) return;

    let isCancelled = false;
    async function hydrateSummaries() {
      try {
        const result = await fetchNodeSummaries({
          root_id: activeConversationId,
          node_ids: missingIds,
          model: selectedModel as ModelId,
        });
        if (isCancelled) return;
        const byId = new Map(result.summaries.map((s) => [s.node_id, s]));
        useConversationStore.setState((state) => {
          const nextNodes = { ...state.nodes };
          for (const [nodeId, summary] of byId.entries()) {
            const existing = nextNodes[nodeId];
            if (!existing) continue;
            nextNodes[nodeId] = {
              ...existing,
              metadata: {
                ...(existing.metadata ?? {}),
                summary_title: summary.title,
                summary_subtitle: summary.subtitle,
              },
            };
          }
          return { nodes: nextNodes };
        });
      } catch (err) {
        console.error('Failed to load node summaries', err);
      }
    }

    hydrateSummaries();
    return () => {
      isCancelled = true;
    };
  }, [activeConversationId, storeNodes, selectedModel]);

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
    // Let node double-click open preview instead of triggering zoom-in.
    select(svg).on('dblclick.zoom', null);

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
    if (selectedNodeIds.length < 2) return;
    const rootId = activeConversationId ?? storeNodes[selectedNodeIds[0]]?.root_id ?? 'default';

    setMergeLoading(true);
    setMergeError(null);
    try {
      const result = await fetchMerge({ node_ids: selectedNodeIds, root_id: rootId, model: selectedModel });
      if (result.requires_resolution) {
        const defaults: Record<string, MergeResolution> = {};
        for (const c of result.conflicts) {
          defaults[c.id] = { id: c.id, choice: 'left' };
        }
        setPendingMergePair({ a: selectedNodeIds[0], b: selectedNodeIds[1] });
        setMergeConflicts(result.conflicts);
        setConflictResolutions(defaults);
        return;
      }
      if (!result.node_id) throw new Error('Merge completed without node_id');
      mergeNodes(selectedNodeIds[0], selectedNodeIds[1], result.response, result.node_id);
      clearMergeSelection();
      setMergeMode(false);
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

    setMergeLoading(true);
    setMergeError(null);
    try {
      const result = await fetchMerge({
        node_ids: [pendingMergePair.a, pendingMergePair.b],
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

  const panToNode = useCallback((nodeId: string) => {
    const svg = svgRef.current;
    const zoomBehavior = zoomBehaviorRef.current;
    if (!svg || !zoomBehavior) return;

    const target = layoutNodes.find((n) => n.data.id === nodeId);
    if (!target) return;

    const svgRect = svg.getBoundingClientRect();
    const svgW = svgRect.width || 800;
    const svgH = svgRect.height || 600;
    const scale = 1.5;

    select(svg)
      .transition()
      .duration(500)
      .call(
        zoomBehavior.transform,
        zoomIdentity.translate(svgW / 2 - target.x * scale, svgH / 2 - target.y * scale).scale(scale),
      );
  }, [layoutNodes]);

  const nodeCount = Object.values(storeNodes).filter((n) => !n.pruned).length;

  // All branch nodes are pink; merge nodes are purple; trunk is cyan
  const firstBranchSet = useMemo(() => {
    return new Set(
      Object.values(storeNodes)
        .filter((n) => !n.pruned && n.branch_label !== null)
        .map((n) => n.node_id)
    );
  }, [storeNodes]);

  return (
    <div className="flex-1 flex flex-col relative" style={{ background: isDark ? '#1a1a1e' : '#f0f0f2' }}>
      {/* Header bar */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between">
        <button
          onClick={() => setActiveTab('chats')}
          className={`text-xs underline hover:opacity-80 transition-opacity ${isDark ? 'text-[#2DD4BF]' : 'text-[#0d9488]'}`}
        >
          &larr; Back to Chats
        </button>
        <div className="flex items-center gap-2">
          {/* Merge mode toggle */}
          <button
            onClick={() => { setMergeMode((m) => !m); clearMergeSelection(); }}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium ${
              mergeMode
                ? 'bg-[#7c3aed] border-[#7c3aed] text-white'
                : isDark
                  ? 'border-[#1e1e24] text-gray-400 hover:text-white hover:border-gray-500'
                  : 'border-gray-300 text-gray-500 hover:text-gray-800 hover:border-gray-400'
            }`}
          >
            {mergeMode ? '⌥ Merge Mode ON' : '⌥ Merge Mode'}
          </button>
          <span className={`text-xs font-mono ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>{nodeCount} node{nodeCount !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Empty state */}
      {layoutNodes.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <p className={`text-sm ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>No conversation nodes yet. Start chatting to build your branch history.</p>
        </div>
      )}

      {/* SVG canvas */}
      <svg ref={svgRef} className="flex-1 w-full h-full" style={{ minHeight: 0 }}
        onClick={() => ctxMenu && setCtxMenu(null)}
      >
        <g ref={gRef}>
          {layoutNodes.map((node) => {
            if (!node.parent) return null;
            const n = node.data.node;
            const isMerge = n.is_merge_node;
            const isBranch = n.branch_label !== null;
            const isFirst = firstBranchSet.has(n.node_id);
            let stroke = '#2DD4BF';
            if (isMerge) stroke = '#7c3aed';
            else if (isBranch) stroke = isFirst ? '#ec4899' : '#2DD4BF';
            return (
              <path
                key={`link-${node.data.id}`}
                d={linkPath(node.parent.x, node.parent.y, node.x, node.y)}
                fill="none"
                stroke={stroke}
                strokeWidth={1.5}
                strokeDasharray={isBranch || isMerge ? '6 3' : undefined}
                opacity={isBranch || isMerge ? 0.7 : 0.35}
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
              isBookmarked: bookmarkedNodeIds.has(d.node_id),
              isFirstBranch: firstBranchSet.has(d.node_id),
              isInMergeMode: mergeMode,
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
          className={`fixed z-50 border rounded shadow-lg py-1 min-w-max ${isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200'}`}          style={{ left: ctxMenu.x, top: ctxMenu.y, boxShadow: '0 4px 16px rgba(0,0,0,0.6)' }}
        >
          <button
            className={`block w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition-colors ${isDark ? 'text-white' : 'text-gray-800 hover:bg-black/5'}`}
            onClick={() => { handlers.onBranch(ctxMenu.nodeId); setCtxMenu(null); setActiveTab('chats'); }}
          >
            &#x238B; Branch from Here
          </button>
          <button
            className="block w-full text-left px-4 py-2 text-sm text-amber-400 hover:bg-white/10 transition-colors"
            onClick={() => { toggleBookmark(ctxMenu.nodeId); setCtxMenu(null); }}
          >
            {bookmarkedNodeIds.has(ctxMenu.nodeId) ? '★ Remove Bookmark' : '☆ Bookmark'}
          </button>
          <button
            className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            onClick={() => {
              if (!confirm('Prune this node and all its descendants? This cannot be undone.')) return;
              handlers.onPrune(ctxMenu.nodeId);
              setCtxMenu(null);
            }}
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

      {mergeConflicts.length > 0 && pendingMergePair && (
        <div className="absolute inset-0 z-40 bg-black/60 flex items-center justify-center px-4">
          <div className={`w-full max-w-lg border rounded-xl p-4 ${isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Resolve Conflicts</h3>
              <button className={isDark ? 'text-gray-400 hover:text-white' : 'text-gray-400 hover:text-gray-900'}
                onClick={() => { setPendingMergePair(null); setMergeConflicts([]); setConflictResolutions({}); }}>✕</button>
            </div>

            <div className="space-y-2">
              {mergeConflicts.map((conflict) => {
                const resolution = conflictResolutions[conflict.id];
                return (
                  <div key={conflict.id} className={`border rounded-lg p-3 ${isDark ? 'border-[#1e1e24]' : 'border-gray-200'}`}>
                    <p className={`text-xs mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{conflict.why_conflict}</p>
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      <button
                        onClick={() => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'left' } }))}
                        className={`text-xs rounded-lg p-2 border text-left transition-colors ${
                          resolution?.choice === 'left'
                            ? 'border-teal-400 bg-teal-500/10 text-teal-300'
                            : isDark ? 'border-[#1e1e24] text-gray-300 hover:border-gray-500' : 'border-gray-200 text-gray-700 hover:border-gray-400'
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wide mb-0.5 opacity-60">Left</div>
                        {conflict.left_claim}
                      </button>
                      <button
                        onClick={() => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'right' } }))}
                        className={`text-xs rounded-lg p-2 border text-left transition-colors ${
                          resolution?.choice === 'right'
                            ? 'border-purple-400 bg-purple-500/10 text-purple-300'
                            : isDark ? 'border-[#1e1e24] text-gray-300 hover:border-gray-500' : 'border-gray-200 text-gray-700 hover:border-gray-400'
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wide mb-0.5 opacity-60">Right</div>
                        {conflict.right_claim}
                      </button>
                    </div>
                    <button
                      onClick={() => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'custom', custom_resolution: prev[conflict.id]?.custom_resolution ?? '' } }))}
                      className={`w-full text-xs rounded-lg px-2 py-1.5 border text-left transition-colors ${
                        resolution?.choice === 'custom'
                          ? 'border-amber-400 bg-amber-500/10 text-amber-300'
                          : isDark ? 'border-[#1e1e24] text-gray-400 hover:border-gray-500' : 'border-gray-200 text-gray-500 hover:border-gray-400'
                      }`}
                    >
                      ✏ Custom resolution
                    </button>
                    {resolution?.choice === 'custom' && (
                      <textarea
                        value={resolution.custom_resolution ?? ''}
                        onChange={(e) => setConflictResolutions((prev) => ({ ...prev, [conflict.id]: { id: conflict.id, choice: 'custom', custom_resolution: e.target.value } }))}
                        className={`mt-2 w-full text-xs rounded p-2 border resize-none ${isDark ? 'bg-black/30 border-[#1e1e24] text-gray-100 placeholder-gray-600' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-400'}`}
                        rows={2}
                        placeholder="Describe how to resolve this conflict..."
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-3 flex justify-end gap-2">
              <button className={`px-3 py-1.5 text-xs rounded border ${isDark ? 'border-[#1e1e24] text-gray-400 hover:text-white' : 'border-gray-200 text-gray-500 hover:text-gray-900'}`}
                onClick={() => { setPendingMergePair(null); setMergeConflicts([]); setConflictResolutions({}); }}>
                Cancel
              </button>
              <button
                className="px-3 py-1.5 text-xs rounded bg-[#7c3aed] text-white font-semibold hover:opacity-90 disabled:opacity-50"
                onClick={handleResolveAndMerge} disabled={mergeLoading}>
                {mergeLoading ? 'Merging…' : 'Merge'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Small hover preview */}
      {hoverPreview && storeNodes[hoverPreview.nodeId] && (
        <div
          className={`fixed z-40 w-80 max-w-[85vw] border rounded-lg backdrop-blur px-3 py-2 pointer-events-none ${
            isDark ? 'border-[#1e1e24] bg-[#111114]/95' : 'border-gray-200 bg-white/95 shadow-lg'
          }`}
          style={{ left: hoverPreview.x, top: hoverPreview.y }}
        >
          <div className={`text-xs font-semibold truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {(storeNodes[hoverPreview.nodeId].metadata?.summary_title as string) || 'Node Preview'}
          </div>
          <div className={`mt-1 text-[11px] ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>
            {storeNodes[hoverPreview.nodeId].prompt.slice(0, 120)}
            {storeNodes[hoverPreview.nodeId].prompt.length > 120 ? '…' : ''}
          </div>
          <div className={`mt-1 text-[11px] ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            {storeNodes[hoverPreview.nodeId].response.slice(0, 220)}
            {storeNodes[hoverPreview.nodeId].response.length > 220 ? '…' : ''}
          </div>
        </div>
      )}

      {/* Floating action bar — only shown in merge mode */}
      {mergeMode && (
        <div
          className={`absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-3 items-center border rounded-lg px-4 py-2 shadow-xl z-20 ${
            isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200'
          }`}
          style={{ boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}
        >
          <span className={`text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            {selectedNodeIds.length}/5 selected
          </span>

          {selectedNodeIds.length >= 2 && (
            <button
              onClick={handleMerge}
              disabled={mergeLoading}
              className={`px-4 py-1.5 rounded font-semibold text-sm transition-opacity text-white ${
                mergeLoading ? 'opacity-50 cursor-not-allowed bg-[#7c3aed]' : 'bg-[#7c3aed] hover:opacity-90'
              }`}
            >
              {mergeLoading ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Merging…
                </span>
              ) : (
                `⌥ Merge ${selectedNodeIds.length} Nodes`
              )}
            </button>
          )}

          {selectedNodeIds.length === 0 && (
            <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              Click nodes to select (2–5)
            </span>
          )}

          <button
            onClick={() => { clearMergeSelection(); setMergeMode(false); }}
            className={`text-xs transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-400 hover:text-gray-900'}`}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Bookmarks card */}
      <div
        className={`absolute bottom-4 right-4 z-20 w-80 border rounded-lg shadow-xl overflow-hidden ${
          isDark ? 'bg-[#111114] border-[#1e1e24]' : 'bg-white border-gray-200'
        }`}
        style={{ boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}
      >
        <button
          className={`w-full flex items-center justify-between px-4 py-3 text-sm font-semibold transition-colors ${
            isDark ? 'text-white hover:bg-white/5' : 'text-gray-800 hover:bg-gray-50'
          }`}
          onClick={() => setBookmarksExpanded((v) => !v)}
        >
          <span>★ Bookmarks ({bookmarkedNodeIds.size})</span>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>{bookmarksExpanded ? '▾' : '▸'}</span>
        </button>

        {bookmarksExpanded && (
          <div className={`max-h-64 overflow-y-auto border-t ${isDark ? 'border-[#1e1e24]' : 'border-gray-200'}`}>
            {bookmarkedNodeIds.size === 0 ? (
              <p className={`text-xs px-4 py-3 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                No bookmarks yet. Right-click a node to bookmark it.
              </p>
            ) : (
              [...bookmarkedNodeIds].map((nodeId) => {
                const label = labelMap[nodeId] ?? nodeId.slice(0, 8);
                const sublabel = sublabelMap[nodeId] ?? '';
                return (
                  <div
                    key={nodeId}
                    className={`flex items-center gap-2 px-4 py-2.5 transition-colors group ${
                      isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'
                    }`}
                  >
                    <button
                      className="flex-1 text-left min-w-0"
                      onClick={() => { panToNode(nodeId); checkoutNode(nodeId); }}
                    >
                      <div className={`text-sm font-medium truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>{label}</div>
                      <div className={`text-xs truncate mt-0.5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{sublabel}</div>
                    </button>
                    <button
                      className="text-gray-600 hover:text-amber-400 text-sm opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                      onClick={() => toggleBookmark(nodeId)}
                      title="Remove bookmark"
                    >
                      ✕
                    </button>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
