import { Link } from "react-router-dom";
import { Bot } from "lucide-react";
import type { AgentOverview } from "../../types";
import { StatusBadge } from "./Badge";
import { TrustIndicator } from "./TrustIndicator";
import { formatCompactMoney } from "../../utils/format";

/** Agent card used on the Agents grid. */
export function AgentCard({ agent }: { agent: AgentOverview }) {
  return (
    <Link
      to={`/agents/${agent.id}`}
      className="card group p-5 transition-shadow hover:shadow-[0_1px_0_var(--color-line-strong),0_8px_24px_-12px_rgba(15,23,42,0.15)]"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-soft text-brand">
            <Bot className="h-[18px] w-[18px]" />
          </span>
          <div>
            <p className="text-[14px] font-semibold text-ink">{agent.name}</p>
            <p className="line-clamp-1 max-w-[180px] text-[12px] text-ink-muted">
              {agent.objective}
            </p>
          </div>
        </div>
        <StatusBadge status={agent.status} kind="lifecycle" />
      </div>

      <div className="mt-4">
        <div className="mb-1 eyebrow">Trust</div>
        <TrustIndicator score={agent.trust_score} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-3">
        <div>
          <div className="eyebrow">Txn Limit</div>
          <p className="mt-0.5 font-mono text-[13px] text-ink">
            {formatCompactMoney(agent.max_transaction_limit)}
          </p>
        </div>
        <div>
          <div className="eyebrow">Daily Limit</div>
          <p className="mt-0.5 font-mono text-[13px] text-ink">
            {formatCompactMoney(agent.daily_limit)}
          </p>
        </div>
      </div>
    </Link>
  );
}
