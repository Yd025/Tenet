export type ModelId = 'deepseek' | 'qwen' | 'qwen2.5-7b' | 'gemma4' | 'system';

export interface ConversationNode {
  node_id: string;
  conversation_id: string;
  parent_id: string | null;
  merge_parent_id: string | null;
  parent_ids: string[];
  children_ids: string[];
  root_id: string;
  prompt: string;
  response: string;
  model_used: ModelId;
  execution_context: 'local';
  is_sensitive: boolean;
  branch_label: string | null;
  is_merge_node: boolean;
  pruned: boolean;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  root_node_id: string | null;
  created_at: string;
}

export interface TelemetryStats {
  temp_c?: number;
  vram_gb?: number;
  utilization?: number;
  active_nodes: number;
  tps?: number;
}
