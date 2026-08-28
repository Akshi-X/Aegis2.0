import { ShieldAlert, ShieldCheck, HelpCircle, Activity } from "lucide-react";
import type { EngineResult, EngineStatus } from "../../types";
import { StatusBadge } from "./Badge";
import { cn } from "../../utils/cn";
import type { ReactNode } from "react";

interface SecurityEngineCardProps {
  engineName: string;
  description: string;
  result?: EngineResult;
  icon?: ReactNode;
  children?: ReactNode;
}

export function SecurityEngineCard({
  engineName,
  description,
  result,
  icon,
  children
}: SecurityEngineCardProps) {
  const isImplemented = result && result.status !== "NOT_IMPLEMENTED";
  
  const getBorderColor = (status?: EngineStatus) => {
    if (!status || status === "NOT_IMPLEMENTED") return "border-slate-800";
    if (status === "PASS") return "border-emerald-500/50";
    if (status === "WARN") return "border-amber-500/50";
    if (status === "FAIL" || status === "ERROR") return "border-rose-500/50";
    return "border-slate-800";
  };
  
  const getHeaderColor = (status?: EngineStatus) => {
    if (!status || status === "NOT_IMPLEMENTED") return "text-slate-500";
    if (status === "PASS") return "text-emerald-400";
    if (status === "WARN") return "text-amber-400";
    if (status === "FAIL" || status === "ERROR") return "text-rose-400";
    return "text-slate-200";
  };

  const getStatusIcon = (status?: EngineStatus) => {
    if (!status || status === "NOT_IMPLEMENTED") return <HelpCircle className="w-5 h-5" />;
    if (status === "PASS") return <ShieldCheck className="w-5 h-5" />;
    if (status === "WARN" || status === "FAIL" || status === "ERROR") return <ShieldAlert className="w-5 h-5" />;
    return <Activity className="w-5 h-5" />;
  };

  return (
    <div className={cn(
      "bg-slate-900 border rounded-lg p-5 transition-colors",
      getBorderColor(result?.status),
      !isImplemented && "opacity-60"
    )}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn("p-2 rounded-md bg-slate-950", getHeaderColor(result?.status))}>
            {icon || getStatusIcon(result?.status)}
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-wide uppercase text-slate-200">
              {engineName.replace("_", " ")}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">{description}</p>
          </div>
        </div>
        
        <div>
          {result ? <StatusBadge status={result.status} /> : <StatusBadge status="NOT_EVALUATED" />}
        </div>
      </div>

      {isImplemented && result && (
        <div className="space-y-4">
          {result.risk_score !== null && (
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-400">Risk Score:</span>
              <span className="font-mono font-medium text-slate-200">{result.risk_score.toFixed(1)}</span>
            </div>
          )}
          
          {result.flags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {result.flags.map((flag) => (
                <span key={flag} className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {flag}
                </span>
              ))}
            </div>
          )}
          
          {children && (
            <div className="pt-3 border-t border-slate-800 mt-3">
              {children}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
