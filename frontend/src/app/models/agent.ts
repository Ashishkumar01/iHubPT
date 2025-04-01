export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

export enum AgentStatus {
  IDLE = 'IDLE',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  ERROR = 'ERROR'
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  prompt: string;
  tools: string[];
  hitl_enabled: boolean;
  status: AgentStatus;
  created_at: string;
  updated_at: string;
  context?: {
    chat_history?: Array<{
      role: 'user' | 'assistant' | 'function';
      content: string;
      timestamp: string;
      name?: string;  // For function messages
    }>;
  };
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