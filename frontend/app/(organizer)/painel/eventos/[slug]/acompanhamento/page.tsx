"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Count = { label: string; people: number };
type Stats = {
  capacity: number;
  registration_limit: number;
  registered: number;
  present: number;
  cancelled: number;
  orders: number;
  priority: number;
  by_age: Count[];
  by_day: Count[];
  by_source: Count[];
  waitlist: Count[];
  emails_not_sent: number;
};
type Broadcast = {
  id: number;
  kind: "confirm" | "tomorrow";
  status: "running" | "done";
  requested_by: string;
  total: number;
  sent: number;
  failed: number;
  created_at: string;
  finished_at: string | null;
};
type WaitRow = {
  id: string;
  position: number | null;
  name: string;
  email: string;
  phone: string | null;
  quantity: number;
  status: "waiting" | "notified" | "registered" | "expired" | "left";
  created_at: string;
  hold_until: string | null;
};

const REMINDERS = [
  {
    kind: "confirm" as const,
    title: "Faltam poucos dias",
    when: "Sugestão: segunda, 16/11",
    text: "Lembra a data, reenvia os ingressos e pede para quem não puder ir cancelar — a vaga vai para a lista de espera.",
  },
  {
    kind: "tomorrow" as const,
    title: "É amanhã!",
    when: "Sugestão: quarta, 18/11",
    text: "Horário, endereço, “chegue cedo” e os QR Codes de novo, para usar mesmo sem internet na porta.",
  },
];

const WAIT_STATUS: Record<WaitRow["status"], string> = {
  waiting: "Na fila",
  notified: "Avisado",
  registered: "Inscrito",
  expired: "Não usou",
  left: "Saiu",
};

const hm = (iso: string) =>
  `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}`;

function Tile({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="text-3xl font-bold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

function CountTable({ title, rows }: { title: string; rows: Count[] }) {
  return (
    <Card className="space-y-2 p-4 sm:p-5">
      <h3 className="font-semibold">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">Sem dados ainda.</p>
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.label}
                className="border-b border-border last:border-0"
              >
                <td className="py-1.5">{r.label}</td>
                <td className="py-1.5 text-right font-semibold tabular-nums">
                  {r.people}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

export default function FollowUpPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const base = `/org/events/${params.slug}`;
  const [stats, setStats] = useState<Stats | null>(null);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [recipients, setRecipients] = useState<number | null>(null);
  const [queue, setQueue] = useState<WaitRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canEdit =
    me?.memberships.some((m) => m.role === "owner" || m.role === "admin") ??
    false;

  const load = useCallback(async () => {
    try {
      const [s, b, r, q] = await Promise.all([
        api<Stats>(`${base}/stats`),
        api<Broadcast[]>(`${base}/broadcasts`),
        api<{ recipients: number }>(`${base}/broadcasts/recipients`),
        api<WaitRow[]>(`${base}/waitlist`),
      ]);
      setStats(s);
      setBroadcasts(b);
      setRecipients(r.recipients);
      setQueue(q);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    }
  }, [base]);

  const running = broadcasts.some((b) => b.status === "running");
  useEffect(() => {
    if (!me) return;
    load();
    const timer = setInterval(load, running ? 2000 : 30000);
    return () => clearInterval(timer);
  }, [me, load, running]);

  async function send(kind: Broadcast["kind"], title: string) {
    const last = broadcasts.find((b) => b.kind === kind);
    const warning = last
      ? ` Atenção: “${title}” já foi enviado em ${hm(last.created_at)}.`
      : "";
    if (
      !window.confirm(
        `Enviar “${title}” para ${recipients} inscrições agora?${warning}`,
      )
    )
      return;
    setBusy(true);
    setNotice(null);
    try {
      await api(`${base}/broadcasts`, {
        method: "POST",
        body: JSON.stringify({ kind }),
      });
      setNotice("Envio iniciado. Acompanhe o progresso abaixo.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(false);
    }
  }

  async function notifyQueue() {
    setBusy(true);
    try {
      const r = await api<{ notified: number; free_seats: number }>(
        `${base}/waitlist/notify`,
        {
          method: "POST",
        },
      );
      setNotice(
        r.notified
          ? `${r.notified} ${r.notified === 1 ? "inscrição avisada" : "inscrições avisadas"} por e-mail.`
          : "Nenhuma vaga livre para chamar a fila agora.",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(false);
    }
  }

  if (!me || !stats) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  const waiting = queue.filter(
    (q) => q.status === "waiting" || q.status === "notified",
  );

  return (
    <main className="mx-auto w-full max-w-5xl space-y-8 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-2xl font-bold">
          Acompanhamento · CANTEMOS 2026
        </h1>
        <p className="text-sm text-muted">
          Atualiza sozinho a cada 30 segundos.
        </p>
      </div>

      {notice && (
        <p
          role="status"
          className="rounded-xl bg-success/10 px-4 py-3 text-sm text-success"
        >
          {notice}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
        >
          {error}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Números</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Tile
            label="Pessoas inscritas"
            value={stats.registered}
            hint={`de ${stats.registration_limit} aceitas · ${stats.capacity} lugares`}
          />
          <Tile label="Inscrições (famílias)" value={stats.orders} />
          <Tile label="Presentes" value={stats.present} />
          <Tile
            label="Prioritários"
            value={stats.priority}
            hint={`${stats.cancelled} cancelados`}
          />
        </div>
        {stats.emails_not_sent > 0 && (
          <p
            role="alert"
            className="rounded-xl bg-warning/20 px-4 py-3 text-sm"
          >
            {stats.emails_not_sent}{" "}
            {stats.emails_not_sent === 1
              ? "inscrição não recebeu"
              : "inscrições não receberam"}{" "}
            o e-mail do ingresso (falha no envio). Os lembretes abaixo reenviam
            os QR Codes.
          </p>
        )}
        <div className="grid gap-3 md:grid-cols-3">
          <CountTable title="Inscrições por dia" rows={stats.by_day} />
          <CountTable title="Origem (links ?origem=)" rows={stats.by_source} />
          <CountTable title="Faixa etária" rows={stats.by_age} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Lembretes por e-mail</h2>
        <p className="text-sm text-muted">
          Vão para as {recipients ?? "…"} inscrições ativas, com os QR Codes. O
          envio acontece aos poucos (cerca de 1 por segundo) para respeitar o
          limite do Gmail.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {REMINDERS.map((r) => (
            <Card key={r.kind} className="flex flex-col gap-3">
              <div>
                <p className="text-sm font-semibold text-accent">{r.when}</p>
                <h3 className="text-lg font-bold">{r.title}</h3>
                <p className="text-sm text-muted">{r.text}</p>
              </div>
              {canEdit && (
                <Button
                  className="mt-auto"
                  loading={busy}
                  disabled={running || !recipients}
                  onClick={() => send(r.kind, r.title)}
                >
                  Enviar para {recipients ?? 0} inscrições
                </Button>
              )}
            </Card>
          ))}
        </div>
        {broadcasts.length > 0 && (
          <Card className="p-4 sm:p-5">
            <h3 className="mb-2 font-semibold">Envios</h3>
            <ul className="divide-y divide-border text-sm">
              {broadcasts.map((b) => (
                <li
                  key={b.id}
                  className="flex flex-wrap items-center justify-between gap-2 py-2"
                >
                  <span>
                    <strong>
                      {REMINDERS.find((r) => r.kind === b.kind)?.title}
                    </strong>{" "}
                    · {hm(b.created_at)} por {b.requested_by}
                  </span>
                  <span
                    className={
                      b.status === "running" ? "font-semibold text-primary" : ""
                    }
                  >
                    {b.status === "running" ? "Enviando… " : "Concluído · "}
                    {b.sent}/{b.total}
                    {b.failed > 0 && (
                      <span className="text-danger"> · {b.failed} falhas</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">
            Lista de espera ({waiting.length})
          </h2>
          {canEdit && (
            <Button variant="secondary" loading={busy} onClick={notifyQueue}>
              Avisar próximos da fila
            </Button>
          )}
        </div>
        <p className="text-sm text-muted">
          Quando abre vaga, a fila é avisada sozinha por ordem de chegada e a
          vaga fica guardada por 24 h. Use o botão se aumentar a lotação e
          quiser chamar na hora.
        </p>
        {queue.length === 0 ? (
          <Card>
            <p className="text-muted">Ninguém na lista de espera.</p>
          </Card>
        ) : (
          <Card className="overflow-x-auto p-0 sm:p-0">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted">
                  <th className="px-4 py-2">#</th>
                  <th className="px-4 py-2">Nome</th>
                  <th className="px-4 py-2">Pessoas</th>
                  <th className="px-4 py-2">Situação</th>
                  <th className="px-4 py-2">Contato</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((q) => (
                  <tr
                    key={q.id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-4 py-2 tabular-nums">
                      {q.position ?? "–"}
                    </td>
                    <td className="px-4 py-2 font-medium">{q.name}</td>
                    <td className="px-4 py-2 tabular-nums">{q.quantity}</td>
                    <td className="px-4 py-2">
                      {WAIT_STATUS[q.status]}
                      {q.status === "notified" && q.hold_until && (
                        <span className="block text-xs text-muted">
                          vaga guardada até {hm(q.hold_until)}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {q.email}
                      {q.phone && (
                        <span className="block text-xs text-muted">
                          {q.phone}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>
    </main>
  );
}
