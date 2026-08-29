import { trustBand, toneToHex } from "../../utils/status";
import { cn } from "../../utils/cn";

/** Horizontal trust bar with score + band label. */
export function TrustIndicator({
  score,
  showLabel = true,
  className,
}: {
  score: number;
  showLabel?: boolean;
  className?: string;
}) {
  const band = trustBand(score);
  const color = toneToHex[band.tone];

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center justify-between text-[12px]">
        <span className="font-mono font-medium text-ink">{score.toFixed(0)}</span>
        {showLabel && (
          <span className="font-medium" style={{ color }}>
            {band.label}
          </span>
        )}
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, Math.max(0, score))}%`, background: color }}
        />
      </div>
    </div>
  );
}
