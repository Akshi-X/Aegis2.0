import { cn } from "../../utils/cn";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "green" | "yellow" | "red" | "blue" | "slate";
  className?: string;
}

export function Badge({ children, variant = "slate", className }: BadgeProps) {
  return (
    <span className={cn("badge", `badge-${variant}`, className)}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const getVariant = (s: string) => {
    switch (s.toUpperCase()) {
      case "PASS":
      case "ACTIVE":
      case "NORMAL":
      case "EXECUTE":
      case "COMPLETED":
        return "green";
      case "WARN":
      case "DEVIATION":
      case "ESCALATE":
      case "PROPOSED":
        return "yellow";
      case "FAIL":
      case "ERROR":
      case "BLOCK":
      case "SUSPENDED":
        return "red";
      case "NOT_IMPLEMENTED":
      case "EVALUATED":
        return "slate";
      case "PROCESSING":
        return "blue";
      default:
        return "slate";
    }
  };

  return <Badge variant={getVariant(status)}>{status}</Badge>;
}
