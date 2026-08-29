import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "../../utils/cn";

export function MetricCard({
  label,
  value,
  icon,
  delta,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  delta?: { value: string; direction?: "up" | "down" };
  tone?: "neutral" | "brand" | "success" | "warning" | "danger";
}) {
  const iconTone = {
    neutral: "bg-canvas text-ink-soft",
    brand: "bg-brand-soft text-brand",
    success: "bg-[var(--color-success-soft)] text-[var(--color-success)]",
    warning: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
    danger: "bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
  }[tone];

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <span className="text-[12.5px] font-medium text-ink-soft">{label}</span>
        <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg", iconTone)}>
          {icon}
        </span>
      </div>
      <div className="mt-2 text-[28px] font-semibold leading-none tracking-tight text-ink">
        {value}
      </div>
      {delta && (
        <div
          className={cn(
            "mt-2 flex items-center gap-1 text-[12px] font-medium",
            delta.direction === "down" ? "text-[var(--color-danger)]" : "text-[var(--color-success)]"
          )}
        >
          {delta.direction === "down" ? (
            <ArrowDownRight className="h-3.5 w-3.5" />
          ) : (
            <ArrowUpRight className="h-3.5 w-3.5" />
          )}
          {delta.value}
        </div>
      )}
    </div>
  );
}
