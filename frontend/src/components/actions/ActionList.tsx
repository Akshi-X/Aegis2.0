import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../../services/api";
import type { ActionProposal, AgentOverview } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card } from "../common/Card";
import { ActionRow } from "../common/ActionRow";
import { ListSkeleton } from "../common/Skeleton";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { cn } from "../../utils/cn";

const FILTERS: { key: string; label: string; match: (a: ActionProposal) => boolean }[] = [
  { key: "all", label: "All", match: () => true },
  { key: "proposed", label: "Proposed", match: (a) => a.status === "PROPOSED" },
  { key: "evaluated", label: "Evaluated", match: (a) => a.status === "EVALUATED" },
  { key: "executed", label: "Executed", match: (a) => a.status === "EXECUTED" },
  { key: "blocked", label: "Blocked", match: (a) => a.status === "BLOCKED" },
];

interface Bundle {
  actions: ActionProposal[];
  agents: AgentOverview[];
}

export function ActionList() {
  const { data, loading, error, reload } = useAsync<Bundle>(async () => {
    const [actions, agents] = await Promise.all([api.getActions(), api.getAgents()]);
    return { actions, agents };
  });
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const agentName = useMemo(() => {
    const m = new Map((data?.agents ?? []).map((a) => [a.id, a.name]));
    return (id: number) => m.get(id) ?? `Agent #${id}`;
  }, [data]);

  const filtered = useMemo(() => {
    const active = FILTERS.find((f) => f.key === filter) ?? FILTERS[0];
    const q = search.toLowerCase();
    return (data?.actions ?? [])
      .filter(active.match)
      .filter(
        (a) =>
          !q ||
          a.action_id.toLowerCase().includes(q) ||
          a.recipient.toLowerCase().includes(q) ||
          a.purpose.toLowerCase().includes(q)
      );
  }, [data, filter, search]);

  return (
    <PageContainer>
      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-surface p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
                filter === f.key ? "bg-brand-soft text-brand" : "text-ink-soft hover:text-ink"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search actions…"
            className="w-full rounded-lg border border-line bg-surface py-2 pl-9 pr-3 text-[13px] text-ink placeholder:text-ink-muted focus:border-brand focus:outline-none"
          />
        </div>
      </div>

      {/* List */}
      {loading ? (
        <ListSkeleton rows={6} />
      ) : error || !data ? (
        <Card padded={false}>
          <ErrorState message={error ?? undefined} onRetry={reload} />
        </Card>
      ) : filtered.length === 0 ? (
        <Card padded={false}>
          <EmptyState title="No actions found" description="Try a different filter or search term." />
        </Card>
      ) : (
        <Card padded={false}>
          <div className="divide-y divide-line">
            {filtered.map((a) => (
              <ActionRow key={a.action_id} action={a} agentName={agentName(a.agent_id)} />
            ))}
          </div>
        </Card>
      )}
    </PageContainer>
  );
}
