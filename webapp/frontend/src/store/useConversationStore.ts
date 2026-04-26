import { create } from 'zustand';
import type { ConversationNode, Conversation, ModelId } from '../types';

interface ConversationStore {
  nodes: Record<string, ConversationNode>;
  conversations: Conversation[];
  activeConversationId: string | null;
  headNodeId: string | null;
  selectedNodeIds: string[];
  autoBranchingEnabled: boolean;
  lastMessageAt: number; // increments on each commit to trigger sidebar refresh
  lastTps: number | null;

  // actions
  loadNodes: (nodes: ConversationNode[]) => void;
  startConversation: (title: string) => void;
  commitMessage: (
    prompt: string,
    response: string,
    model: ModelId,
    backendNodeId?: string,
    parentNodeId?: string | null,
  ) => void;
  checkoutNode: (nodeId: string) => void;
  branchFromNode: (nodeId: string, label: string) => string;
  pruneNode: (nodeId: string) => void;
  mergeNodes: (
    nodeIdA: string,
    nodeIdB: string,
    synthesisResponse: string,
    mergeNodeId?: string,
  ) => void;
  selectNodeForMerge: (nodeId: string) => void;
  clearMergeSelection: () => void;
  setActiveConversation: (id: string | null) => void;
  setAutoBranchingEnabled: (enabled: boolean) => void;
  deleteLocalConversation: (id: string) => void;
  setLastTps: (tps: number) => void;
  getThreadToHead: () => ConversationNode[];
}

function collectDescendants(
  nodeId: string,
  nodes: Record<string, ConversationNode>,
): string[] {
  const result: string[] = [nodeId];
  const node = nodes[nodeId];
  if (!node) return result;
  for (const childId of node.children_ids) {
    result.push(...collectDescendants(childId, nodes));
  }
  return result;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  nodes: {},
  conversations: [],
  activeConversationId: null,
  headNodeId: null,
  selectedNodeIds: [],
  autoBranchingEnabled: false,
  lastMessageAt: 0,
  lastTps: null,

  // Load nodes fetched from the backend into the store.
  // Reconstructs children_ids from parent_ids since the backend doesn't store them.
  loadNodes: (incoming: ConversationNode[]) => {
    const nodes: Record<string, ConversationNode> = {};

    for (const n of incoming) {
      nodes[n.node_id] = {
        ...n,
        conversation_id: n.conversation_id ?? n.root_id,
        parent_id: n.parent_ids?.[0] ?? null,
        merge_parent_id: n.parent_ids?.[1] ?? null,
        children_ids: [],
        branch_label: n.branch_label ?? null,
        is_merge_node: (n.parent_ids?.length ?? 0) > 1,
        pruned: n.pruned ?? false,
        execution_context: 'local',
        is_sensitive: n.is_sensitive ?? false,
        model_used: (n.model_used as ModelId) ?? ((n as any).metadata?.model as ModelId) ?? 'gemma4',
      };
    }

    for (const n of Object.values(nodes)) {
      for (const pid of n.parent_ids ?? []) {
        if (nodes[pid]) {
          nodes[pid].children_ids = [...new Set([...nodes[pid].children_ids, n.node_id])];
        }
      }
    }

    // Infer branch_label for nodes that diverge from the trunk.
    // Sort by timestamp — the first non-merge child of each parent is trunk, subsequent are branches.
    const sortedNodes = Object.values(nodes).sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    const firstNonMergeChildSeen = new Set<string>();
    for (const n of sortedNodes) {
      if (n.is_merge_node || !n.parent_id || n.branch_label) continue;
      if (firstNonMergeChildSeen.has(n.parent_id)) {
        nodes[n.node_id] = { ...nodes[n.node_id], branch_label: 'Branch' };
      } else {
        firstNonMergeChildSeen.add(n.parent_id);
      }
    }

    const leaves = Object.values(nodes).filter((n) => n.children_ids.length === 0 && !n.pruned);
    // Sort by timestamp descending — most recently active leaf becomes head
    const head = leaves.sort((a, b) => {
      const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return tb - ta;
    })[0];

    set((state) => ({
      nodes,
      // Only reset headNodeId if it hasn't been explicitly set since the last
      // setActiveConversation call (i.e. it's still null from the clear).
      // This preserves a headNodeId set by branchFromNode before loadNodes resolves.
      headNodeId: state.headNodeId === null ? (head?.node_id ?? null) : state.headNodeId,
    }));
  },

  startConversation: (title: string) => {
    const id = crypto.randomUUID();
    const newConv: Conversation = {
      id,
      title,
      root_node_id: null,
      created_at: new Date().toISOString(),
    };
    set((state) => ({
      conversations: [...state.conversations, newConv],
      activeConversationId: id,
      headNodeId: null,
      nodes: {},
    }));
  },

  commitMessage: (
    prompt: string,
    response: string,
    model: ModelId,
    backendNodeId?: string,
    parentNodeId?: string | null,
  ) => {
    const nodeId = backendNodeId ?? crypto.randomUUID();
    const timestamp = new Date().toISOString();

    set((state) => {
      const { activeConversationId, headNodeId } = state;
      if (!activeConversationId) return {};
      const effectiveParentId = parentNodeId === undefined ? headNodeId : parentNodeId;

      const parentHasNonMergeChildren =
        effectiveParentId != null &&
        state.nodes[effectiveParentId] != null &&
        state.nodes[effectiveParentId].children_ids.some(
          (cid) => !state.nodes[cid]?.is_merge_node
        );

      const newNode: ConversationNode = {
        node_id: nodeId,
        conversation_id: activeConversationId,
        root_id: activeConversationId,
        parent_id: effectiveParentId,
        merge_parent_id: null,
        parent_ids: effectiveParentId ? [effectiveParentId] : [],
        children_ids: [],
        prompt,
        response,
        model_used: model,
        execution_context: 'local',
        is_sensitive: false,
        branch_label: parentHasNonMergeChildren ? 'Branch' : null,
        is_merge_node: false,
        pruned: false,
        timestamp,
      };

      const updatedNodes = { ...state.nodes, [nodeId]: newNode };

      if (effectiveParentId && updatedNodes[effectiveParentId]) {
        updatedNodes[effectiveParentId] = {
          ...updatedNodes[effectiveParentId],
          children_ids: [...updatedNodes[effectiveParentId].children_ids, nodeId],
        };
      }

      const updatedConversations = state.conversations.map((conv) => {
        if (conv.id === activeConversationId && !conv.root_node_id) {
          return { ...conv, root_node_id: nodeId };
        }
        return conv;
      });

      return {
        nodes: updatedNodes,
        conversations: updatedConversations,
        headNodeId: nodeId,
        lastMessageAt: Date.now(),
      };
    });
  },

  checkoutNode: (nodeId: string) => {
    set({ headNodeId: nodeId });
  },

  // Branching moves HEAD to the target node so the next commit becomes its child.
  // We also store the intended branch target so loadNodes doesn't overwrite it.
  branchFromNode: (nodeId: string, _label: string): string => {
    set({ headNodeId: nodeId });
    return nodeId;
  },

  pruneNode: (nodeId: string) => {
    const allIds = collectDescendants(nodeId, get().nodes);

    set((state) => {
      const updatedNodes = { ...state.nodes };

      for (const id of allIds) {
        if (updatedNodes[id]) {
          updatedNodes[id] = { ...updatedNodes[id], pruned: true };
        }
      }

      const target = state.nodes[nodeId];
      if (target?.parent_id && updatedNodes[target.parent_id]) {
        updatedNodes[target.parent_id] = {
          ...updatedNodes[target.parent_id],
          children_ids: updatedNodes[target.parent_id].children_ids.filter(
            (id) => id !== nodeId,
          ),
        };
      }

      const currentHead = state.headNodeId;
      const newHeadNodeId = currentHead && allIds.includes(currentHead)
        ? (state.nodes[nodeId]?.parent_id ?? null)
        : currentHead;

      return { nodes: updatedNodes, headNodeId: newHeadNodeId };
    });

    // Persist to backend so pruned state survives navigation
    import('../api/client').then(({ bulkDeleteNodes }) => {
      bulkDeleteNodes(allIds, false).catch(() => {});
    });
  },

  mergeNodes: (
    nodeIdA: string,
    nodeIdB: string,
    synthesisResponse: string,
    mergeNodeId?: string,
  ) => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;

    const id = mergeNodeId ?? crypto.randomUUID();
    const mergeNode: ConversationNode = {
      node_id: id,
      conversation_id: activeConversationId,
      root_id: activeConversationId,
      parent_id: nodeIdA,
      merge_parent_id: nodeIdB,
      parent_ids: [nodeIdA, nodeIdB],
      children_ids: [],
      prompt: `⎇ Merge Synthesis`,
      response: synthesisResponse,
      model_used: 'gemma4',
      execution_context: 'local',
      is_sensitive: false,
      branch_label: null,
      is_merge_node: true,
      pruned: false,
      timestamp: new Date().toISOString(),
    };

    set((state) => {
      const updatedNodes = { ...state.nodes, [id]: mergeNode };
      if (updatedNodes[nodeIdA]) {
        updatedNodes[nodeIdA] = {
          ...updatedNodes[nodeIdA],
          children_ids: [...updatedNodes[nodeIdA].children_ids, id],
        };
      }
      if (updatedNodes[nodeIdB]) {
        updatedNodes[nodeIdB] = {
          ...updatedNodes[nodeIdB],
          children_ids: [...updatedNodes[nodeIdB].children_ids, id],
        };
      }
      return { nodes: updatedNodes, headNodeId: id, selectedNodeIds: [] };
    });
  },

  selectNodeForMerge: (nodeId: string) => {
    set((state) => {
      const { selectedNodeIds } = state;
      if (selectedNodeIds.includes(nodeId)) {
        return { selectedNodeIds: selectedNodeIds.filter((id) => id !== nodeId) };
      }
      if (selectedNodeIds.length >= 5) return {}; // max 5
      return { selectedNodeIds: [...selectedNodeIds, nodeId] };
    });
  },

  clearMergeSelection: () => {
    set({ selectedNodeIds: [] });
  },

  setActiveConversation: (id: string | null) => {
    set({ activeConversationId: id, nodes: {}, headNodeId: null, selectedNodeIds: [] });
  },

  setAutoBranchingEnabled: (enabled: boolean) => {
    set({ autoBranchingEnabled: enabled });
  },

  setLastTps: (tps: number) => {
    set({ lastTps: tps });
  },

  deleteLocalConversation: (id: string) => {
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      ...(state.activeConversationId === id ? { activeConversationId: null, nodes: {}, headNodeId: null } : {}),
    }));
  },

  getThreadToHead: (): ConversationNode[] => {
    const { headNodeId, nodes } = get();
    if (!headNodeId) return [];

    const thread: ConversationNode[] = [];
    let currentId: string | null = headNodeId;

    while (currentId !== null) {
      const node: ConversationNode | undefined = nodes[currentId];
      if (!node || node.pruned) break;
      thread.push(node);
      currentId = node.parent_id;
    }

    return thread.reverse();
  },
}));
