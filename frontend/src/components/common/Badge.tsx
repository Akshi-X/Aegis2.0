import type { ReactNode } from "react";
import { cn } from "../../utils/cn";
import {
  engineTone,
  decisionTone,
  lifecycleTone,
  toneToPillClass,
  type PillTone,
} from "../../utils/status";

export function Pill({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: PillTone;
  className?: string;
}) {
  return (
    <span className={cn("pill", toneToPillClass[tone], className)}>{children}</span>
  );
}

/** Back-compat alias used by older components. */
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: PillTone;
  className?: string;
}) {
  return (
    <Pill tone={tone} className={className}>
      {children}
    </Pill>
  );
}

/**
 * Resolves any backend status string to the right tone. `kind` disambiguates
 * the vocabulary when the same word could mean different things.
 */
export function StatusBadge({
  status,
  kind = "auto",
  className,
}: {
  status: string;
  kind?: "engine" | "decision" | "lifecycle" | "auto";
  className?: string;
}) {
  const tone =
    kind === "engine"
      ? engineTone(status)
      : kind === "decision"
        ? decisionTone(status)
        : kind === "lifecycle"
          ? lifecycleTone(status)
          : resolveAuto(status);

  return (
    <Pill tone={tone} className={className}>
      {status.replace(/_/g, " ")}
    </Pill>
  );
}

function resolveAuto(status: string): PillTone {
  const s = status.toUpperCase();
  const decisions = ["EXECUTE", "CONSTRAIN", "DELAY", "BLOCK", "ESCALATE"];
  const engines = ["PASS", "WARN", "FAIL", "ERROR", "NOT_IMPLEMENTED", "PROCESSING"];
  if (decisions.includes(s)) return decisionTone(status);
  if (engines.includes(s)) return engineTone(status);
  return lifecycleTone(status);
}
