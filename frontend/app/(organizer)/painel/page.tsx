"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError, logout, type EventSummary } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const roleLabel: Record<string, string> = {
  owner: "Responsável",
  admin: "Administrador",
  manager: "Produção",
  checkin: "Recepção",
};

// Botão-link: sempre em uma linha só.
const linkButton =
  "inline-flex min-h-touch items-center justify-center whitespace-nowrap rounded-xl px-5 text-sm";

const statusLabel: Record<EventSummary["status"], string> = {
  draft: "Rascunho",
  published: "Publicado",
  open: "Inscrições abertas",
  closed: "Inscrições encerradas",
  finished: "Finalizado",
};

function formatDate(value: string | null) {
  if (!value) return "Data a definir";
  const text = new Date(value).toLocaleString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
  // "quinta-feira, 19 de novembro às 18:30" → só a primeira letra maiúscula
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function PainelPage() {
  const router = useRouter();
  const me = useMe();
  const [events, setEvents] = useState<EventSummary[] | null>(null);
  const [emailStatus, setEmailStatus] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);
  const [sendingEmail, setSendingEmail] = useState(false);

  async function onTestEmail() {
    setSendingEmail(true);
    setEmailStatus(null);
    try {
      const { sent_to } = await api<{ sent_to: string }>("/org/test-email", {
        method: "POST",
      });
      setEmailStatus({
        ok: true,
        text: `E-mail enviado para ${sent_to}. Confira a caixa de entrada.`,
      });
    } catch (err) {
      setEmailStatus({
        ok: false,
        text:
          err instanceof ApiError
            ? err.message
            : "Sem conexão. Tente novamente.",
      });
    } finally {
      setSendingEmail(false);
    }
  }

  useEffect(() => {
    if (me)
      api<EventSummary[]>("/org/events")
        .then(setEvents)
        .catch(() => setEvents([]));
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

  const roles = me.memberships.map(
    (m) => `${roleLabel[m.role] ?? m.role} · ${m.organization_name}`,
  );

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Painel</p>
          <h1 className="text-3xl font-normal leading-tight text-strong">
            Olá, {me.name.split(" ")[0]}
          </h1>
          <p className="text-sm text-muted">{roles.join(" · ")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/painel/perfil"
            className="inline-flex min-h-touch shrink-0 items-center justify-center whitespace-nowrap rounded-xl border border-border bg-line/[0.03] px-5 text-sm font-semibold hover:bg-line/[0.07]"
          >
            Meu perfil
          </Link>
          <Link
            href="/painel/igreja"
            className="inline-flex min-h-touch shrink-0 whitespace-nowrap items-center justify-center rounded-xl border border-border bg-line/[0.03] px-5 text-sm font-semibold hover:bg-line/[0.07]"
          >
            Igreja
          </Link>
          <Button variant="secondary" onClick={onLogout}>
            Sair
          </Button>
        </div>
      </header>

      <section className="space-y-3">
        <h2 className="text-title font-semibold text-strong">Eventos</h2>
        {events === null && <p className="text-muted">Carregando eventos…</p>}
        {events?.length === 0 && (
          <p className="text-muted">Nenhum evento disponível para você.</p>
        )}
        <div className="grid gap-4">
          {events?.map((event) => (
            <Card key={event.slug} className="flex flex-col gap-4">
              <div>
                <p className="eyebrow">{statusLabel[event.status]}</p>
                <p className="text-xl font-bold">{event.title}</p>
                <p className="text-muted">{formatDate(event.starts_at)}</p>
              </div>
              <dl className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-surface-1 p-3">
                  <dt className="text-xs text-muted">Lugares</dt>
                  <dd className="text-xl font-bold tabular-nums">
                    {event.capacity}
                  </dd>
                </div>
                <div className="rounded-xl bg-surface-1 p-3">
                  <dt className="text-xs text-muted">Aceita até</dt>
                  <dd className="text-xl font-bold tabular-nums">
                    {event.registration_limit}
                  </dd>
                </div>
                <div className="rounded-xl bg-surface-1 p-3">
                  <dt className="text-xs text-muted">Inscritos</dt>
                  <dd className="text-xl font-bold tabular-nums">
                    {event.registered}
                  </dd>
                </div>
              </dl>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                <Link
                  href={`/painel/eventos/${event.slug}/recepcao`}
                  className={`${linkButton} bg-brand font-bold uppercase tracking-wide text-primary-fg shadow-sm transition hover:-translate-y-px hover:shadow-cta`}
                >
                  Recepção / check-in
                </Link>
                {[
                  ["identidade", "Identidade visual"],
                  ["mensagens", "Mensagens de e-mail"],
                  ["configuracoes", "Configurações"],
                  ["acompanhamento", "Números e lembretes"],
                ].map(([path, label]) => (
                  <Link
                    key={path}
                    href={`/painel/eventos/${event.slug}/${path}`}
                    className={`${linkButton} border border-border bg-line/[0.03] font-semibold hover:bg-line/[0.07]`}
                  >
                    {label}
                  </Link>
                ))}
                {event.status !== "draft" && (
                  <a
                    href={`/e/${event.slug}`}
                    target="_blank"
                    className={`${linkButton} border border-border bg-line/[0.03] font-semibold hover:bg-line/[0.07]`}
                  >
                    Página pública ↗
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>
      </section>

      {me.memberships.some((m) => m.role === "owner" || m.role === "admin") && (
        <section className="space-y-3">
          <h2 className="text-title font-semibold text-strong">E-mail</h2>
          <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-muted">
              Confirme que os ingressos vão chegar: envie um e-mail de teste
              para {me.email}.
            </p>
            <Button
              variant="secondary"
              loading={sendingEmail}
              onClick={onTestEmail}
            >
              Enviar e-mail de teste
            </Button>
          </Card>
          {emailStatus && (
            <p
              role={emailStatus.ok ? "status" : "alert"}
              className={`rounded-xl px-4 py-3 text-sm ${
                emailStatus.ok
                  ? "bg-success/10 text-success"
                  : "bg-danger/10 text-danger"
              }`}
            >
              {emailStatus.text}
            </p>
          )}
        </section>
      )}
    </main>
  );
}
