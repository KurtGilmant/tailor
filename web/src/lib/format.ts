const usd = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});
const integer = new Intl.NumberFormat("fr-FR");
const dateTime = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });
const day = new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric", month: "short" });

export const formatUsd = (value: number) => usd.format(value);
export const formatInt = (value: number) => integer.format(value);
export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));
export const formatDay = (isoDay: string) => day.format(new Date(`${isoDay}T00:00:00`));

export const TASK_LABELS: Record<string, string> = {
  extract: "Extraction",
  score: "Notation",
  write: "Rédaction",
  verify: "Vérification",
};

export const STATUS_LABELS: Record<string, string> = {
  ok: "OK",
  cached: "Cache",
  invalid: "Hors schéma",
  refused: "Refusé",
  error: "Erreur",
  blocked: "Bloqué",
};
