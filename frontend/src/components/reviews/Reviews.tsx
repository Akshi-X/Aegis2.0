import { FileCheck } from "lucide-react";
import { PageContainer } from "../layout/PageContainer";

export function Reviews() {
  return (
    <PageContainer>
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="w-20 h-20 bg-slate-900 rounded-full flex items-center justify-center border border-slate-800 mb-6">
          <FileCheck className="w-10 h-10 text-emerald-500 opacity-80" />
        </div>
        
        <h1 className="text-2xl font-bold text-slate-100 mb-3">Human Review Queue</h1>
        <p className="text-slate-400 max-w-md mx-auto mb-8">
          The governance and dynamic human-in-the-loop review features will be implemented in a future phase.
        </p>
        
        <div className="px-4 py-2 bg-amber-500/10 text-amber-400 rounded-md border border-amber-500/20 text-sm font-medium">
          Coming Soon (Post Phase 5)
        </div>
      </div>
    </PageContainer>
  );
}
