const WEEKDAYS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];
const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** Lê "2026-11-19T18:30:00" (horário local do evento) sem depender do fuso do aparelho. */
function parts(value: string) {
  const [date, time = "00:00"] = value.split("T");
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":");
  const weekday = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return { y, m, d, hh, mm, weekday };
}

export function formatEventDate(value: string): string {
  const p = parts(value);
  const text = `${WEEKDAYS[p.weekday]}, ${p.d} de ${MONTHS[p.m - 1]}`;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatTime(value: string): string {
  const p = parts(value);
  return `${p.hh}h${p.mm === "00" ? "" : p.mm}`;
}

export function formatEventDateTime(value: string): string {
  return `${formatEventDate(value)} às ${formatTime(value)}`;
}

export function mapsUrl(query: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
