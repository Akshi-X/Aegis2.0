import {
  Fingerprint,
  BrainCircuit,
  MessageSquareWarning,
  Dna,
  Activity,
  TrendingUp,
  Network,
  Users2,
  Zap,
  Layers,
  Gauge,
  Scale,
} from "lucide-react";
import type { ReactNode } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { Pill } from "../common/Badge";

type EngineMeta = {
  title: string;
  description: string;
  icon: ReactNode;
  status: "active" | "soon";
};

/** Mirrors the real backend: only blast_radius remains a placeholder. */
const SIGNAL: EngineMeta[] = [
  { title: "Identity & Authority", description: "Capability, constraint and daily-limit enforcement.", icon: <Fingerprint className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Intent Alignment", description: "Objective-drift detection against the agent's mandate.", icon: <BrainCircuit className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Prompt Manipulation", description: "Detects injected instructions in consumed context.", icon: <MessageSquareWarning className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Financial DNA", description: "Behavioural baseline: amount, hours, recipients.", icon: <Dna className="h-[18px] w-[18px]" />, status: "active" },
  { title: "ML Anomaly (Isolation Forest)", description: "Unsupervised multi-dimensional outlier scoring.", icon: <Activity className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Intent Drift", description: "Trend analysis of behaviour over recent history.", icon: <TrendingUp className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Cascade Detection", description: "Structuring, velocity spikes and coordinated moves.", icon: <Network className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Counterparty Intelligence", description: "Graph analysis of the recipient's money-flow.", icon: <Users2 className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Blast Radius", description: "Estimates the damage if an action is wrong: exposure vs balance, authority and recoverability.", icon: <Zap className="h-[18px] w-[18px]" />, status: "active" },
];

const AGGREGATION: EngineMeta[] = [
  { title: "Risk Fusion", description: "Combines correlated engine signals into one score.", icon: <Layers className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Dynamic Trust", description: "Maps evidence to an earned autonomy tier.", icon: <Gauge className="h-[18px] w-[18px]" />, status: "active" },
  { title: "Governance", description: "Turns fused risk + trust into the final decision.", icon: <Scale className="h-[18px] w-[18px]" />, status: "active" },
];

export function SecurityOverview() {
  return (
    <PageContainer>
      <Card>
        <SectionHeader title="The AEGIS-X Pipeline" subtitle="Every proposed action passes through these engines before a decision is reached." />
        <div className="mt-4 flex flex-wrap items-center gap-2 text-[12.5px] text-ink-soft">
          {["Proposal", "Signal Engines", "Risk Fusion", "Dynamic Trust", "Governance", "Decision"].map((s, i, arr) => (
            <span key={s} className="flex items-center gap-2">
              <span className="rounded-md border border-line bg-canvas px-2.5 py-1 font-medium text-ink">{s}</span>
              {i < arr.length - 1 && <span className="text-ink-muted">→</span>}
            </span>
          ))}
        </div>
      </Card>

      <div>
        <SectionHeader title="Signal Engines" subtitle="Independent risk findings, produced in parallel." />
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SIGNAL.map((e) => <EngineTile key={e.title} {...e} />)}
        </div>
      </div>

      <div>
        <SectionHeader title="Aggregation & Governance" subtitle="Consume the signals and reach a verdict." />
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {AGGREGATION.map((e) => <EngineTile key={e.title} {...e} />)}
        </div>
      </div>
    </PageContainer>
  );
}

function EngineTile({ title, description, icon, status }: EngineMeta) {
  const active = status === "active";
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <span
          className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{
            background: active ? "var(--color-brand-soft)" : "var(--color-canvas)",
            color: active ? "var(--color-brand)" : "var(--color-ink-muted)",
          }}
        >
          {icon}
        </span>
        <Pill tone={active ? "success" : "neutral"}>{active ? "Active" : "Coming Soon"}</Pill>
      </div>
      <h3 className="mt-3 text-[13.5px] font-semibold text-ink">{title}</h3>
      <p className="mt-0.5 text-[12.5px] text-ink-muted">{description}</p>
    </div>
  );
}
