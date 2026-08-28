import { Activity, LayoutDashboard, Shield, Users, Dna, FileCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../../utils/cn";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/agents", icon: Users, label: "Agents" },
  { to: "/actions", icon: Activity, label: "Actions" },
  { to: "/financial-dna", icon: Dna, label: "Financial DNA" },
  { to: "/reviews", icon: FileCheck, label: "Reviews" },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-full shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <div className="flex items-center gap-2 text-emerald-400">
          <Shield className="w-6 h-6" />
          <span className="font-bold tracking-widest text-lg">AEGIS-X</span>
        </div>
      </div>
      
      <nav className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              )
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-800 text-xs text-slate-500 space-y-2">
        <div className="flex items-center justify-between">
          <span>System Status</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Online
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>API Status</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Connected
          </span>
        </div>
      </div>
    </aside>
  );
}
