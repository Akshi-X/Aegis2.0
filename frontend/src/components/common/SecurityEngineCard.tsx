import type { ReactNode } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock, MinusCircle } from "lucide-react";
import type { EngineResult } from "../../types";
import { Pill } from "./Badge";
import { engineTone, toneToHex } from "../../utils/status";
import { cn } from "../../utils/cn";

/**
 * One engine's verdict in the evaluation pipeline. Designed to carry future
 * engines cleanly: pass `result=undefined` (or a NOT_IMPLEMENTED result) and it
 * renders an honest "Not Evaluated" state with no fabricated score.
 */
export function SecurityEngineCard({
  engineName,
  description,
  result,
  icon,
  children,
}: {
  engineName: string;
  description: string;
  result?: EngineResult;
  icon?: ReactNode;
  children?: ReactNode;
}) {
  const status = result?.status ?? "NOT_EVALUATED";
  const processing = status === "PROCESSING";
  const notReady = !result || status === "NOT_IMPLEMENTED" || status === "NOT_EVALUATED";
  const tone = engineTone(status);
  const accent = toneToHex[tone];

  const statusLabel = notReady
    ? "Not Evaluated"
    : processing
      ? "Processing"
      : status;

  return (
    <div
      className={cn(
        "card p-4 transition-colors",
        notReady && "opacity-70"
      )}
      style={notReady ? undefined : { boxShadow: `inset 3px 0 0 ${accent}` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
            style={{ background: notReady ? "var(--color-canvas)" : `${accent}14`, color: notReady ? "var(--color-ink-muted)" : accent }}
          >
            {icon ?? <StatusGlyph status={status} />}
          </span>
          <div>
            <h3 className="text-[13.5px] font-semibold text-ink">{engineName}</h3>
            <p className="mt-0.5 text-[12px] text-ink-muted">{description}</p>
          </div>
        </div>
        <Pill tone={processing ? "brand" : tone}>{statusLabel}</Pill>
      </div>

      {!notReady && !processing && (
        <div className="mt-3 space-y-2 pl-11">
          {result?.risk_score != null && (
            <div className="flex items-center gap-2 text-[12.5px]">
              <span className="text-ink-muted">Risk</span>
              <span className="font-mono font-medium text-ink">
                {result.risk_score.toFixed(1)}
              </span>
            </div>
          )}
          {result && result.flags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.flags.map((f) => (
                <span
                  key={f}
                  className="rounded-md border border-line bg-canvas px-1.5 py-0.5 font-mono text-[10.5px] text-ink-soft"
                >
                  {f}
                </span>
              ))}
            </div>
          )}
          {children}
        </div>
      )}
    </div>
  );
}

function StatusGlyph({ status }: { status: string }) {
  const s = status.toUpperCase();
  const cls = "h-[18px] w-[18px]";
  if (s === "PASS") return <CheckCircle2 className={cls} />;
  if (s === "WARN") return <AlertTriangle className={cls} />;
  if (s === "FAIL" || s === "ERROR") return <XCircle className={cls} />;
  if (s === "PROCESSING") return <Clock className={cls} />;
  return <MinusCircle className={cls} />;
}
