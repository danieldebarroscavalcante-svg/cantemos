"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, logout, type EventSummary } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const roleLabel: Record<string, string> = {
  owner: "Responsável",
  admin: "Administrador",
  manager: "Produção",
  checkin: "Recepção",
};

const statusLabel: Record<EventSummary["status"], string> = {
  draft: "Rascunho",
  published: "Publicado",
  open: "Inscrições abertas",
  closed: "Inscrições encerradas",
  finished: "Finalizado",
};

function formatDate(value: string | null) {
  if (!value) return "Data a definir";
  const date = new Date(value);
  return date.toLocaleString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function PainelPage() {
  const router = useRouter();
  const me = useMe();
  const [events, setEvents] = useState<EventSummary[] | null>(null);

  useEffect(() => {
    if (me) api<EventSummary[]>("/org/events").then(setEvents).catch(() => setEvents([]));
  }, [me]);

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  if (!me) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted" aria-busy>
        Carregando…
      </main>
    );
  }

  const roles = me.memberships.map((m) => `${roleLabel[m.role] ?? m.role} · ${m.organization_name}`);

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">Painel</p>
          <h1 className="text-2xl font-bold">Olá, {me.name.split(" ")[0]}</h1>
          <p className="text-sm text-muted">{roles.join(" · ")}</p>
        </div>
        <Button variant="secondary" onClick={onLogout}>
          Sair
        </Button>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Eventos</h2>
        {events === null && <p className="text-muted">Carregando eventos…</p>}
        {events?.length === 0 && <p className="text-muted">Nenhum evento disponível para você.</p>}
        <div className="grid gap-4 md:grid-cols-2">
          {events?.map((event) => (
            <Card key={event.slug} className="flex flex-col gap-4">
              <div>
                <p className="text-sm font-semibold text-accent">{statusLabel[event.status]}</p>
                <p className="text-xl font-bold">{event.title}</p>
                <p className="capitalize text-muted">{formatDate(event.starts_at)}</p>
              </div>
              <dl className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-bg p-3">
                  <dt className="text-xs text-muted">Lugares</dt>
                  <dd className="text-xl font-bold tabular-nums">{event.capacity}</dd>
                </div>
                <div className="rounded-xl bg-bg p-3">
                  <dt className="text-xs text-muted">Aceita até</dt>
                  <dd className="text-xl font-bold tabular-nums">{event.registration_limit}</dd>
                </div>
                <div className="rounded-xl bg-bg p-3">
                  <dt className="text-xs text-muted">Inscritos</dt>
                  <dd className="text-xl font-bold tabular-nums">{event.registered}</dd>
                </div>
              </dl>
              <Link
                href={`/painel/eventos/${event.slug}/configuracoes`}
                className="inline-flex min-h-touch items-center justify-center rounded-xl border border-border px-5 font-semibold hover:bg-border/40"
              >
                Configurações
              </Link>
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
}
