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

// fetchChat — non-streaming fallback used by ChatView until streaming is wired
export async function fetchChat(params: {
  prompt: string;
  conversation_id: string;
  branch_id: string;
  model: ModelId;
  is_sensitive: boolean;
}): Promise<{ response: string; node_id: string; model_used: ModelId; tps: number }> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

// POST /api/merge/nodes (two-node merge — used by BranchHistoryView)
export async function fetchMerge(params: {
  node_id_a: string;
  node_id_b: string;
  root_id?: string;
  model?: string;
  conflict_resolutions?: MergeResolution[];
}): Promise<MergeResult> {
  const response = await fetch(`${API_BASE}/merge/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      node_ids: [params.node_id_a, params.node_id_b],
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
