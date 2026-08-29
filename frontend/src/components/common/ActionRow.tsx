import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ShieldAlert } from "lucide-react";
import type { ActionProposal } from "../../types";
import { StatusBadge } from "./Badge";
import { formatMoney, formatTime } from "../../utils/format";

/**
 * One row in the actions list. Uses a subtle divider rather than a full card,
 * per the minimal spec. `statusOverride` lets callers show a governance
 * decision (EXECUTE/BLOCK) instead of the raw proposal status when known.
 */
export function ActionRow({
  action,
  agentName,
  statusOverride,
}: {
  action: ActionProposal;
  agentName?: string;
  statusOverride?: string;
}) {
  const status = statusOverride ?? action.status;
  return (
    <Link
      to={`/actions/${action.action_id}`}
      className="group flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-canvas"
    >
      <div className="hidden w-16 shrink-0 sm:block">
        <span className="pill pill-neutral">{action.action_type}</span>
      </div>

      <div className="w-28 shrink-0">
        <p className="font-mono text-[14px] font-semibold text-ink">
          {formatMoney(action.amount, action.currency)}
        </p>
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[13.5px] font-medium text-ink">
          {agentName ?? `Agent #${action.agent_id}`}
        </p>
        <p className="flex items-center gap-1 truncate text-[12.5px] text-ink-muted">
          <ArrowRight className="h-3 w-3 shrink-0" />
          {action.recipient}
          {action.recipient_known ? (
            <CheckCircle2 className="h-3 w-3 shrink-0 text-[var(--color-success)]" />
          ) : (
            <ShieldAlert className="h-3 w-3 shrink-0 text-[var(--color-warning)]" />
          )}
        </p>
      </div>

      <div className="hidden w-20 shrink-0 text-right font-mono text-[12px] text-ink-muted md:block">
        {formatTime(action.created_at)}
      </div>

      <div className="w-24 shrink-0 text-right">
        <StatusBadge status={status} />
      </div>
    </Link>
  );
}
