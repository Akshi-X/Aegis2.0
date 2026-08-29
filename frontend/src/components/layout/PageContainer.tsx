import type { ReactNode } from "react";
import { cn } from "../../utils/cn";

/**
 * Vertical rhythm wrapper for page content. The AppLayout already provides the
 * max-width and outer padding, so this only owns spacing between sections.
 */
export function PageContainer({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("space-y-6", className)}>{children}</div>;
}
