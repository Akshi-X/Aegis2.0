import { useLocation } from "react-router-dom";
import { Calendar, Menu } from "lucide-react";

const META: { match: (p: string) => boolean; title: string; subtitle: string }[] = [
  { match: (p) => p === "/", title: "Overview", subtitle: "Real-time security overview of autonomous financial operations." },
  { match: (p) => p.startsWith("/agents"), title: "Agents", subtitle: "Manage and monitor autonomous financial agents." },
  { match: (p) => p.startsWith("/actions"), title: "Actions", subtitle: "Monitor all financial actions proposed by autonomous agents." },
  { match: (p) => p.startsWith("/financial-dna"), title: "Financial DNA", subtitle: "Behavioural fingerprints of autonomous financial agents." },
  { match: (p) => p.startsWith("/security"), title: "Security", subtitle: "The AEGIS-X evaluation pipeline and its engines." },
  { match: (p) => p.startsWith("/reviews"), title: "Human Review", subtitle: "Actions requiring manual intervention." },
  { match: (p) => p.startsWith("/audit"), title: "Audit Logs", subtitle: "A chronological record of governance events." },
];

export function Topbar({ onMenu }: { onMenu?: () => void }) {
  const { pathname } = useLocation();
  const meta = META.find((m) => m.match(pathname)) ?? META[0];

  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-surface/80 px-4 backdrop-blur-md md:px-8">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenu}
          className="btn btn-ghost btn-sm !px-2 lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-[18px] w-[18px]" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-[17px] font-semibold leading-tight text-ink">
            {meta.title}
          </h1>
          <p className="truncate text-[12.5px] text-ink-muted">{meta.subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button className="btn btn-ghost btn-sm hidden sm:inline-flex">
          <Calendar className="h-4 w-4 text-ink-muted" />
          {today}
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-[12px] font-semibold text-white">
          A
        </div>
      </div>
    </header>
  );
}
