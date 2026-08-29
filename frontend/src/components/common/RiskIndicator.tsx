import { riskBand, toneToHex } from "../../utils/status";

/**
 * Compact circular risk ring. Pass a 0–100 score, or null when no engine has
 * produced a score yet (renders an honest "N/A", never a fabricated number).
 */
export function RiskIndicator({
  score,
  size = 132,
}: {
  score: number | null | undefined;
  size?: number;
}) {
  const band = riskBand(score);
  const color = toneToHex[band.tone];
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = score == null ? 0 : Math.min(100, Math.max(0, score));
  const offset = c - (pct / 100) * c;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-line)" strokeWidth={stroke} />
        {score != null && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset .6s ease" }}
          />
        )}
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-[20px] font-semibold uppercase tracking-wide" style={{ color }}>
          {band.label}
        </span>
        <span className="text-[11px] font-medium text-ink-muted">Risk Level</span>
      </div>
    </div>
  );
}
