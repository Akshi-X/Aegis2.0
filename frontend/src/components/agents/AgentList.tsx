import { api } from "../../services/api";
import type { AgentOverview } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { AgentCard } from "../common/AgentRow";
import { Card } from "../common/Card";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { Skeleton } from "../common/Skeleton";

export function AgentList() {
  const { data: agents, loading, error, reload } = useAsync<AgentOverview[]>(api.getAgents);

  if (loading) {
    return (
      <PageContainer>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-5">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <Skeleton className="mt-3 h-4 w-32" />
              <Skeleton className="mt-4 h-1.5 w-full" />
              <Skeleton className="mt-4 h-8 w-full" />
            </div>
          ))}
        </div>
      </PageContainer>
    );
  }
  if (error || !agents) {
    return (
      <PageContainer>
        <Card padded={false}>
          <ErrorState message={error ?? undefined} onRetry={reload} />
        </Card>
      </PageContainer>
    );
  }
  if (agents.length === 0) {
    return (
      <PageContainer>
        <Card padded={false}>
          <EmptyState title="No agents registered" description="Autonomous agents will appear here once created." />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </PageContainer>
  );
}
