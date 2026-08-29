import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, X, ShieldCheck } from "lucide-react";
import { api } from "../../services/api";
import type { ActionEvaluation, ActionProposal, AgentOverview } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card } from "../common/Card";
import { Pill } from "../common/Badge";
import { ListSkeleton } from "../common/Skeleton";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { formatMoney } from "../../utils/format";
import { decisionTone } from "../../utils/status";

interface ReviewItem {
  proposal: ActionProposal;
  evaluation: ActionEvaluation;
  agentName: string;
}

/** Decisions that route to a human rather than auto-resolving. */
const NEEDS_HUMAN = new Set(["ESCALATE", "DELAY", "CONSTRAIN"]);

export function Reviews() {
  const { data, loading, error, reload } = useAsync<ReviewItem[]>(async () => {
    const [actions, agents] = await Promise.all([api.getActions(), api.getAgents()]);
    const names = new Map<number, string>(agents.map((a: AgentOverview) => [a.id, a.name]));

    // Only evaluated proposals can be in the queue; fetch their latest verdict.
    const evaluated = actions.filter((a) => a.status !== "PROPOSED");
    const results = await Promise.all(
      evaluated.map(async (proposal) => {
        const evals = await api.getActionEvaluations(proposal.action_id).catch(() => []);
        const evaluation = evals[0];
        if (!evaluation || !NEEDS_HUMAN.has(evaluation.decision)) return null;
        return { proposal, evaluation, agentName: names.get(proposal.agent_id) ?? `Agent #${proposal.agent_id}` };
      })
    );
    return results.filter((r): r is ReviewItem => r !== null);
  });

  const [resolved, setResolved] = useState<Record<string, "approved" | "rejected">>({});

  if (loading) {
    return (
      <PageContainer>
        <ListSkeleton rows={3} />
      </PageContainer>
    );
  }
  if (error || !data) {
    return (
      <PageContainer>
        <Card padded={false}>
          <ErrorState message={error ?? undefined} onRetry={reload} />
        </Card>
      </PageContainer>
    );
  }

  const queue = data.filter((item) => !resolved[item.proposal.action_id]);

  if (queue.length === 0) {
    return (
      <PageContainer>
        <Card padded={false}>
          <EmptyState
            icon={<ShieldCheck className="h-5 w-5" />}
            title="No actions require human review"
            description="All current autonomous financial operations are within policy."
          />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <p className="text-[13px] text-ink-muted">
        {queue.length} action{queue.length > 1 ? "s" : ""} escalated by AEGIS-X governance. Decisions are recorded for review — no funds move.
      </p>
      <div className="space-y-4">
        {queue.map(({ proposal, evaluation, agentName }) => {
          const top = evaluation.top_factors?.[0];
          return (
            <Card key={proposal.action_id}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[20px] font-semibold text-ink">
                      {formatMoney(proposal.amount, proposal.currency)}
                    </span>
                    <Pill tone={decisionTone(evaluation.decision)}>{evaluation.decision}</Pill>
                  </div>
                  <p className="mt-1 flex items-center gap-1.5 text-[13px] text-ink-soft">
                    <span className="font-medium text-ink">{agentName}</span>
                    <ArrowRight className="h-3.5 w-3.5 text-ink-muted" />
                    {proposal.recipient}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => setResolved((r) => ({ ...r, [proposal.action_id]: "rejected" }))}
                  >
                    <X className="h-4 w-4" /> Reject
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => setResolved((r) => ({ ...r, [proposal.action_id]: "approved" }))}
                  >
                    <Check className="h-4 w-4" /> Approve
                  </button>
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-line bg-canvas p-3">
                <div className="eyebrow mb-1">Reason</div>
                <p className="text-[13px] text-ink">
                  {evaluation.decision_reason || "Escalated for manual review."}
                </p>
                {top && (
                  <p className="mt-1 text-[12.5px] text-ink-muted">
                    Top factor: <span className="font-medium text-ink-soft">{top.engine}</span>
                    {top.risk_score != null && ` (${top.risk_score.toFixed(0)})`}
                  </p>
                )}
              </div>

              <div className="mt-3 flex items-center justify-between">
                <Link to={`/actions/${proposal.action_id}`} className="text-[12.5px] font-medium text-brand hover:underline">
                  View full investigation →
                </Link>
                <span className="text-[11.5px] text-ink-muted">
                  Overall risk {evaluation.overall_risk_score != null ? evaluation.overall_risk_score.toFixed(0) : "—"}
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </PageContainer>
  );
}
