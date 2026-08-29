import { toneToHex, type PillTone } from "../../utils/status";

export interface TimelineEvent {
  time: string;
  title: string;
  detail?: string;
  tone?: PillTone;
}

/** Vertical chronological timeline with a connecting rail. */
export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <ol className="relative ml-1.5 space-y-5 border-l border-line pl-6">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span
            className="absolute -left-[29px] top-1 flex h-3 w-3 items-center justify-center rounded-full ring-4 ring-surface"
            style={{ background: toneToHex[e.tone ?? "brand"] }}
          />
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-mono text-[12px] text-ink-muted">{e.time}</span>
            <span className="text-[13.5px] font-medium text-ink">{e.title}</span>
          </div>
          {e.detail && <p className="mt-0.5 text-[12.5px] text-ink-muted">{e.detail}</p>}
        </li>
      ))}
    </ol>
  );
}
