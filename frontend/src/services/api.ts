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
    // TODO: The backend does not currently have a GET /agents endpoint.
    // This is a placeholder that returns a mock list based on our knowledge of the seed data.
    return [
      {
        id: 1,
        name: "Treasury Agent",
        status: "ACTIVE",
        objective: "Pay legitimate company vendor invoices.",
        trust_score: 85.0,
        max_transaction_limit: 100000.0,
        daily_limit: 500000.0,
        allowed_actions: ["TRANSFER"],
        allowed_currencies: ["INR"],
      },
    ];
  },

  async getAgent(id: number): Promise<AgentOverview> {
    // TODO: The backend does not currently have a GET /agents/{id} endpoint.
    // This is a placeholder.
    if (id === 1) {
      return (await this.getAgents())[0];
    }
    throw new Error("Agent not found");
  },

  async getDashboardMetrics(): Promise<any> {
    // TODO: No backend endpoint for aggregate dashboard metrics yet.
    // Returning placeholder data.
    return {
      active_agents: 1,
      actions_today: "N/A", // We'd need an endpoint or to fetch all actions and filter
      executed_actions: "N/A",
      blocked_actions: "N/A",
      average_trust: 85,
    };
  },
};
