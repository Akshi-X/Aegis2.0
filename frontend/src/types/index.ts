export type ActionType = "TRANSFER";
export type ProposalStatus = "PROPOSED" | "EVALUATED";
export type EngineStatus = "PASS" | "WARN" | "FAIL" | "ERROR" | "NOT_IMPLEMENTED";

export interface SourceAccountRef {
  id: number;
  account_number: string;
  account_name: string;
}

export interface ActionProposal {
  action_id: string;
  agent_id: number;
  action_type: ActionType;
  amount: number;
  currency: string;
  recipient: string;
  recipient_account_number: string | null;
  purpose: string;
  source_account: SourceAccountRef | null;
  status: ProposalStatus;
  created_at: string;
  recipient_known: boolean;
}

export interface EngineResult {
  engine: string;
  status: EngineStatus;
  risk_score: number | null;
  flags: string[];
  details: Record<string, any>;
}

export interface ActionEvaluation {
  evaluation_id: string;
  action_id: string;
  decision: "EXECUTE" | "BLOCK" | "ESCALATE";
  provisional: boolean;
  engines_run: number;
  engine_results: Record<string, EngineResult>;
  coverage: {
    complete: boolean;
    implemented: string[];
    not_implemented: string[];
    errored: string[];
  };
  latency_ms: number;
  timestamp: string;
}

export interface EvaluationResponse {
  evaluation: ActionEvaluation;
  proposal: ActionProposal;
}

export interface FinancialDNAProfile {
  agent_id: number;
  normal_amount_range: [number, number];
  normal_hours: [number, number];
  known_recipients: string[];
  typical_daily_transactions: number;
  typical_daily_exposure: number;
  last_updated: string;
}

// Frontend specific abstractions
export interface AgentOverview {
  id: number;
  name: string;
  status: string;
  objective: string;
  trust_score: number;
  max_transaction_limit: number;
  daily_limit: number;
  allowed_actions: string[];
  allowed_currencies: string[];
}
