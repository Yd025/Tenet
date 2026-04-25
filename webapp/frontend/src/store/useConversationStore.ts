import { create } from 'zustand';
import type { ConversationNode, Conversation, ModelId } from '../types';

interface ConversationStore {
  nodes: Record<string, ConversationNode>;
  conversations: Conversation[];
  activeConversationId: string | null;
  headNodeId: string | null;
  selectedNodeIds: string[];

  // actions
  startConversation: (title: string) => void;
  commitMessage: (
    prompt: string,
    response: string,
    model: ModelId,
    isSensitive: boolean,
  ) => void;
  checkoutNode: (nodeId: string) => void;
  branchFromNode: (nodeId: string, label: string) => string;
  pruneNode: (nodeId: string) => void;
  mergeNodes: (
    nodeIdA: string,
    nodeIdB: string,
    synthesisResponse: string,
  ) => void;
  selectNodeForMerge: (nodeId: string) => void;
  clearMergeSelection: () => void;
  setActiveConversation: (id: string) => void;
  getThreadToHead: () => ConversationNode[];
}

// ---------------------------------------------------------------------------
// Seed data — hardcoded UUIDs for stability
// ---------------------------------------------------------------------------
const SEED_CONV_ID = 'a1b2c3d4-0000-4000-8000-000000000001';
const SEED_V1_ID = 'a1b2c3d4-0000-4000-8000-000000000010';
const SEED_V2_ID = 'a1b2c3d4-0000-4000-8000-000000000020';
const SEED_V3_ID = 'a1b2c3d4-0000-4000-8000-000000000030';
const SEED_B1_ID = 'a1b2c3d4-0000-4000-8000-000000000040';

const seedNodes: Record<string, ConversationNode> = {
  [SEED_V1_ID]: {
    node_id: SEED_V1_ID,
    conversation_id: SEED_CONV_ID,
    parent_id: null,
    children_ids: [SEED_V2_ID],
    prompt:
      "I have a phone screening for a senior software engineer role at a mid-size fintech startup tomorrow. The job description emphasizes distributed systems, Python, and API design. Can you help me set the context so we can prep effectively?",
    response:
      "Absolutely — let's set you up for success. For a senior SWE phone screen at a fintech startup with that stack, interviewers typically probe three areas in the first 30–45 minutes:\n\n1. **Role fit** — your experience with distributed systems (queues, consensus, eventual consistency) and how you reason about trade-offs.\n2. **Python depth** — not just syntax; they'll test async patterns, GIL awareness, packaging, and testing discipline.\n3. **API design instincts** — REST vs. gRPC, versioning strategies, auth models, and how you'd document a contract.\n\nI'll track this context across our conversation. What would you like to drill first — technical depth, behavioral questions, or system design?",
    model_used: 'deepseek',
    execution_context: 'local',
    is_sensitive: false,
    branch_label: null,
    is_merge_node: false,
    pruned: false,
    timestamp: '2026-04-20T09:00:00.000Z',
  },
  [SEED_V2_ID]: {
    node_id: SEED_V2_ID,
    conversation_id: SEED_CONV_ID,
    parent_id: SEED_V1_ID,
    children_ids: [SEED_V3_ID, SEED_B1_ID],
    prompt:
      "Let's focus on the technical side first. What Python and distributed systems questions should I expect, and how should I frame my answers?",
    response:
      "Great call — technical questions usually come in two flavors here:\n\n**Python:**\n- *\"Walk me through the GIL and when it matters.\"* Frame around CPU-bound vs. I/O-bound work; mention `multiprocessing` vs. `asyncio`.\n- *\"How do you structure a large Python service?\"* Hit: layered architecture, dependency injection, type annotations, and `pytest` fixtures.\n- *\"What's your approach to async Python?\"* Discuss `async/await`, event loops, and avoiding blocking calls in coroutines.\n\n**Distributed Systems:**\n- *\"Explain eventual consistency and where you've applied it.\"* Use a concrete example (e.g., order ledger with async settlement).\n- *\"How would you design a rate limiter?\"* Token bucket vs. sliding window — mention Redis + Lua for atomic ops.\n- *\"What happens during a network partition in your system?\"* CAP theorem, circuit breakers, retry with exponential back-off.\n\n**Framing tip:** Lead with the trade-off, then your decision, then the outcome. Interviewers want to see how you think, not just what you know.",
    model_used: 'deepseek',
    execution_context: 'local',
    is_sensitive: false,
    branch_label: null,
    is_merge_node: false,
    pruned: false,
    timestamp: '2026-04-20T09:05:00.000Z',
  },
  [SEED_V3_ID]: {
    node_id: SEED_V3_ID,
    conversation_id: SEED_CONV_ID,
    parent_id: SEED_V2_ID,
    children_ids: [],
    prompt:
      "Now give me 3 system design questions they're likely to ask and concise talking points for each.",
    response:
      "Here are the top 3 for a fintech senior SWE screen:\n\n**1. Design a payment processing pipeline**\n- Idempotency keys on every write; exactly-once semantics via deduplication table.\n- Async queue (Kafka/SQS) between ingestion and settlement; dead-letter queue for failures.\n- Ledger as append-only event log; balances computed as materialized view.\n\n**2. Design a real-time fraud detection system**\n- Stream processing (Flink/Spark Structured Streaming) for low-latency feature computation.\n- Feature store (Redis) for sub-millisecond lookups during scoring.\n- Async feedback loop to retrain models without blocking transaction flow.\n\n**3. Design a rate-limited public API**\n- Token bucket per API key stored in Redis; Lua script for atomic check-and-decrement.\n- Tiered limits (free/pro/enterprise) backed by config service — no deploys for limit changes.\n- Return `Retry-After` headers; expose usage metrics via `/me/usage` endpoint.\n\n**For each:** state assumptions first, call out the biggest risk (consistency, latency, cost), and mention one thing you'd iterate on post-MVP.",
    model_used: 'deepseek',
    execution_context: 'local',
    is_sensitive: false,
    branch_label: null,
    is_merge_node: false,
    pruned: false,
    timestamp: '2026-04-20T09:12:00.000Z',
  },
  [SEED_B1_ID]: {
    node_id: SEED_B1_ID,
    conversation_id: SEED_CONV_ID,
    parent_id: SEED_V2_ID,
    children_ids: [],
    prompt:
      "Actually, let me take a different angle — what behavioral questions should I prep for instead?",
    response:
      "Smart to cover both tracks. For a senior role at a fintech startup, expect STAR-format behavioral questions like:\n\n**1. \"Tell me about a time you disagreed with a technical decision.\"**\n- Show you can advocate with data, accept decisions gracefully, and revisit when new evidence emerges.\n\n**2. \"Describe a production incident you owned.\"**\n- Hit: detection, communication cadence, root cause, blameless post-mortem, and the follow-up action item you shipped.\n\n**3. \"How do you mentor junior engineers?\"**\n- Concrete example: code reviews as teaching moments, pairing sessions, setting up feedback loops without micromanaging.\n\n**4. \"Tell me about a time you had to ship under pressure.\"**\n- Emphasize how you scoped ruthlessly, communicated trade-offs to stakeholders, and documented the tech debt you deferred.\n\n**Fintech-specific angle:** Weave in compliance awareness — e.g., how you balanced velocity with audit trail requirements or PCI-DSS constraints. It signals maturity for the domain.",
    model_used: 'deepseek',
    execution_context: 'local',
    is_sensitive: false,
    branch_label: 'Behavioral Focus',
    is_merge_node: false,
    pruned: false,
    timestamp: '2026-04-20T09:08:00.000Z',
  },
};

const seedConversations: Conversation[] = [
  {
    id: SEED_CONV_ID,
    title: 'Phone Screening Prep',
    root_node_id: SEED_V1_ID,
    created_at: '2026-04-20T09:00:00.000Z',
  },
];

// ---------------------------------------------------------------------------
// Helper: collect all descendant node ids (inclusive of root)
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------
export const useConversationStore = create<ConversationStore>((set, get) => ({
  nodes: { ...seedNodes },
  conversations: [...seedConversations],
  activeConversationId: SEED_CONV_ID,
  headNodeId: SEED_V3_ID,
  selectedNodeIds: [],

  startConversation: (title: string) => {
    const id = crypto.randomUUID();
    const newConv: Conversation = {
      id,
      title,
      root_node_id: '',
      created_at: new Date().toISOString(),
    };
    set((state) => ({
      conversations: [...state.conversations, newConv],
      activeConversationId: id,
      headNodeId: null,
    }));
  },

  commitMessage: (
    prompt: string,
    response: string,
    model: ModelId,
    isSensitive: boolean,
  ) => {
    const { activeConversationId, headNodeId } = get();
    if (!activeConversationId) return;

    const nodeId = crypto.randomUUID();
    const newNode: ConversationNode = {
      node_id: nodeId,
      conversation_id: activeConversationId,
      parent_id: headNodeId,
      children_ids: [],
      prompt,
      response,
      model_used: model,
      execution_context: 'local',
      is_sensitive: isSensitive,
      branch_label: null,
      is_merge_node: false,
      pruned: false,
      timestamp: new Date().toISOString(),
    };

    set((state) => {
      const updatedNodes = { ...state.nodes, [nodeId]: newNode };

      // If there was a previous head, register this new node as its child
      if (headNodeId && updatedNodes[headNodeId]) {
        updatedNodes[headNodeId] = {
          ...updatedNodes[headNodeId],
          children_ids: [...updatedNodes[headNodeId].children_ids, nodeId],
        };
      }

      // Update root_node_id on the conversation if this is the first node
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
      };
    });
  },

  checkoutNode: (nodeId: string) => {
    set({ headNodeId: nodeId });
  },

  branchFromNode: (nodeId: string, label: string): string => {
    const { activeConversationId } = get();
    if (!activeConversationId) return '';

    const newNodeId = crypto.randomUUID();
    const newNode: ConversationNode = {
      node_id: newNodeId,
      conversation_id: activeConversationId,
      parent_id: nodeId,
      children_ids: [],
      prompt: '',
      response: '',
      model_used: 'deepseek',
      execution_context: 'local',
      is_sensitive: false,
      branch_label: label,
      is_merge_node: false,
      pruned: false,
      timestamp: new Date().toISOString(),
    };

    set((state) => {
      const updatedNodes = { ...state.nodes, [newNodeId]: newNode };
      if (updatedNodes[nodeId]) {
        updatedNodes[nodeId] = {
          ...updatedNodes[nodeId],
          children_ids: [...updatedNodes[nodeId].children_ids, newNodeId],
        };
      }
      return { nodes: updatedNodes, headNodeId: newNodeId };
    });

    return newNodeId;
  },

  pruneNode: (nodeId: string) => {
    set((state) => {
      const allIds = collectDescendants(nodeId, state.nodes);
      const updatedNodes = { ...state.nodes };

      // Mark all descendants (and the node itself) as pruned
      for (const id of allIds) {
        if (updatedNodes[id]) {
          updatedNodes[id] = { ...updatedNodes[id], pruned: true };
        }
      }

      // Remove from parent's children_ids
      const target = state.nodes[nodeId];
      if (target?.parent_id && updatedNodes[target.parent_id]) {
        updatedNodes[target.parent_id] = {
          ...updatedNodes[target.parent_id],
          children_ids: updatedNodes[target.parent_id].children_ids.filter(
            (id) => id !== nodeId,
          ),
        };
      }

      return { nodes: updatedNodes };
    });
  },

  mergeNodes: (
    nodeIdA: string,
    nodeIdB: string,
    synthesisResponse: string,
  ) => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;

    const mergeNodeId = crypto.randomUUID();
    const mergeNode: ConversationNode = {
      node_id: mergeNodeId,
      conversation_id: activeConversationId,
      parent_id: nodeIdA,
      children_ids: [],
      prompt: `[Merge of ${nodeIdA} and ${nodeIdB}]`,
      response: synthesisResponse,
      model_used: 'deepseek',
      execution_context: 'local',
      is_sensitive: false,
      branch_label: null,
      is_merge_node: true,
      pruned: false,
      timestamp: new Date().toISOString(),
    };

    set((state) => {
      const updatedNodes = { ...state.nodes, [mergeNodeId]: mergeNode };
      if (updatedNodes[nodeIdA]) {
        updatedNodes[nodeIdA] = {
          ...updatedNodes[nodeIdA],
          children_ids: [...updatedNodes[nodeIdA].children_ids, mergeNodeId],
        };
      }
      return {
        nodes: updatedNodes,
        headNodeId: mergeNodeId,
        selectedNodeIds: [],
      };
    });
  },

  selectNodeForMerge: (nodeId: string) => {
    set((state) => {
      const { selectedNodeIds } = state;
      if (selectedNodeIds.includes(nodeId)) {
        // Toggle off
        return { selectedNodeIds: selectedNodeIds.filter((id) => id !== nodeId) };
      }
      if (selectedNodeIds.length >= 2) {
        // Already at max — ignore
        return {};
      }
      return { selectedNodeIds: [...selectedNodeIds, nodeId] };
    });
  },

  clearMergeSelection: () => {
    set({ selectedNodeIds: [] });
  },

  setActiveConversation: (id: string) => {
    set({ activeConversationId: id });
  },

  getThreadToHead: (): ConversationNode[] => {
    const { headNodeId, nodes } = get();
    if (!headNodeId) return [];

    const thread: ConversationNode[] = [];
    let currentId: string | null = headNodeId;

    while (currentId !== null) {
      const node: ConversationNode | undefined = nodes[currentId];
      if (!node) break;
      if (!node.pruned) {
        thread.push(node);
      }
      currentId = node.parent_id;
    }

    return thread.reverse();
  },
}));
