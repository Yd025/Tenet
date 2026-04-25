export interface ConversationNode {
  node_id: string;
  conversation_id: string;
  parent_id: string | null;
  merge_parent_id: string | null;
  children_ids: string[];
  prompt: string;
  response: string;
  model_used: ModelId;
  execution_context: 'local';
  is_sensitive: boolean;
  branch_label: string | null;
  is_merge_node: boolean;
  pruned: boolean;
  timestamp: string; // ISO-8601
}

export interface Conversation {
  id: string;
  title: string;
  root_node_id: string | null;
  created_at: string;
}

export interface TelemetryStats {
  temp_c: number;
  petaflops_pct: number;
  tps: number;
}

export type ModelId = 'deepseek' | 'qwen' | 'gemma4' | 'system';
