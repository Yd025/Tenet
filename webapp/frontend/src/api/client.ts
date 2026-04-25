import type { ModelId, TelemetryStats } from '../types/index.js';

const API_BASE = '/api';

// Helper function to handle API errors
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(
      `API error: ${response.status} ${response.statusText}`
    );
  }
  return response.json();
}

// POST /api/chat
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

// POST /api/branch
export async function fetchBranch(params: {
  node_id: string;
  label: string;
}): Promise<{ branch_id: string }> {
  const response = await fetch(`${API_BASE}/branch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

// POST /api/merge
export async function fetchMerge(params: {
  node_id_a: string;
  node_id_b: string;
}): Promise<{ response: string; node_id: string }> {
  const response = await fetch(`${API_BASE}/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(response);
}

// DELETE /api/node/:node_id
export async function fetchPrune(node_id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/node/${node_id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(
      `API error: ${response.status} ${response.statusText}`
    );
  }
}

// GET /api/telemetry
export async function fetchTelemetry(): Promise<TelemetryStats> {
  const response = await fetch(`${API_BASE}/telemetry`);
  return handleResponse(response);
}

// GET /api/models
export async function fetchModels(): Promise<ModelId[]> {
  const response = await fetch(`${API_BASE}/models`);
  return handleResponse(response);
}
