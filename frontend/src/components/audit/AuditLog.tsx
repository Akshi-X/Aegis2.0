import { useMemo, useState, type ReactNode } from "react";
import { api } from "../../services/api";
import type { ActionProposal, AgentOverview } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { AuditTimeline, type TimelineEvent } from "../common/AuditTimeline";
import { ListSkeleton } from "../common/Skeleton";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { lifecycleTone } from "../../utils/status";
import { formatMoney, formatDate } from "../../utils/format";
import { cn } from "../../utils/cn";

interface Bundle {
  actions: ActionProposal[];
  agents: AgentOverview[];
}

/**
 * There is no dedicated audit-log API yet, so this derives an honest
 * chronological record from real action proposals rather than inventing events.
 */
export function AuditLog() {
  const { data, loading, error, reload } = useAsync<Bundle>(async () => {
    const [actions, agents] = await Promise.all([api.getActions(), api.getAgents()]);
    return { actions, agents };
  });
  const [agentFilter, setAgentFilter] = useState<number | "all">("all");

  const events: TimelineEvent[] = useMemo(() => {
    if (!data) return [];
    const names = new Map(data.agents.map((a) => [a.id, a.name]));
    return data.actions
      .filter((a) => agentFilter === "all" || a.agent_id === agentFilter)
      .slice()
      .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
      .map((a) => ({
        time: formatDate(a.created_at),
        title: `${names.get(a.agent_id) ?? `Agent #${a.agent_id}`} proposed ${formatMoney(a.amount, a.currency)} → ${a.recipient}`,
        detail: `Status: ${a.status.replace(/_/g, " ")}`,
        tone: lifecycleTone(a.status),
      }));
  }, [data, agentFilter]);

  if (loading) {
    return (
      <PageContainer>
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

  return (
    <PageContainer>
      <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-surface p-1">
        <FilterChip active={agentFilter === "all"} onClick={() => setAgentFilter("all")}>
          All Agents
        </FilterChip>
        {data.agents.map((a) => (
          <FilterChip key={a.id} active={agentFilter === a.id} onClick={() => setAgentFilter(a.id)}>
            {a.name}
          </FilterChip>
        ))}
      </div>

      <Card>
        <SectionHeader title="Activity Timeline" subtitle="Derived from recorded action proposals." />
        <div className="mt-5">
          {events.length === 0 ? (
            <EmptyState title="No recorded events" description="Proposals will appear here as agents act." />
          ) : (
            <AuditTimeline events={events} />
          )}
        </div>
      </Card>
    </PageContainer>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
        active ? "bg-brand-soft text-brand" : "text-ink-soft hover:text-ink"
      )}
    >
      {children}
    </button>
  );
}
