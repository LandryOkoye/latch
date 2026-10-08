const DAY_MS = 86_400_000;

const dateFormat = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const formatDate = (iso: string) => dateFormat.format(new Date(iso));
export const formatDateTime = (iso: string) => dateTimeFormat.format(new Date(iso));

/** Whole days from now until `iso`; negative means it has passed. */
export function daysUntil(iso: string, now = Date.now()): number {
  return Math.round((new Date(iso).getTime() - now) / DAY_MS);
}

export function dueLabel(iso: string): { text: string; overdue: boolean } {
  const days = daysUntil(iso);
  if (days < 0) return { text: `${-days} day${days === -1 ? "" : "s"} overdue`, overdue: true };
  if (days === 0) return { text: "Due today", overdue: false };
  return { text: `Due in ${days} day${days === 1 ? "" : "s"}`, overdue: false };
}

export const percent = (rate: number) => `${Math.round(rate * 100)}%`;
