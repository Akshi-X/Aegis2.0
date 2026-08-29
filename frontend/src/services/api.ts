/** Low-level HTTP client. Domain modules (agents/actions/dashboard) build on this. */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function http<T>(path: string, options?: RequestInit): Promise<T> {
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

import type {
  ActionEvaluation,
  ActionProposal,
  AgentOverview,
  DashboardMetrics,
  EvaluationResponse,
  FinancialDNAProfile,
} from "../types";

/** Flat facade kept for back-compat with existing imports. */
export const api = {
  getActions: (params?: { status?: string; agent_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.agent_id != null) q.set("agent_id", String(params.agent_id));
    const qs = q.toString();
    return http<ActionProposal[]>(`/actions${qs ? `?${qs}` : ""}`);
  },
  getAction: (id: string) => http<ActionProposal>(`/actions/${id}`),
  evaluateAction: (id: string) =>
    http<EvaluationResponse>(`/actions/${id}/evaluate`, { method: "POST" }),
  getActionEvaluations: (id: string) =>
    http<ActionEvaluation[]>(`/actions/${id}/evaluations`),
  getFinancialDNA: (agentId: number) =>
    http<FinancialDNAProfile>(`/agent/${agentId}/financial-dna`),
  getAgents: () => http<AgentOverview[]>("/agent"),
  getAgent: (id: number) => http<AgentOverview>(`/agent/${id}`),
  getDashboardMetrics: () => http<DashboardMetrics>("/agent/metrics"),
  updateActionStatus: (id: string, status: string) =>
    http<ActionProposal>(`/actions/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  getEngineConfig: () => http<Record<string, boolean>>("/engines/config"),
  updateEngineConfig: (engine_key: string, active: boolean) =>
    http<Record<string, boolean>>(`/engines/config/${engine_key}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    }),
};
