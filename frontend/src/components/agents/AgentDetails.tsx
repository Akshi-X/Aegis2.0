import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Dna, Fingerprint, Bot } from "lucide-react";
import { api } from "../../services/api";
import type { AgentOverview, FinancialDNAProfile, ActionProposal } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { StatusBadge } from "../common/Badge";
import { TrustIndicator } from "../common/TrustIndicator";
import { FinancialDNARange } from "../common/FinancialDNARange";
import { ActionRow } from "../common/ActionRow";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { Skeleton } from "../common/Skeleton";
import { formatCompactMoney, formatHour } from "../../utils/format";

interface Bundle {
  agent: AgentOverview;
  dna: FinancialDNAProfile | null;
  actions: ActionProposal[];
}

export function AgentDetails() {
  const { id } = useParams<{ id: string }>();
  const agentId = Number(id);

  const { data, loading, error, reload } = useAsync<Bundle>(async () => {
    const [agent, dna, actions] = await Promise.all([
      api.getAgent(agentId),
      api.getFinancialDNA(agentId).catch(() => null),
      api.getActions().then((res) => res.filter((a) => a.agent_id === agentId).slice(0, 6)),
    ]);
    return { agent, dna, actions };
  }, [agentId]);

  if (loading) {
    return (
      <PageContainer>
        <Skeleton className="h-8 w-56" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      </PageContainer>
    );
  }
  if (error || !data) {
    return (
      <PageContainer>
        <BackLink />
        <Card padded={false}>
          <ErrorState message={error ?? "Agent not found."} onRetry={reload} />
        </Card>
      </PageContainer>
    );
  }

  const { agent, dna, actions } = data;

  return (
    <PageContainer>
      <BackLink />

      {/* Identity header */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-soft text-brand">
              <Bot className="h-6 w-6" />
            </span>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-[20px] font-semibold text-ink">{agent.name}</h1>
                <StatusBadge status={agent.status} kind="lifecycle" />
              </div>
              <p className="mt-1 max-w-xl text-[13.5px] text-ink-soft">{agent.objective}</p>
            </div>
          </div>
          <div className="min-w-[160px]">
            <div className="eyebrow mb-1 text-right">Trust</div>
            <TrustIndicator score={agent.trust_score} />
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Authority */}
        <Card>
          <SectionHeader
            title={
              <span className="flex items-center gap-2">
                <Fingerprint className="h-[18px] w-[18px] text-brand" /> Authority
              </span>
            }
          />
          <div className="mt-4 grid grid-cols-2 gap-4">
            <Field label="Maximum Transaction" value={formatCompactMoney(agent.max_transaction_limit)} mono />
            <Field label="Daily Limit" value={formatCompactMoney(agent.daily_limit)} mono />
            <div>
              <div className="eyebrow mb-1.5">Allowed Actions</div>
              <div className="flex flex-wrap gap-1.5">
                {agent.allowed_actions.map((a) => (
                  <span key={a} className="pill pill-neutral">{a}</span>
                ))}
              </div>
            </div>
            <div>
              <div className="eyebrow mb-1.5">Currencies</div>
              <div className="flex flex-wrap gap-1.5">
                {agent.allowed_currencies.map((c) => (
                  <span key={c} className="pill pill-neutral">{c}</span>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Financial DNA */}
        <Card>
          <SectionHeader
            title={
              <span className="flex items-center gap-2">
                <Dna className="h-[18px] w-[18px] text-brand" /> Financial DNA
              </span>
            }
            action={
              <Link to="/financial-dna" className="text-[12.5px] font-medium text-brand hover:underline">
                Full profile
              </Link>
            }
          />
          {dna ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="eyebrow">Normal Amount Range</span>
                  <span className="font-mono text-[12px] text-ink-soft">
                    {formatCompactMoney(dna.normal_amount_range[0])} — {formatCompactMoney(dna.normal_amount_range[1])}
                  </span>
                </div>
                <FinancialDNARange
                  min={dna.normal_amount_range[0]}
                  max={dna.normal_amount_range[1]}
                  formatValue={(n) => formatCompactMoney(n)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4 border-t border-line pt-3">
                <Field label="Normal Hours" value={`${formatHour(dna.normal_hours[0])} — ${formatHour(dna.normal_hours[1])}`} mono />
                <Field label="Known Recipients" value={String(dna.known_recipients.length)} />
                <Field label="Avg Daily Actions" value={String(dna.typical_daily_transactions)} />
                <Field label="Daily Exposure" value={formatCompactMoney(dna.typical_daily_exposure)} mono />
              </div>
            </div>
          ) : (
            <EmptyState title="No behavioural profile yet" description="Financial DNA builds once the agent has transaction history." />
          )}
        </Card>
      </div>

      {/* Recent actions */}
      <Card padded={false}>
        <div className="p-5 pb-2">
          <SectionHeader title="Recent Actions" />
        </div>
        <div className="divide-y divide-line">
          {actions.length === 0 ? (
            <EmptyState title="No actions yet" description="This agent has not proposed any actions." />
          ) : (
            actions.map((a) => <ActionRow key={a.action_id} action={a} agentName={agent.name} />)
          )}
        </div>
      </Card>
    </PageContainer>
  );
}

function BackLink() {
  return (
    <Link to="/agents" className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-soft hover:text-ink">
      <ArrowLeft className="h-4 w-4" /> Agents
    </Link>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="eyebrow mb-1">{label}</div>
      <p className={`text-[14px] font-medium text-ink ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
