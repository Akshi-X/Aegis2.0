import { useState, type ReactNode } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  RefreshCw,
  Fingerprint,
  BrainCircuit,
  Dna,
  Activity,
  Network,
  Users2,
  Zap,
  CheckCircle2,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { api } from "../../services/api";
import type { ActionEvaluation, ActionProposal, EngineResult } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { StatusBadge, Pill } from "../common/Badge";
import { SecurityEngineCard } from "../common/SecurityEngineCard";
import { ErrorState } from "../common/EmptyState";
import { Skeleton } from "../common/Skeleton";
import { decisionTone, riskBand, toneToHex } from "../../utils/status";
import { formatMoney, formatDate } from "../../utils/format";

/** Ordered pipeline metadata — the engines AEGIS-X actually runs. */
const PIPELINE: { key: string; title: string; description: string; icon: ReactNode }[] = [
  { key: "authority", title: "Identity & Authority", description: "Validates agent capabilities, constraints, and daily limits.", icon: <Fingerprint className="h-[18px] w-[18px]" /> },
  { key: "intent", title: "Intent Alignment", description: "Analyses objective drift and prompt manipulation.", icon: <BrainCircuit className="h-[18px] w-[18px]" /> },
  { key: "financial_dna", title: "Financial DNA", description: "Compares against the agent's behavioural baseline.", icon: <Dna className="h-[18px] w-[18px]" /> },
  { key: "anomaly", title: "ML Anomaly Engine", description: "Isolation Forest multi-dimensional outlier detection.", icon: <Activity className="h-[18px] w-[18px]" /> },
  { key: "cascade", title: "Cascade Detection", description: "Detects structuring and coordinated sequences.", icon: <Network className="h-[18px] w-[18px]" /> },
  { key: "counterparty", title: "Counterparty Intelligence", description: "Graph analysis of the recipient's money-flow.", icon: <Users2 className="h-[18px] w-[18px]" /> },
  { key: "blast_radius", title: "Blast Radius", description: "Estimates the damage if this action is wrong or malicious.", icon: <Zap className="h-[18px] w-[18px]" /> },
];

export function ActionInvestigation() {
  const { id } = useParams<{ id: string }>();
  const [evaluating, setEvaluating] = useState(false);
  const [override, setOverride] = useState<{ proposal: ActionProposal; evaluation: ActionEvaluation | null } | null>(null);

  const { data, loading, error, reload } = useAsync(async () => {
    const [proposal, evals] = await Promise.all([
      api.getAction(id!),
      api.getActionEvaluations(id!).catch(() => [] as ActionEvaluation[]),
    ]);
    return { proposal, evaluation: evals[0] ?? null };
  }, [id]);

  const view = override ?? data;

  async function runEvaluation() {
    if (!id) return;
    setEvaluating(true);
    try {
      const res = await api.evaluateAction(id);
      setOverride({ proposal: res.proposal, evaluation: res.evaluation });
      reload(); // Refresh the main view as well
    } catch (e: any) {
      alert("Evaluation failed: " + e.message);
    } finally {
      setEvaluating(false);
    }
  }

  async function handleOverride(status: "APPROVED" | "REJECTED") {
    if (!id) return;
    try {
      await api.updateActionStatus(id, status);
      reload(); // Reload to get updated status
      setOverride(null); // Clear override state so it reflects db accurately
    } catch (e: any) {
      alert("Failed to update status: " + e.message);
    }
  }

  if (loading) {
    return (
      <PageContainer>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </PageContainer>
    );
  }
  if (error || !view) {
    return (
      <PageContainer>
        <BackLink />
        <Card padded={false}>
          <ErrorState message={error ?? "Action not found."} onRetry={reload} />
        </Card>
      </PageContainer>
    );
  }

  const { proposal, evaluation } = view;
  const engines: Record<string, EngineResult> = evaluation?.engine_results ?? {};

  return (
    <PageContainer>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <BackLink />
        <button className="btn btn-primary btn-md" onClick={runEvaluation} disabled={evaluating}>
          {evaluating ? (
            <><RefreshCw className="h-4 w-4 animate-spin" /> Evaluating…</>
          ) : evaluation ? (
            <><RefreshCw className="h-4 w-4" /> Re-evaluate</>
          ) : (
            <><Play className="h-4 w-4" /> Run Evaluation</>
          )}
        </button>
      </div>

      {/* Summary */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Pill tone="neutral">{proposal.action_type}</Pill>
            <span className="font-mono text-[22px] font-semibold text-ink">
              {formatMoney(proposal.amount, proposal.currency)}
            </span>
            <div className="flex items-center gap-2 text-[14px] text-ink-soft">
              <span className="font-medium text-ink">{proposal.source_account?.account_name ?? `Agent #${proposal.agent_id}`}</span>
              <ArrowRight className="h-4 w-4 text-ink-muted" />
              <span className="font-medium text-ink">{proposal.recipient}</span>
              {proposal.recipient_known ? (
                <CheckCircle2 className="h-4 w-4 text-[var(--color-success)]" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-[var(--color-warning)]" />
              )}
            </div>
          </div>
          <StatusBadge status={proposal.status} />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-line pt-4 md:grid-cols-4">
          <Meta label="Agent">
            <Link to={`/agents/${proposal.agent_id}`} className="font-medium text-brand hover:underline">
              {proposal.source_account?.account_name ?? `Agent #${proposal.agent_id}`}
            </Link>
          </Meta>
          <Meta label="Recipient Account">
            <span className="font-mono text-[13px] text-ink">{proposal.recipient_account_number ?? "—"}</span>
          </Meta>
          <Meta label="Proposed">
            <span className="text-[13px] text-ink">{formatDate(proposal.created_at)}</span>
          </Meta>
          <Meta label="Purpose">
            <span className="text-[13px] text-ink">{proposal.purpose || "—"}</span>
          </Meta>
        </div>
      </Card>

      {!evaluation ? (
        <Card>
          <div className="flex flex-col items-center py-10 text-center">
            <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
              <Play className="h-5 w-5" />
            </span>
            <p className="text-[14px] font-semibold text-ink">Not yet evaluated</p>
            <p className="mt-1 max-w-sm text-[13px] text-ink-muted">
              Run the AEGIS-X security pipeline to assess this action. No funds move — a decision is recorded, not executed.
            </p>
            <button className="btn btn-primary btn-md mt-4" onClick={runEvaluation} disabled={evaluating}>
              <Play className="h-4 w-4" /> Run Evaluation
            </button>
          </div>
        </Card>
      ) : (
        <>
          <DecisionBanner 
            evaluation={evaluation} 
            proposalStatus={proposal.status}
            onOverride={handleOverride}
          />

          <div>
            <SectionHeader title="Security Evaluation" subtitle={`${evaluation.engines_run} engines · ${evaluation.latency_ms.toFixed(0)}ms · coverage ${evaluation.coverage.implemented.length}/${evaluation.coverage.engines_total}`} />
            <div className="relative mt-4 space-y-3 border-l border-line pl-6">
              {PIPELINE.map((engine) => {
                const engineResult = engines[engine.key];
                return (
                  <div key={engine.key} className="relative">
                    <span className="absolute -left-[27px] top-4 h-2 w-2 rounded-full bg-line-strong ring-4 ring-canvas" />
                    <SecurityEngineCard
                      engineName={engine.title}
                      description={engine.description}
                      icon={engine.icon}
                      result={engineResult}
                    >
                      {engineResult?.details?.gemini_reasoning && (
                        <div className="mt-3 rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
                          <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
                            <BrainCircuit className="h-3.5 w-3.5" /> Gemini AI Reasoning
                          </div>
                          <p className="text-[13px] leading-relaxed text-ink-soft">
                            {engineResult.details.gemini_reasoning}
                          </p>
                        </div>
                      )}
                    </SecurityEngineCard>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </PageContainer>
  );
}

function DecisionBanner({ 
  evaluation, 
  proposalStatus,
  onOverride 
}: { 
  evaluation: ActionEvaluation;
  proposalStatus: string;
  onOverride: (status: "APPROVED" | "REJECTED") => void;
}) {
  const tone = decisionTone(evaluation.decision);
  const accent = toneToHex[tone];
  const band = riskBand(evaluation.overall_risk_score);
  
  const isEscalated = evaluation.decision === "ESCALATE" || evaluation.decision === "DELAY";
  const canOverride = isEscalated && proposalStatus !== "EXECUTED" && proposalStatus !== "FAILED";
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-xl"
            style={{ background: `${accent}14`, color: accent }}
          >
            <Zap className="h-6 w-6" />
          </div>
          <div>
            <div className="eyebrow">Governance Decision</div>
            <div className="flex items-center gap-2">
              <span className="text-[22px] font-semibold tracking-tight" style={{ color: accent }}>
                {evaluation.decision}
              </span>
              {evaluation.provisional && <Pill tone="warning">Provisional</Pill>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <Stat label="Overall Risk" value={evaluation.overall_risk_score != null ? evaluation.overall_risk_score.toFixed(1) : "—"} sub={band.label} />
          <Stat label="Trust" value={evaluation.trust_score_at_evaluation != null ? evaluation.trust_score_at_evaluation.toFixed(0) : "—"} />
          <Stat label="Coverage" value={`${evaluation.coverage.implemented.length}/${evaluation.coverage.engines_total}`} />
        </div>
      </div>
      {evaluation.decision_reason && (
        <p className="mt-3 border-t border-line pt-3 text-[13px] text-ink-soft">{evaluation.decision_reason}</p>
      )}
      
      {canOverride && (
        <div className="mt-4 flex items-center gap-3 border-t border-line pt-4">
          <button 
            onClick={() => onOverride("APPROVED")}
            className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-4 py-2 text-[13px] font-semibold text-emerald-500 transition-colors hover:bg-emerald-500/20"
          >
            <CheckCircle2 className="h-4 w-4" /> Approve Action
          </button>
          <button 
            onClick={() => onOverride("REJECTED")}
            className="flex items-center gap-2 rounded-lg bg-rose-500/10 px-4 py-2 text-[13px] font-semibold text-rose-500 transition-colors hover:bg-rose-500/20"
          >
            <XCircle className="h-4 w-4" /> Decline Action
          </button>
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="text-right">
      <div className="eyebrow">{label}</div>
      <div className="font-mono text-[18px] font-semibold text-ink">{value}</div>
      {sub && <div className="text-[11px] text-ink-muted">{sub}</div>}
    </div>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="eyebrow mb-1">{label}</div>
      {children}
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/actions" className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-soft hover:text-ink">
      <ArrowLeft className="h-4 w-4" /> Actions
    </Link>
  );
}
