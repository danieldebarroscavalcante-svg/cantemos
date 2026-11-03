import "server-only";
import type { PublicEvent } from "@/lib/api";

const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Busca o evento público no servidor. null = não publicado; erro de rede sobe para error.tsx. */
export async function fetchPublicEvent(
  slug: string,
  waitlistToken?: string,
): Promise<PublicEvent | null> {
  const query = waitlistToken
    ? `?lista=${encodeURIComponent(waitlistToken)}`
    : "";
  const response = await fetch(
    `${backend}/api/v1/public/events/${encodeURIComponent(slug)}${query}`,
    { cache: "no-store" },
  );
  if (response.status === 404) return null;
  if (!response.ok)
    throw new Error(`Falha ao carregar o evento (HTTP ${response.status})`);
  return (await response.json()) as PublicEvent;
}
