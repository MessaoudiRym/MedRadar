const DAY_MS = 24 * 3600 * 1000;

/** "today", "yesterday", "3 days ago", then a date. */
export function updatedAgo(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  const days = Math.floor((startOfDay(now) - startOfDay(date.getTime())) / DAY_MS);
  if (days <= 0) return `today at ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  return `on ${date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}`;
}

function startOfDay(ms: number) {
  const d = new Date(ms);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

export function formatDistance(km: number): string {
  return km < 1 ? `${Math.round(km * 1000 / 10) * 10} m` : `${km.toFixed(1)} km`;
}

/** "0550000001" -> "0550 00 00 01", "041234567" -> "041 23 45 67" */
export function formatPhone(phone: string): string {
  if (/^0[567]\d{8}$/.test(phone)) return phone.replace(/^(\d{4})(\d{2})(\d{2})(\d{2})$/, "$1 $2 $3 $4");
  if (/^0\d{8}$/.test(phone)) return phone.replace(/^(\d{3})(\d{2})(\d{2})(\d{2})$/, "$1 $2 $3 $4");
  return phone;
}
