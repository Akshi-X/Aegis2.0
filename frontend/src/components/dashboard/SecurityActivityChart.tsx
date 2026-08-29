import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { ActionProposal } from "../../types";

/**
 * Buckets real proposals into the last 7 calendar days. Only real fields are
 * used: `created_at` for the day, `status` to classify executed vs blocked.
 * No synthetic trend is invented — a quiet week shows as a quiet chart.
 */
function buildSeries(actions: ActionProposal[]) {
  const days: { key: string; label: string; proposed: number; executed: number; blocked: number }[] = [];
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    days.push({
      key: d.toDateString(),
      label: d.toLocaleDateString("en-US", { weekday: "short" }),
      proposed: 0,
      executed: 0,
      blocked: 0,
    });
  }
  const index = new Map(days.map((d) => [d.key, d]));
  for (const a of actions) {
    const bucket = index.get(new Date(a.created_at).toDateString());
    if (!bucket) continue;
    bucket.proposed += 1;
    if (a.status === "EXECUTED") bucket.executed += 1;
    if (a.status === "BLOCKED") bucket.blocked += 1;
  }
  return days;
}

const SERIES = [
  { key: "proposed", label: "Proposed", color: "#2563eb" },
  { key: "executed", label: "Executed", color: "#16a34a" },
  { key: "blocked", label: "Blocked", color: "#dc2626" },
];

export function SecurityActivityChart({ actions }: { actions: ActionProposal[] }) {
  const data = useMemo(() => buildSeries(actions), [actions]);

  return (
    <div>
      <div className="mb-4 flex items-center gap-4">
        {SERIES.map((s) => (
          <div key={s.key} className="flex items-center gap-1.5 text-[12px] text-ink-soft">
            <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
            {s.label}
          </div>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 12, fill: "var(--color-ink-muted)" }}
            axisLine={{ stroke: "var(--color-line)" }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12, fill: "var(--color-ink-muted)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--color-line)",
              fontSize: 12,
              boxShadow: "0 8px 24px -12px rgba(15,23,42,.2)",
            }}
          />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              dot={{ r: 2.5, strokeWidth: 0, fill: s.color }}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
