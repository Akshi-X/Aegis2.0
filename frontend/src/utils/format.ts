export function formatCurrency(amount: number, currency: string = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

/** Whole-rupee amount, no decimals: ₹50,000 */
export function formatMoney(amount: number, currency: string = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Compact Indian notation: ₹20K, ₹1.2L, ₹5Cr */
export function formatCompactMoney(amount: number, currency: string = "INR") {
  const symbol = currency === "INR" ? "₹" : "";
  const abs = Math.abs(amount);
  if (abs >= 1e7) return `${symbol}${trim(amount / 1e7)}Cr`;
  if (abs >= 1e5) return `${symbol}${trim(amount / 1e5)}L`;
  if (abs >= 1e3) return `${symbol}${trim(amount / 1e3)}K`;
  return `${symbol}${Math.round(amount)}`;
}

function trim(n: number) {
  return Number(n.toFixed(1)).toString();
}

export function formatDate(isoString: string) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatTime(isoString: string) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

/** "2h ago", "3d ago" — compact relative time. */
export function formatRelative(isoString: string) {
  const then = new Date(isoString).getTime();
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  return `${d}d ago`;
}

/** Zero-padded hour label from an integer hour, e.g. 9 -> "09:00". */
export function formatHour(hour: number) {
  return `${String(hour).padStart(2, "0")}:00`;
}
