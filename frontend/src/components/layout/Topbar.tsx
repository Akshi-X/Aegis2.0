import { Search, Bell, ShieldCheck } from "lucide-react";
import { useLocation } from "react-router-dom";

export function Topbar() {
  const location = useLocation();
  
  let pageTitle = "Dashboard";
  if (location.pathname.startsWith("/agents")) pageTitle = "Agents";
  if (location.pathname.startsWith("/actions")) pageTitle = "Actions";
  if (location.pathname.startsWith("/financial-dna")) pageTitle = "Financial DNA";
  if (location.pathname.startsWith("/reviews")) pageTitle = "Human Reviews";
  
  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 shrink-0 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-slate-100">{pageTitle}</h1>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="relative relative w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search actions, agents..." 
            className="w-full bg-slate-950 border border-slate-800 rounded-md py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-700"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <span className="badge badge-slate flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" />
            Phase 5
          </span>
        </div>
        
        <button className="text-slate-400 hover:text-slate-200 relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-0 right-0 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-slate-900" />
        </button>
      </div>
    </header>
  );
}
