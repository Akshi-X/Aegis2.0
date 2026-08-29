/**
 * A labelled range track with a marker — used to visualise an agent's "normal"
 * band (amount, hours) and where a current value sits within it.
 */
export function FinancialDNARange({
  min,
  max,
  marker,
  formatValue,
  lowLabel,
  highLabel,
  markerLabel,
}: {
  min: number;
  max: number;
  marker?: number;
  formatValue: (n: number) => string;
  lowLabel?: string;
  highLabel?: string;
  markerLabel?: string;
}) {
  const span = max - min || 1;
  const pct =
    marker != null ? Math.min(100, Math.max(0, ((marker - min) / span) * 100)) : null;

  return (
    <div>
      <div className="relative h-1.5 w-full rounded-full bg-line">
        {/* normal band */}
        <div className="absolute inset-0 rounded-full bg-brand-soft" />
        <div className="absolute inset-y-0 left-0 right-0 rounded-full border border-brand/20" />
        {pct != null && (
          <div
            className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-brand shadow-sm"
            style={{ left: `${pct}%` }}
          />
        )}
      </div>
      <div className="mt-2 flex items-center justify-between text-[12px] text-ink-muted">
        <span>{lowLabel ?? formatValue(min)}</span>
        {markerLabel && marker != null && (
          <span className="font-medium text-brand">{markerLabel}</span>
        )}
        <span>{highLabel ?? formatValue(max)}</span>
      </div>
    </div>
  );
}
