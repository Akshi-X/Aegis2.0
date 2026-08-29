export type ActionType = "TRANSFER" | "PAYMENT";
export type ProposalStatus =
  | "PROPOSED"
  | "EVALUATED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "EXECUTED"
  | "BLOCKED"
  | "FAILED";
export type EngineStatus =
  | "PASS"
  | "WARN"
  | "FAIL"
  | "ERROR"
  | "NOT_IMPLEMENTED"
  | "PROCESSING";
export type GovernanceDecision =
  | "EXECUTE"
  | "CONSTRAIN"
  | "DELAY"
  | "BLOCK"
  | "ESCALATE";

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

export interface CoverageReport {
  engines_total: number;
  engines_implemented: number;
  implemented: string[];
  not_implemented: string[];
  errored: string[];
  complete: boolean;
}

export interface RiskFactor {
  engine: string;
  risk_score: number | null;
  status: string;
  flags: string[];
}

export interface ActionEvaluation {
  evaluation_id: string;
  proposal_id: number;
  agent_id: number;
  decision: GovernanceDecision;
  decision_reason: string;
  provisional: boolean;
  overall_risk_score: number | null;
  trust_score_at_evaluation: number | null;
  engines_run: number;
  engine_results: Record<string, EngineResult>;
  coverage: CoverageReport;
  fusion_detail: Record<string, any>;
  top_factors: RiskFactor[];
  latency_ms: number;
  created_at: string;
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

export interface DashboardMetrics {
  active_agents: number;
  actions_today: number;
  executed_actions: number;
  blocked_actions: number;
  average_trust: number;
}
