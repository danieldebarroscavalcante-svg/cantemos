"use client";

import {
  api,
  ApiError,
  refreshSession,
  type AgeGroup,
  type Ticket,
} from "@/lib/api";

/** Acesso à recepção: token do voluntário (código da recepção) ou login da equipe. */

export type Summary = {
  capacity: number;
  registration_limit: number;
  registered: number;
  present: number;
  priority_present: number;
};

export type Attendee = {
  id: string;
  name: string;
  age_group: AgeGroup;
  type_name: string;
  priority: boolean;
  accessibility_need: string | null;
  status: Ticket["status"];
  checked_in_at: string | null;
  checked_in_by: string | null;
};

export type OrderBrief = {
  code: string;
  buyer_name: string;
  tickets: Attendee[];
};

export type CheckinResult = {
  result: "ok" | "already" | "cancelled" | "invalid" | "other_event";
  message: string;
  ticket: Attendee | null;
  order: OrderBrief | null;
  summary: Summary;
};

export type Operator = {
  name: string;
  event_slug: string;
  event_title: string;
  can_undo: boolean;
};

const key = (slug: string) => `eventmer:recepcao:${slug}`;

function storedToken(slug: string): string | null {
  try {
    return localStorage.getItem(key(slug));
  } catch {
    return null;
  }
}

export function saveVolunteerToken(slug: string, token: string | null) {
  try {
    if (token) localStorage.setItem(key(slug), token);
    else localStorage.removeItem(key(slug));
  } catch {
    /* navegação privada: o token fica só nesta aba */
  }
  memoryToken = token;
}

let memoryToken: string | null = null;

export function deviceId(): string {
  try {
    let id = localStorage.getItem("eventmer:device");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("eventmer:device", id);
    }
    return id;
  } catch {
    return "desconhecido";
  }
}

export async function checkinApi<T>(
  slug: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = memoryToken ?? storedToken(slug);
  const url = `/checkin/events/${slug}${path}`;
  if (!token) return api<T>(url, init); // equipe logada (com renovação automática)

  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`/api/v1${url}`, { ...init, headers });
  if (!response.ok) {
    let message = "Não foi possível completar a ação.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* sem JSON */
    }
    if (response.status === 401) saveVolunteerToken(slug, null);
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

/** Descobre quem está operando: voluntário salvo, equipe logada ou ninguém. */
export async function currentOperator(slug: string): Promise<Operator | null> {
  try {
    return await checkinApi<Operator>(slug, "/me");
  } catch {
    if (storedToken(slug)) return null;
    if (await refreshSession()) {
      try {
        return await checkinApi<Operator>(slug, "/me");
      } catch {
        return null;
      }
    }
    return null;
  }
}

export async function volunteerLogin(
  slug: string,
  code: string,
  name: string,
): Promise<Operator> {
  const response = await api<{
    token: string;
    event_slug: string;
    event_title: string;
    operator_name: string;
  }>(`/checkin/events/${slug}/login`, {
    method: "POST",
    body: JSON.stringify({ code, name }),
  });
  saveVolunteerToken(slug, response.token);
  return {
    name: response.operator_name,
    event_slug: response.event_slug,
    event_title: response.event_title,
    can_undo: false,
  };
}

/** Bipe + vibração para o voluntário não precisar olhar a tela o tempo todo. */
let audio: AudioContext | null = null;
export function feedback(kind: "ok" | "warn" | "error") {
  try {
    audio ??= new AudioContext();
    const notes = kind === "ok" ? [880] : kind === "warn" ? [520, 520] : [220];
    notes.forEach((freq, i) => {
      const osc = audio!.createOscillator();
      const gain = audio!.createGain();
      osc.frequency.value = freq;
      osc.type = "sine";
      gain.gain.value = 0.15;
      osc.connect(gain).connect(audio!.destination);
      const start = audio!.currentTime + i * 0.18;
      osc.start(start);
      osc.stop(start + (kind === "error" ? 0.45 : 0.13));
    });
  } catch {
    /* sem áudio */
  }
  navigator.vibrate?.(
    kind === "ok" ? 80 : kind === "warn" ? [80, 60, 80] : 400,
  );
}
