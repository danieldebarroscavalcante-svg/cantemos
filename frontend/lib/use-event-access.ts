"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type EventAccess = {
  role: "owner" | "admin" | "manager" | "checkin";
  label: string;
  permissions: {
    edit_event: boolean;
    manage_team: boolean;
    send_messages: boolean;
    view_reports: boolean;
    checkin: boolean;
    undo_any_checkin: boolean;
  };
};

/** Nível de quem está no painel neste evento (igreja + equipe do evento). */
export function useEventAccess(
  slug: string,
  enabled = true,
): EventAccess | null {
  const [access, setAccess] = useState<EventAccess | null>(null);
  useEffect(() => {
    if (!enabled) return;
    api<EventAccess>(`/org/events/${slug}/access`)
      .then(setAccess)
      .catch(() => setAccess(null));
  }, [slug, enabled]);
  return access;
}
