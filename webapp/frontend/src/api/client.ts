import type { ModelId, TelemetryStats } from '../types/index.js';

const API_BASE = '/api';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Telemetry
// ---------------------------------------------------------------------------

// GET /telemetry
export async function fetchTelemetry(): Promise<TelemetryStats> {
  const response = await fetch(`${API_BASE}/telemetry`);
  return handleResponse(response);
}

// ---------------------------------------------------------------------------
// Streaming chat (SSE)
// ---------------------------------------------------------------------------

export interface StreamChatParams {
  prompt: string;
  parent_id: string | null;
  root_id: string;
  model: ModelId;
  auto_branching?: boolean;
}

export interface StreamChunk {
  token: string;
  tps: number;
  node_id?: string;
}

export interface StreamResult {
  nodeId: string | null;
  parentId: string | null;
}

export interface MergeConflict {
  id: string;
  left_claim: string;
  right_claim: string;
  why_conflict?: string;
}

export interface MergeResolution {
  id: string;
  choice: 'left' | 'right' | 'custom';
  custom_resolution?: string;
}

export interface MergeResult {
  response: string;
  node_id: string | null;
  requires_resolution: boolean;
  conflicts: MergeConflict[];
}

export interface NodeSummaryResult {
  summaries: Array<{
    node_id: string;
    title: string;
    subtitle: string;
  }>;
}

// POST /chat/stream — streams tokens via SSE, returns the backend node_id when done.
export function streamChat(
  params: StreamChatParams,
  signal: AbortSignal,
  onChunk: (chunk: StreamChunk) => void,
): Promise<StreamResult> {
  return fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';
    let savedNodeId: string | null = null;
    let savedParentId: string | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const json = trimmed.slice(5).trim();
        if (!json || json === '[DONE]') continue;
        try {
          const parsed = JSON.parse(json);
          if (parsed.type === 'node_saved') {
            savedNodeId = parsed.node_id;
            savedParentId = parsed.parent_id ?? null;
          } else {
            onChunk(parsed as StreamChunk);
          }
        } catch {
          // ignore malformed SSE lines
        }
      }
    }

    return { nodeId: savedNodeId, parentId: savedParentId };
  });
}

// ---------------------------------------------------------------------------
// Node merge (intra-root)
// ---------------------------------------------------------------------------

// POST /merge/nodes
export async function fetchMergeNodes(params: {
  node_ids: string[];
  root_id: string;
  model: ModelId;
}): Promise<{ node_id: string; response: string }> {
  const response = await fetch(`${API_BASE}/merge/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

// ---------------------------------------------------------------------------
// Root merge (workspace synthesis)
// ---------------------------------------------------------------------------

// POST /merge/roots
export async function fetchMergeRoots(params: {
  root_ids: string[];
  new_root_name: string;
}): Promise<{ root_id: string; node_id: string; response: string }> {
  const response = await fetch(`${API_BASE}/merge/roots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

// ---------------------------------------------------------------------------
// Legacy / compatibility shims
// ---------------------------------------------------------------------------

// POST /api/merge/nodes (multi-node merge — used by BranchHistoryView)
export async function fetchMerge(params: {
  node_ids: string[];
  root_id?: string;
  model?: string;
  conflict_resolutions?: MergeResolution[];
}): Promise<MergeResult> {
  const response = await fetch(`${API_BASE}/merge/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      node_ids: params.node_ids,
      root_id: params.root_id ?? 'default',
      model: params.model ?? 'gemma4',
      conflict_resolutions: params.conflict_resolutions ?? null,
    }),
  });
  return handleResponse(response);
}

// ---------------------------------------------------------------------------
// Nodes
// ---------------------------------------------------------------------------

// GET /api/nodes?root_id=<id>
export async function fetchNodes(rootId: string): Promise<import('../types').ConversationNode[]> {
  const response = await fetch(`${API_BASE}/nodes?root_id=${encodeURIComponent(rootId)}`);
  if (!response.ok) return [];
  return response.json();
}

// GET /api/nodes/:node_id
export async function fetchNode(nodeId: string): Promise<import('../types').ConversationNode> {
  const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}`);
  return handleResponse(response);
}

// GET /api/roots
export async function fetchRoots(): Promise<{ roots: string[] }> {
  const response = await fetch(`${API_BASE}/roots`);
  return handleResponse(response);
}

// GET /api/conversations
export async function fetchConversations(): Promise<{ root_id: string; title: string; created_at: string }[]> {
  const response = await fetch(`${API_BASE}/conversations`);
  if (!response.ok) return [];
  return response.json();
}

// GET /api/conversations/:root_id
export async function fetchConversation(rootId: string): Promise<{ root_id: string; title: string; created_at: string }> {
  const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(rootId)}`);
  return handleResponse(response);
}

// PUT /api/conversations/:root_id
export async function updateConversation(rootId: string, title: string): Promise<{ root_id: string; title: string }> {
  const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(rootId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  return handleResponse(response);
}

// DELETE /api/conversations/:root_id
export async function deleteConversation(rootId: string): Promise<{ deleted_nodes: number; deleted_conversation: number }> {
  const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(rootId)}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

// PUT /api/nodes/:node_id
export async function updateNode(nodeId: string, fields: {
  prompt?: string;
  response?: string;
  branch_label?: string;
  pruned?: boolean;
  metadata?: Record<string, unknown>;
}): Promise<import('../types').ConversationNode> {
  const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fields),
  });
  return handleResponse(response);
}

// DELETE /api/nodes/:node_id  (soft by default, hard=true for permanent)
export async function deleteNode(nodeId: string, hard = false): Promise<{ pruned?: boolean; deleted?: boolean; node_id: string }> {
  const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}?hard=${hard}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

// DELETE /api/nodes  (bulk)
export async function bulkDeleteNodes(nodeIds: string[], hard = false): Promise<{ pruned?: number; deleted?: number }> {
  const response = await fetch(`${API_BASE}/nodes?hard=${hard}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_ids: nodeIds }),
  });
  return handleResponse(response);
}

// PATCH /api/nodes/:node_id/restore
export async function restoreNode(nodeId: string): Promise<import('../types').ConversationNode> {
  const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}/restore`, {
    method: 'PATCH',
  });
  return handleResponse(response);
}

// PATCH /api/nodes/:node_id/reparent
export async function reparentNode(nodeId: string, newParentId: string): Promise<import('../types').ConversationNode> {
  const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}/reparent?new_parent_id=${encodeURIComponent(newParentId)}`, {
    method: 'PATCH',
  });
  return handleResponse(response);
}

// POST /api/nodes/summaries
export async function fetchNodeSummaries(params: {
  root_id: string;
  node_ids?: string[];
  model?: ModelId;
}): Promise<NodeSummaryResult> {
  const response = await fetch(`${API_BASE}/nodes/summaries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      root_id: params.root_id,
      node_ids: params.node_ids ?? null,
      model: params.model ?? 'gemma4',
    }),
  });
  return handleResponse(response);
}
