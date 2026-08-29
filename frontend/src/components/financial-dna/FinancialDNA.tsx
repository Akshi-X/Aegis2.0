import { useState, type ReactNode } from "react";
import { Dna, Clock, Activity, Users, Wallet } from "lucide-react";
import { api } from "../../services/api";
import type { AgentOverview, FinancialDNAProfile } from "../../types";
import { useAsync } from "../../hooks/useAsync";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { FinancialDNARange } from "../common/FinancialDNARange";
import { ErrorState, EmptyState } from "../common/EmptyState";
import { Skeleton } from "../common/Skeleton";
import { formatCompactMoney, formatHour, formatRelative } from "../../utils/format";
import { cn } from "../../utils/cn";

export function FinancialDNA() {
  const { data: agents, loading, error, reload } = useAsync<AgentOverview[]>(api.getAgents);
  const [selected, setSelected] = useState<number | null>(null);
  const activeId = selected ?? agents?.[0]?.id ?? null;

  const dna = useAsync<FinancialDNAProfile | null>(
    () => (activeId != null ? api.getFinancialDNA(activeId) : Promise.resolve(null)),
    [activeId]
  );

  if (loading) {
    return (
      <PageContainer>
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Skeleton className="h-56 w-full rounded-xl" />
          <Skeleton className="h-56 w-full rounded-xl" />
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

  const profile = dna.data;

  return (
    <PageContainer>
      {/* Agent selector */}
      <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-surface p-1">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => setSelected(a.id)}
            className={cn(
              "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
              activeId === a.id ? "bg-brand-soft text-brand" : "text-ink-soft hover:text-ink"
            )}
          >
            {a.name}
          </button>
        ))}
      </div>

      {dna.loading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Skeleton className="h-56 w-full rounded-xl" />
          <Skeleton className="h-56 w-full rounded-xl" />
        </div>
      ) : !profile ? (
        <Card padded={false}>
          <EmptyState
            icon={<Dna className="h-5 w-5" />}
            title="No behavioural profile yet"
            description="This agent has insufficient transaction history to form a Financial DNA baseline."
          />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Amount */}
            <Card>
              <SectionHeader
                title={<span className="flex items-center gap-2"><Wallet className="h-[18px] w-[18px] text-brand" /> Normal Transaction Range</span>}
              />
              <div className="mt-5">
                <div className="mb-1 text-[28px] font-semibold tracking-tight text-ink">
                  {formatCompactMoney((profile.normal_amount_range[0] + profile.normal_amount_range[1]) / 2)}
                </div>
                <p className="mb-5 text-[12.5px] text-ink-muted">Typical transaction size</p>
                <FinancialDNARange
                  min={profile.normal_amount_range[0]}
                  max={profile.normal_amount_range[1]}
                  formatValue={(n) => formatCompactMoney(n)}
                />
              </div>
            </Card>

            {/* Hours */}
            <Card>
              <SectionHeader
                title={<span className="flex items-center gap-2"><Clock className="h-[18px] w-[18px] text-brand" /> Normal Operating Hours</span>}
              />
              <div className="mt-5">
                <div className="mb-1 font-mono text-[28px] font-semibold tracking-tight text-ink">
                  {formatHour(profile.normal_hours[0])} — {formatHour(profile.normal_hours[1])}
                </div>
                <p className="mb-5 text-[12.5px] text-ink-muted">When this agent normally operates</p>
                <div className="flex gap-[3px]">
                  {Array.from({ length: 24 }).map((_, h) => {
                    const active = h >= profile.normal_hours[0] && h <= profile.normal_hours[1];
                    return (
                      <div
                        key={h}
                        title={`${formatHour(h)}`}
                        className={cn("h-8 flex-1 rounded-sm", active ? "bg-brand" : "bg-line")}
                      />
                    );
                  })}
                </div>
                <div className="mt-1.5 flex justify-between font-mono text-[10px] text-ink-muted">
                  <span>00:00</span>
                  <span>12:00</span>
                  <span>23:59</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard icon={<Activity className="h-[18px] w-[18px]" />} label="Transaction Frequency" value={`${profile.typical_daily_transactions} / day`} />
            <StatCard icon={<Wallet className="h-[18px] w-[18px]" />} label="Daily Exposure" value={formatCompactMoney(profile.typical_daily_exposure)} />
            <StatCard icon={<Users className="h-[18px] w-[18px]" />} label="Known Recipients" value={String(profile.known_recipients.length)} />
          </div>

          {/* Recipients */}
          <Card>
            <SectionHeader title="Known Recipients" subtitle="Counterparties this agent normally pays" />
            {profile.known_recipients.length === 0 ? (
              <p className="mt-4 text-[13px] text-ink-muted">No recipients on record.</p>
            ) : (
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {profile.known_recipients.map((r) => (
                  <div key={r} className="flex items-center gap-3 rounded-lg border border-line bg-canvas px-3 py-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-[12px] font-semibold text-brand">
                      {r.charAt(0).toUpperCase()}
                    </span>
                    <span className="truncate text-[13px] font-medium text-ink">{r}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <p className="text-right text-[12px] text-ink-muted">
            Profile updated {formatRelative(profile.last_updated)}
          </p>
        </>
      )}
    </PageContainer>
  );
}

function StatCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-ink-muted">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-soft text-brand">{icon}</span>
        <span className="text-[12.5px] font-medium text-ink-soft">{label}</span>
      </div>
      <p className="mt-2 font-mono text-[22px] font-semibold text-ink">{value}</p>
    </div>
  );
}
