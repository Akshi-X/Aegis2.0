import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

export function EmptyState({
  title,
  description,
  icon,
  action,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-canvas text-ink-muted">
        {icon ?? <Inbox className="h-5 w-5" />}
      </div>
      <p className="text-[14px] font-semibold text-ink">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-[13px] text-ink-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <EmptyState
      title="Something went wrong"
      description={message ?? "Unable to load data."}
      action={
        onRetry ? (
          <button className="btn btn-ghost btn-sm" onClick={onRetry}>
            Retry
          </button>
        ) : undefined
      }
    />
  );
}
