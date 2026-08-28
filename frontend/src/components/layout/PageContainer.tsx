import type { ReactNode } from "react";
import { cn } from "../../utils/cn";

export function PageContainer({ children, className }: { children: ReactNode, className?: string }) {
  return (
    <main className={cn("flex-1 overflow-y-auto p-6 lg:p-8", className)}>
      <div className="max-w-7xl mx-auto space-y-6">
        {children}
      </div>
    </main>
  );
}
