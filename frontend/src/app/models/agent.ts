export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

export enum AgentStatus {
  IDLE = 'IDLE',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED'
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  tools: string[];
  prompt: string;
  hitl_enabled: boolean;
  status: AgentStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  tools: string[];
  prompt: string;
  hitl_enabled?: boolean;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  tools?: string[];
  prompt?: string;
  hitl_enabled?: boolean;
  status?: AgentStatus;
} 