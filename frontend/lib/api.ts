/**
 * Cliente da API. As chamadas vão para /api/v1 no mesmo domínio (proxy do Next.js),
 * então o cookie httpOnly de refresh funciona sem configuração de CORS.
 * O access token fica só em memória — nunca em localStorage.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function parseError(response: Response): Promise<ApiError> {
  let message = "Não foi possível completar a ação. Tente novamente.";
  try {
    const body = await response.json();
    if (typeof body.detail === "string") message = body.detail;
  } catch {
    /* resposta sem JSON */
  }
  return new ApiError(response.status, message);
}

export async function refreshSession(): Promise<boolean> {
  refreshing ??= fetch("/api/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
  })
    .then(async (response) => {
      if (!response.ok) {
        setAccessToken(null);
        return false;
      }
      setAccessToken((await response.json()).access_token);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, init, false);
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** Download autenticado (ex.: planilha CSV). */
export async function apiDownload(
  path: string,
  filename: string,
): Promise<void> {
  const doFetch = () =>
    fetch(`/api/v1${path}`, {
      credentials: "include",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
  let response = await doFetch();
  if (response.status === 401 && (await refreshSession()))
    response = await doFetch();
  if (!response.ok) throw await parseError(response);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export type Membership = {
  organization_id: string;
  organization_name: string;
  role: string;
};
export type Me = {
  id: string;
  name: string;
  email: string;
  memberships: Membership[];
};

export async function login(email: string, password: string): Promise<void> {
  const { access_token } = await api<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(access_token);
}

export async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
  setAccessToken(null);
}

export type EventSummary = {
  slug: string;
  title: string;
  status: "draft" | "published" | "open" | "closed" | "finished";
  starts_at: string | null;
  capacity: number;
  registration_limit: number;
  registered: number;
};

export type QuotaUsage = { quantity: number; issued: number };
export type ReservedQuota = {
  id?: string;
  name: string;
  quantity: number;
  issued?: number;
};

export type EventSettings = {
  slug: string;
  title: string;
  status: EventSummary["status"];
  venue_name: string | null;
  venue_address: string | null;
  description: string | null;
  starts_at: string;
  doors_open_at: string | null;
  capacity: number;
  overbooking_percent: number;
  max_tickets_per_order: number;
  priority_quota: number;
  reserved_quotas: ReservedQuota[];
  registration_limit: number;
  general: QuotaUsage;
  priority: QuotaUsage;
  registered: number;
};

export type EventSettingsInput = Pick<
  EventSettings,
  | "starts_at"
  | "doors_open_at"
  | "capacity"
  | "overbooking_percent"
  | "max_tickets_per_order"
  | "priority_quota"
  | "status"
> & {
  reserved_quotas: Array<Pick<ReservedQuota, "id" | "name" | "quantity">>;
  venue_name: string;
  venue_address: string;
  description: string;
};

export type PublicEvent = {
  slug: string;
  title: string;
  subtitle: string | null;
  description: string | null;
  venue_name: string | null;
  venue_address: string | null;
  status: EventSummary["status"];
  starts_at: string;
  doors_open_at: string | null;
  max_tickets_per_order: number;
  available: number;
  priority_available: number;
  waitlist_waiting: number;
  invite: { name: string; quantity: number; hold_until: string } | null;
};

export type AgeGroup = "adulto" | "crianca" | "idoso";

export type Ticket = {
  id: string;
  attendee_name: string;
  age_group: AgeGroup;
  type_name: string;
  priority: boolean;
  accessibility_need: string | null;
  status: "valid" | "used" | "cancelled" | "transferred";
  qr: string | null;
};

export type Order = {
  code: string;
  token: string;
  status: "pending" | "confirmed" | "cancelled" | "expired" | "refunded";
  buyer_name: string;
  buyer_email: string;
  created_at: string;
  email_sent: boolean;
  event: PublicEvent;
  tickets: Ticket[];
};
