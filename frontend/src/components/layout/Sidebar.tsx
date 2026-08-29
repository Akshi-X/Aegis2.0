import { NavLink } from "react-router-dom";
import { AegisMark } from "../common/Logo";
import { cn } from "../../utils/cn";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/agents", label: "Agents" },
  { to: "/actions", label: "Actions" },
  { to: "/financial-dna", label: "Financial DNA" },
  { to: "/security", label: "Security" },
  { to: "/reviews", label: "Human Review" },
  { to: "/audit", label: "Audit Logs" },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <aside className="flex h-full w-full flex-col bg-surface border-r border-line">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2 px-5">
        <AegisMark className="h-7 w-7 text-brand" />
        <span className="text-[15px] font-semibold tracking-tight text-ink">
          AEGIS<span className="text-brand">-X</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "block rounded-lg px-3 py-2 text-[13.5px] font-medium transition-colors",
                isActive
                  ? "bg-brand-soft text-brand"
                  : "text-ink-soft hover:bg-canvas hover:text-ink"
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* System status */}
      <div className="mx-3 mb-3 rounded-lg border border-line bg-canvas px-3 py-2.5">
        <div className="eyebrow mb-1">System Status</div>
        <div className="flex items-center gap-2 text-[13px] font-medium text-ink">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success/50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          Operational
        </div>
        <p className="mt-0.5 text-[11.5px] text-ink-muted">All systems running normally</p>
      </div>

      {/* User */}
      <div className="flex items-center gap-3 border-t border-line px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-[12px] font-semibold text-white">
          A
        </div>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold text-ink">Admin</p>
          <p className="truncate text-[11.5px] text-ink-muted">Security Officer</p>
        </div>
      </div>
    </aside>
  );
}
