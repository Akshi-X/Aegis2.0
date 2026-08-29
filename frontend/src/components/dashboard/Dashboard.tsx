import { Link } from "react-router-dom";
import {
  Users,
  Activity,
  ShieldOff,
  Gauge,
  ArrowRight,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";
import { api } from "../../services/api";
import type { ActionProposal, AgentOverview, DashboardMetrics } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { MetricCard } from "../common/MetricCard";
import { Card, SectionHeader } from "../common/Card";
import { MetricSkeletonRow, ListSkeleton } from "../common/Skeleton";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { TrustIndicator } from "../common/TrustIndicator";
import { RiskIndicator } from "../common/RiskIndicator";
import { StatusBadge } from "../common/Badge";
import { SecurityActivityChart } from "./SecurityActivityChart";
import { formatMoney, formatTime } from "../../utils/format";

interface Bundle {
  metrics: DashboardMetrics;
  actions: ActionProposal[];
  agents: AgentOverview[];
}

export function Dashboard() {
  const { data, loading, error, reload } = useAsync<Bundle>(async () => {
    const [metrics, actions, agents] = await Promise.all([
      api.getDashboardMetrics(),
      api.getActions(),
      api.getAgents(),
    ]);
    return { metrics, actions, agents };
  });

  if (loading) {
    return (
      <PageContainer>
        <MetricSkeletonRow />
        <ListSkeleton rows={6} />
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

  const { metrics, actions, agents } = data;
  const agentName = (id: number) => agents.find((a) => a.id === id)?.name ?? `Agent #${id}`;
  const recent = actions.slice(0, 6);
  const pendingReview = actions.filter((a) => a.status === "PENDING_APPROVAL").length;
  // System posture is a transparent function of a real metric (avg trust),
  // not a fabricated risk engine.
  const posture = Math.max(0, Math.round(100 - metrics.average_trust));

  return (
    <PageContainer>
      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Active Agents" value={metrics.active_agents} icon={<Users className="h-[18px] w-[18px]" />} tone="brand" />
        <MetricCard label="Actions Today" value={metrics.actions_today} icon={<Activity className="h-[18px] w-[18px]" />} />
        <MetricCard label="Blocked Actions" value={metrics.blocked_actions} icon={<ShieldOff className="h-[18px] w-[18px]" />} tone={metrics.blocked_actions > 0 ? "danger" : "neutral"} />
        <MetricCard label="Avg Agent Trust" value={metrics.average_trust.toFixed(0)} icon={<Gauge className="h-[18px] w-[18px]" />} tone="success" />
      </div>

      {/* Activity + Feed */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Security Activity"
            subtitle="Proposed, executed and blocked actions"
            action={<span className="pill pill-neutral">Last 7 Days</span>}
          />
          <div className="mt-4">
            <SecurityActivityChart actions={actions} />
          </div>
        </Card>

        <Card padded={false} className="flex flex-col">
          <div className="p-5 pb-3">
            <SectionHeader title="Live Action Feed" subtitle="Most recent proposals" />
          </div>
          <div className="flex-1 divide-y divide-line">
            {recent.length === 0 ? (
              <EmptyState title="No recent actions" description="Agent proposals will appear here." />
            ) : (
              recent.map((a) => (
                <Link key={a.action_id} to={`/actions/${a.action_id}`} className="block px-5 py-3 hover:bg-canvas">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11.5px] text-ink-muted">{formatTime(a.created_at)}</span>
                    <StatusBadge status={a.status} />
                  </div>
                  <p className="mt-1 text-[13px] font-medium text-ink">{agentName(a.agent_id)}</p>
                  <p className="flex items-center gap-1 text-[12.5px] text-ink-soft">
                    Proposed {a.action_type.toLowerCase()} of{" "}
                    <span className="font-medium text-ink">{formatMoney(a.amount, a.currency)}</span>
                  </p>
                  <p className="mt-0.5 flex items-center gap-1 text-[12px] text-ink-muted">
                    <ArrowRight className="h-3 w-3" />
                    {a.recipient}
                    {a.recipient_known ? (
                      <CheckCircle2 className="h-3 w-3 text-[var(--color-success)]" />
                    ) : (
                      <ShieldAlert className="h-3 w-3 text-[var(--color-warning)]" />
                    )}
                  </p>
                </Link>
              ))
            )}
          </div>
          <Link to="/actions" className="border-t border-line px-5 py-3 text-[13px] font-medium text-brand hover:bg-canvas">
            View all actions →
          </Link>
        </Card>
      </div>

      {/* Trust + Risk + Summary */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <SectionHeader title="Agent Trust" subtitle="Current trust posture" />
          <div className="mt-4 space-y-4">
            {agents.length === 0 ? (
              <EmptyState title="No agents" />
            ) : (
              agents.map((a) => (
                <div key={a.id}>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-[13px] font-medium text-ink">{a.name}</span>
                  </div>
                  <TrustIndicator score={a.trust_score} />
                </div>
              ))
            )}
          </div>
        </Card>

        <Card>
          <SectionHeader title="Current System Risk" subtitle="Derived from live trust" />
          <div className="mt-3 flex flex-col items-center">
            <RiskIndicator score={posture} />
          </div>
          <div className="mt-4 space-y-2.5 border-t border-line pt-4">
            <Factor label="Average Trust" value={metrics.average_trust.toFixed(0)} />
            <Factor label="Blocked Today" value={String(metrics.blocked_actions)} />
            <Factor label="Active Agents" value={String(metrics.active_agents)} />
            <Factor label="Pending Review" value={String(pendingReview)} />
          </div>
        </Card>

        <Card>
          <SectionHeader title="System Summary" />
          <div className="mt-4 divide-y divide-line">
            <SummaryRow label="Total Agents" value={agents.length} />
            <SummaryRow label="Actions Today" value={metrics.actions_today} />
            <SummaryRow label="Actions Executed" value={metrics.executed_actions} />
            <SummaryRow label="Actions Blocked" value={metrics.blocked_actions} />
            <SummaryRow label="Pending Review" value={pendingReview} />
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}

function Factor({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-[13px]">
      <span className="flex items-center gap-2 text-ink-soft">
        <span className="h-1.5 w-1.5 rounded-full bg-brand" />
        {label}
      </span>
      <span className="font-mono font-medium text-ink">{value}</span>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between py-2.5 text-[13px]">
      <span className="text-ink-soft">{label}</span>
      <span className="font-mono font-semibold text-ink">{value}</span>
    </div>
  );
}
