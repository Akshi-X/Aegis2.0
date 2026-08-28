export function formatCurrency(amount: number, currency: string = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(isoString: string) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export function formatTime(isoString: string) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    timeStyle: "medium",
  }).format(date);
}
