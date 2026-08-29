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
  Power,
} from "lucide-react";
import type { ReactNode } from "react";
import { PageContainer } from "../layout/PageContainer";
import { Card, SectionHeader } from "../common/Card";
import { Pill } from "../common/Badge";
import { api } from "../../services/api";
import { useAsync } from "../../hooks/useAsync";

type EngineMeta = {
  title: string;
  description: string;
  icon: ReactNode;
  status: "active" | "soon";
  engineKey?: string;
};

/** Mirrors the real backend: only blast_radius remains a placeholder. */
const SIGNAL: EngineMeta[] = [
  { title: "Identity & Authority", description: "Capability, constraint and daily-limit enforcement.", icon: <Fingerprint className="h-[18px] w-[18px]" />, status: "active", engineKey: "authority" },
  { title: "Intent Alignment", description: "Objective-drift detection against the agent's mandate.", icon: <BrainCircuit className="h-[18px] w-[18px]" />, status: "active", engineKey: "intent" },
  { title: "Financial DNA", description: "Behavioural baseline: amount, hours, recipients.", icon: <Dna className="h-[18px] w-[18px]" />, status: "active", engineKey: "financial_dna" },
  { title: "ML Anomaly (Isolation Forest)", description: "Unsupervised multi-dimensional outlier scoring.", icon: <Activity className="h-[18px] w-[18px]" />, status: "active", engineKey: "anomaly" },
  { title: "Cascade Detection", description: "Structuring, velocity spikes and coordinated moves.", icon: <Network className="h-[18px] w-[18px]" />, status: "active", engineKey: "cascade" },
  { title: "Counterparty Intelligence", description: "Graph analysis of the recipient's money-flow.", icon: <Users2 className="h-[18px] w-[18px]" />, status: "active", engineKey: "counterparty" },
  { title: "Blast Radius", description: "Estimates the damage if an action is wrong: exposure vs balance, authority and recoverability.", icon: <Zap className="h-[18px] w-[18px]" />, status: "active", engineKey: "blast_radius" },
];

const AGGREGATION: EngineMeta[] = [
  { title: "Risk Fusion", description: "Combines correlated engine signals into one score.", icon: <Layers className="h-[18px] w-[18px]" />, status: "active", engineKey: "risk_fusion" },
  { title: "Dynamic Trust", description: "Maps evidence to an earned autonomy tier.", icon: <Gauge className="h-[18px] w-[18px]" />, status: "active", engineKey: "trust" },
  { title: "Governance", description: "Turns fused risk + trust into the final decision.", icon: <Scale className="h-[18px] w-[18px]" />, status: "active", engineKey: "governance" },
];

export function SecurityOverview() {
  const { data: config, reload } = useAsync(() => api.getEngineConfig());
  const engineConfig = config || {};

  const handleToggle = async (key: string, currentStatus: boolean) => {
    try {
      await api.updateEngineConfig(key, !currentStatus);
      reload();
    } catch (e: any) {
      alert("Failed to toggle engine: " + e.message);
    }
  };

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
          {SIGNAL.map((e) => (
            <EngineTile 
              key={e.title} 
              {...e} 
              isToggledOn={e.engineKey ? engineConfig[e.engineKey] !== false : true}
              onToggle={e.engineKey ? () => handleToggle(e.engineKey!, engineConfig[e.engineKey!] !== false) : undefined}
            />
          ))}
        </div>
      </div>

      <div>
        <SectionHeader title="Aggregation & Governance" subtitle="Consume the signals and reach a verdict." />
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {AGGREGATION.map((e) => (
            <EngineTile 
              key={e.title} 
              {...e} 
              isToggledOn={e.engineKey ? engineConfig[e.engineKey] !== false : true}
              onToggle={e.engineKey ? () => handleToggle(e.engineKey!, engineConfig[e.engineKey!] !== false) : undefined}
            />
          ))}
        </div>
      </div>
    </PageContainer>
  );
}

function EngineTile({ 
  title, 
  description, 
  icon, 
  status, 
  isToggledOn = true, 
  onToggle 
}: EngineMeta & { isToggledOn?: boolean; onToggle?: () => void }) {
  const active = status === "active" && isToggledOn;
  
  return (
    <div className={`card p-4 transition-opacity ${!active && status === "active" ? "opacity-60" : ""}`}>
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
        <div className="flex items-center gap-3">
          <Pill tone={active ? "success" : "neutral"}>{active ? "Active" : (status === "soon" ? "Coming Soon" : "Disabled")}</Pill>
          {onToggle && status === "active" && (
            <button 
              onClick={onToggle}
              className={`flex h-6 w-10 items-center rounded-full p-1 transition-colors ${isToggledOn ? "bg-emerald-500" : "bg-zinc-300"}`}
            >
              <div className={`h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${isToggledOn ? "translate-x-4" : "translate-x-0"}`} />
            </button>
          )}
        </div>
      </div>
      <h3 className="mt-3 text-[13.5px] font-semibold text-ink">{title}</h3>
      <p className="mt-0.5 text-[12.5px] text-ink-muted">{description}</p>
    </div>
  );
}
