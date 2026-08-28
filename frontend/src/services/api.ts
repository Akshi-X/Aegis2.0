import type {
  ActionEvaluation,
  ActionProposal,
  AgentOverview,
  EvaluationResponse,
  FinancialDNAProfile,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody?.detail?.message || `API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Real endpoints
  async getActions(): Promise<ActionProposal[]> {
    return fetchApi<ActionProposal[]>("/actions");
  },

  async getAction(id: string): Promise<ActionProposal> {
    return fetchApi<ActionProposal>(`/actions/${id}`);
  },

  async evaluateAction(id: string): Promise<EvaluationResponse> {
    return fetchApi<EvaluationResponse>(`/actions/${id}/evaluate`, {
      method: "POST",
    });
  },

  async getActionEvaluations(id: string): Promise<ActionEvaluation[]> {
    return fetchApi<ActionEvaluation[]>(`/actions/${id}/evaluations`);
  },

  async getFinancialDNA(agentId: number): Promise<FinancialDNAProfile> {
    return fetchApi<FinancialDNAProfile>(`/agent/${agentId}/financial-dna`);
  },

  // Abstracted/Mocked endpoints for missing backend features
  async getAgents(): Promise<AgentOverview[]> {
    return fetchApi<AgentOverview[]>("/agent");
  },

  async getAgent(id: number): Promise<AgentOverview> {
    return fetchApi<AgentOverview>(`/agent/${id}`);
  },

  async getDashboardMetrics(): Promise<any> {
    return fetchApi<any>("/agent/metrics");
  },
};
