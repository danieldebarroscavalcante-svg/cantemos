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
  refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" })
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

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "include" });

  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, init, false);
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type Membership = { organization_id: string; organization_name: string; role: string };
export type Me = { id: string; name: string; email: string; memberships: Membership[] };

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
