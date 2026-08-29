/**
 * Central mapping from backend vocabularies to UI treatment.
 * Keeps status/decision colours consistent across every page.
 */

export type PillTone = "success" | "warning" | "danger" | "brand" | "neutral";

/** Engine result status → pill tone. */
export function engineTone(status: string): PillTone {
  switch (status?.toUpperCase()) {
    case "PASS":
      return "success";
    case "WARN":
      return "warning";
    case "FAIL":
    case "ERROR":
      return "danger";
    case "PROCESSING":
      return "brand";
    default: // NOT_IMPLEMENTED / NOT_EVALUATED
      return "neutral";
  }
}

/** Governance decision → pill tone. */
export function decisionTone(decision: string): PillTone {
  switch (decision?.toUpperCase()) {
    case "EXECUTE":
      return "success";
    case "CONSTRAIN":
      return "brand";
    case "DELAY":
    case "ESCALATE":
      return "warning";
    case "BLOCK":
    case "REJECTED":
      return "danger";
    default:
      return "neutral";
  }
}

/** Proposal / agent lifecycle status → pill tone. */
export function lifecycleTone(status: string): PillTone {
  switch (status?.toUpperCase()) {
    case "EXECUTED":
    case "APPROVED":
    case "ACTIVE":
    case "COMPLETED":
      return "success";
    case "PROPOSED":
    case "PENDING_APPROVAL":
    case "EVALUATED":
      return "brand";
    case "BLOCKED":
    case "REJECTED":
    case "FAILED":
    case "SUSPENDED":
    case "FROZEN":
      return "danger";
    default:
      return "neutral";
  }
}

export type TrustBand = { label: string; tone: PillTone };

/** Trust score (0–100) → band label + tone. */
export function trustBand(score: number): TrustBand {
  if (score >= 90) return { label: "High", tone: "success" };
  if (score >= 70) return { label: "Normal", tone: "brand" };
  if (score >= 50) return { label: "Restricted", tone: "warning" };
  return { label: "Low", tone: "danger" };
}

/** Risk score (0–100) → band label + tone. */
export function riskBand(score: number | null | undefined): TrustBand {
  if (score == null) return { label: "N/A", tone: "neutral" };
  if (score < 30) return { label: "Low", tone: "success" };
  if (score < 50) return { label: "Moderate", tone: "warning" };
  if (score < 70) return { label: "Elevated", tone: "warning" };
  return { label: "High", tone: "danger" };
}

export const toneToPillClass: Record<PillTone, string> = {
  success: "pill-success",
  warning: "pill-warning",
  danger: "pill-danger",
  brand: "pill-brand",
  neutral: "pill-neutral",
};

export const toneToHex: Record<PillTone, string> = {
  success: "#16a34a",
  warning: "#d97706",
  danger: "#dc2626",
  brand: "#2563eb",
  neutral: "#94a3b8",
};
