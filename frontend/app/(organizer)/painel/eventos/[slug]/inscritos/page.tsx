"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, apiDownload, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useEventAccess } from "@/lib/use-event-access";
import { useMe } from "@/lib/use-me";

type Person = {
  id: string;
  attendee_name: string;
  age_group: string;
  ticket_type: string;
  priority: boolean;
  accessibility_need: string | null;
  status: "valid" | "used" | "cancelled" | string;
  checked_in_at: string | null;
};

type Registration = {
  code: string;
  status: "confirmed" | "cancelled" | string;
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string | null;
  source: string | null;
  is_test: boolean;
  registered_at: string;
  email_sent: boolean;
  tickets: Person[];
};

type Filter =
  | "all"
  | "active"
  | "missing"
  | "present"
  | "priority"
  | "cancelled"
  | "test";

const FILTERS: Array<{ key: Filter; label: string }> = [
  { key: "all", label: "Todas" },
  { key: "active", label: "Ativas" },
  { key: "missing", label: "Falta entrar" },
  { key: "present", label: "Presentes" },
  { key: "priority", label: "Prioridade" },
  { key: "cancelled", label: "Canceladas" },
  { key: "test", label: "Teste" },
];

const AGE: Record<string, string> = {
  adulto: "Adulto",
  crianca: "Criança",
  idoso: "Idoso",
};

/** Sem acentos e em minúsculas, para a busca achar "joao" em "João". */
function plain(text: string) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function whatsapp(phone: string) {
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 10) return null;
  return `https://wa.me/${digits.length <= 11 ? `55${digits}` : digits}`;
}

function matches(r: Registration, filter: Filter) {
  const live = r.tickets.filter((t) => t.status !== "cancelled");
  switch (filter) {
    case "active":
      return r.status === "confirmed";
    case "missing":
      return r.tickets.some((t) => t.status === "valid");
    case "present":
      return r.tickets.some((t) => t.status === "used");
    case "priority":
      return live.some((t) => t.priority);
    case "cancelled":
      return r.tickets.some((t) => t.status === "cancelled");
    case "test":
      return r.is_test;
    default:
      return true;
  }
}

function PersonStatus({ person }: { person: Person }) {
  if (person.status === "used")
    return (
      <span className="whitespace-nowrap rounded-md bg-success/10 px-2 py-0.5 text-xs font-semibold text-success">
        Presente{person.checked_in_at ? ` · ${person.checked_in_at}` : ""}
      </span>
    );
  if (person.status === "cancelled")
    return (
      <span className="whitespace-nowrap rounded-md bg-danger/10 px-2 py-0.5 text-xs font-semibold text-danger">
        Cancelado
      </span>
    );
  return (
    <span className="whitespace-nowrap rounded-md bg-line/[0.08] px-2 py-0.5 text-xs font-semibold text-soft">
      Inscrito
    </span>
  );
}

type EditForm = {
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  names: Record<string, string>;
};

export default function RegistrationsPage({
  params,
}: {
  params: { slug: string };
}) {
  const me = useMe();
  const access = useEventAccess(params.slug, Boolean(me));
  const canEdit = access?.permissions.edit_event ?? false;
  const base = `/org/events/${params.slug}/registrations`;

  const [regs, setRegs] = useState<Registration[] | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState<EditForm | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Registration[]>(base)
      .then((data) => {
        setRegs(data);
        setError(null);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Sem conexão."),
      );
  }, [base]);

  useEffect(() => {
    if (!me) return;
    load();
    // Atualiza sozinho a cada minuto enquanto a tela estiver aberta.
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [me, load]);

  function replace(updated: Registration) {
    setRegs((list) =>
      list ? list.map((r) => (r.code === updated.code ? updated : r)) : list,
    );
  }

  async function run(key: string, fn: () => Promise<Registration>, ok: string) {
    setBusy(key);
    setNotice(null);
    setError(null);
    try {
      replace(await fn());
      setNotice(ok);
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  function resend(r: Registration) {
    run(
      `resend-${r.code}`,
      () => api<Registration>(`${base}/${r.code}/resend`, { method: "POST" }),
      `Ingresso de ${r.code} reenviado para ${r.buyer_email}.`,
    );
  }

  function cancel(r: Registration, person?: Person) {
    const text = person
      ? `Cancelar o lugar de ${person.attendee_name} (${r.code})? A vaga volta para as inscrições.`
      : `Cancelar a inscrição ${r.code} inteira (${r.buyer_name})? As vagas voltam para as inscrições.`;
    if (!window.confirm(text)) return;
    run(
      `cancel-${person?.id ?? r.code}`,
      () =>
        api<Registration>(`${base}/${r.code}/cancel`, {
          method: "POST",
          body: JSON.stringify({ ticket_ids: person ? [person.id] : [] }),
        }),
      person
        ? `Lugar de ${person.attendee_name} cancelado.`
        : `Inscrição ${r.code} cancelada.`,
    );
  }

  function startEdit(r: Registration) {
    setEditing(r.code);
    setForm({
      buyer_name: r.buyer_name,
      buyer_email: r.buyer_email,
      buyer_phone: r.buyer_phone ?? "",
      names: Object.fromEntries(r.tickets.map((t) => [t.id, t.attendee_name])),
    });
  }

  async function saveEdit(e: FormEvent, r: Registration) {
    e.preventDefault();
    if (!form) return;
    const saved = await run(
      `edit-${r.code}`,
      () =>
        api<Registration>(`${base}/${r.code}`, {
          method: "PUT",
          body: JSON.stringify({
            buyer_name: form.buyer_name,
            buyer_email: form.buyer_email,
            buyer_phone: form.buyer_phone,
            attendees: Object.entries(form.names).map(([id, name]) => ({
              id,
              name,
            })),
          }),
        }),
      `Dados da inscrição ${r.code} salvos.`,
    );
    if (saved) setEditing(null);
  }

  async function onExport() {
    setError(null);
    try {
      await apiDownload(
        `/org/events/${params.slug}/attendees.csv`,
        `inscritos-${params.slug}.csv`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    }
  }

  const totals = useMemo(() => {
    const real = (regs ?? []).filter((r) => !r.is_test);
    const tickets = real.flatMap((r) => r.tickets);
    return {
      families: real.filter((r) => r.status === "confirmed").length,
      people: tickets.filter((t) => t.status !== "cancelled").length,
      present: tickets.filter((t) => t.status === "used").length,
      cancelled: tickets.filter((t) => t.status === "cancelled").length,
    };
  }, [regs]);

  const shown = useMemo(() => {
    const q = plain(query.trim());
    const digits = query.replace(/\D/g, "");
    return (regs ?? []).filter((r) => {
      if (!matches(r, filter)) return false;
      if (!q) return true;
      const text = plain(
        [
          r.code,
          r.buyer_name,
          r.buyer_email,
          r.source ?? "",
          ...r.tickets.map((t) => t.attendee_name),
        ].join(" "),
      );
      const phone = (r.buyer_phone ?? "").replace(/\D/g, "");
      return text.includes(q) || (digits.length >= 4 && phone.includes(digits));
    });
  }, [regs, query, filter]);

  if (!me || (!regs && !error)) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        Carregando…
      </main>
    );
  }

  if (!regs) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center">
        <div className="space-y-3">
          <p className="text-danger">{error}</p>
          <Link href="/painel" className="text-sm font-semibold text-primary">
            ← Voltar ao painel
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/painel" className="text-sm font-semibold text-primary">
            ← Painel
          </Link>
          <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
            Inscritos
          </h1>
          <p className="text-muted">
            Cada cartão é uma inscrição (família), com o responsável e as
            pessoas. Atualiza sozinho a cada minuto.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onExport}>
            Exportar planilha (CSV)
          </Button>
          <Link
            href={`/painel/eventos/${params.slug}/lista`}
            className="inline-flex min-h-touch items-center justify-center whitespace-nowrap rounded-xl border border-border bg-line/[0.03] px-5 text-sm font-semibold hover:bg-line/[0.07]"
          >
            Lista para imprimir
          </Link>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Pessoas inscritas", totals.people],
          ["Inscrições ativas", totals.families],
          ["Presentes", totals.present],
          ["Lugares cancelados", totals.cancelled],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl bg-surface-1 p-3 text-center">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="text-2xl font-bold tabular-nums text-strong">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {regs.some((r) => r.is_test) && (
        <p className="-mt-3 text-xs text-subtle">
          Os totais não contam as inscrições do Teste geral.
        </p>
      )}

      <div className="space-y-3">
        <Input
          label="Buscar"
          type="search"
          placeholder="Nome, responsável, e-mail, telefone ou código"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="Filtrar inscrições"
        >
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              aria-pressed={filter === f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "min-h-[40px] whitespace-nowrap rounded-full border px-4 text-sm font-semibold transition",
                filter === f.key
                  ? "border-primary/50 bg-primary/15 text-primary"
                  : "border-border bg-line/[0.03] text-soft hover:bg-line/[0.07]",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <p className="text-sm text-muted" aria-live="polite">
          Mostrando {shown.length} de {regs.length} inscrições
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

      {regs.length === 0 && (
        <Card>
          <p className="text-muted">
            Ainda não há inscrições. Assim que alguém se inscrever pela página
            do evento, aparece aqui.
          </p>
        </Card>
      )}

      <ul className="space-y-3">
        {shown.map((r) => {
          const expanded = open === r.code || editing === r.code;
          const live = r.tickets.filter((t) => t.status !== "cancelled");
          const wa = r.buyer_phone ? whatsapp(r.buyer_phone) : null;
          return (
            <li key={r.code}>
              <Card
                className={cn(
                  "space-y-3",
                  r.status === "cancelled" && "opacity-70",
                )}
              >
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? null : r.code)}
                  className="flex w-full flex-wrap items-start justify-between gap-2 text-left"
                >
                  <div className="min-w-0">
                    <p className="text-lg font-semibold text-strong">
                      {r.buyer_name}
                    </p>
                    <p className="truncate text-sm text-muted">
                      {live.length} {live.length === 1 ? "pessoa" : "pessoas"} ·{" "}
                      {(live.length ? live : r.tickets)
                        .map((t) => t.attendee_name)
                        .join(", ")}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {r.is_test && (
                      <span className="rounded-md bg-warning/15 px-2 py-0.5 text-xs font-semibold text-warning">
                        Teste
                      </span>
                    )}
                    {r.status === "cancelled" && (
                      <span className="rounded-md bg-danger/10 px-2 py-0.5 text-xs font-semibold text-danger">
                        Cancelada
                      </span>
                    )}
                    {live.some((t) => t.priority) && (
                      <span className="rounded-md bg-primary/15 px-2 py-0.5 text-xs font-semibold text-primary">
                        Prioridade
                      </span>
                    )}
                    <span className="font-mono text-sm text-soft">
                      {r.code}
                    </span>
                    <span aria-hidden className="text-subtle">
                      {expanded ? "▴" : "▾"}
                    </span>
                  </div>
                </button>

                {expanded && editing !== r.code && (
                  <div className="space-y-4 border-t border-border pt-3">
                    <dl className="grid gap-2 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-xs text-muted">E-mail</dt>
                        <dd>
                          <a
                            href={`mailto:${r.buyer_email}`}
                            className="break-all text-fg underline-offset-2 hover:underline"
                          >
                            {r.buyer_email}
                          </a>
                          {!r.email_sent && r.status === "confirmed" && (
                            <span className="ml-2 text-xs text-warning">
                              ingresso não enviado
                            </span>
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted">Telefone</dt>
                        <dd className="flex flex-wrap items-center gap-3">
                          {r.buyer_phone ? (
                            <>
                              <a
                                href={`tel:${r.buyer_phone.replace(/[^\d+]/g, "")}`}
                                className="text-fg underline-offset-2 hover:underline"
                              >
                                {r.buyer_phone}
                              </a>
                              {wa && (
                                <a
                                  href={wa}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-xs font-semibold text-primary"
                                >
                                  WhatsApp ↗
                                </a>
                              )}
                            </>
                          ) : (
                            <span className="text-subtle">Não informado</span>
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted">Inscrito em</dt>
                        <dd className="text-fg">{r.registered_at}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted">Origem</dt>
                        <dd className="text-fg">{r.source ?? "Direto"}</dd>
                      </div>
                    </dl>

                    <ul className="divide-y divide-border rounded-xl border border-border">
                      {r.tickets.map((t) => (
                        <li
                          key={t.id}
                          className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
                        >
                          <div className="min-w-0">
                            <p
                              className={cn(
                                "font-medium text-fg",
                                t.status === "cancelled" &&
                                  "text-subtle line-through",
                              )}
                            >
                              {t.attendee_name}
                            </p>
                            <p className="text-xs text-muted">
                              {AGE[t.age_group] ?? t.age_group} ·{" "}
                              {t.ticket_type}
                              {t.accessibility_need &&
                                ` · ${t.accessibility_need}`}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <PersonStatus person={t} />
                            {canEdit &&
                              t.status === "valid" &&
                              live.length > 1 && (
                                <Button
                                  variant="ghost-danger"
                                  className="min-h-[36px] px-3 text-xs"
                                  loading={busy === `cancel-${t.id}`}
                                  onClick={() => cancel(r, t)}
                                >
                                  Cancelar
                                </Button>
                              )}
                          </div>
                        </li>
                      ))}
                    </ul>

                    {r.status === "confirmed" && (
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="secondary"
                          loading={busy === `resend-${r.code}`}
                          onClick={() => resend(r)}
                        >
                          Reenviar ingresso
                        </Button>
                        {canEdit && (
                          <Button
                            variant="secondary"
                            onClick={() => startEdit(r)}
                          >
                            Corrigir dados
                          </Button>
                        )}
                        {canEdit &&
                          r.tickets.some((t) => t.status === "valid") && (
                            <Button
                              variant="ghost-danger"
                              loading={busy === `cancel-${r.code}`}
                              onClick={() => cancel(r)}
                            >
                              Cancelar inscrição
                            </Button>
                          )}
                      </div>
                    )}
                  </div>
                )}

                {editing === r.code && form && (
                  <form
                    onSubmit={(e) => saveEdit(e, r)}
                    className="space-y-4 border-t border-border pt-3"
                  >
                    <div className="grid gap-4 sm:grid-cols-3">
                      <Input
                        label="Responsável"
                        required
                        minLength={2}
                        value={form.buyer_name}
                        onChange={(e) =>
                          setForm({ ...form, buyer_name: e.target.value })
                        }
                      />
                      <Input
                        label="E-mail"
                        type="email"
                        inputMode="email"
                        required
                        value={form.buyer_email}
                        onChange={(e) =>
                          setForm({ ...form, buyer_email: e.target.value })
                        }
                      />
                      <Input
                        label="Telefone"
                        type="tel"
                        inputMode="tel"
                        value={form.buyer_phone}
                        onChange={(e) =>
                          setForm({ ...form, buyer_phone: e.target.value })
                        }
                      />
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {r.tickets.map((t, i) => (
                        <Input
                          key={t.id}
                          label={`Pessoa ${i + 1}`}
                          required
                          minLength={2}
                          value={form.names[t.id] ?? ""}
                          onChange={(e) =>
                            setForm({
                              ...form,
                              names: { ...form.names, [t.id]: e.target.value },
                            })
                          }
                        />
                      ))}
                    </div>
                    <p className="text-sm text-muted">
                      Trocou o e-mail? Depois de salvar, use “Reenviar ingresso”
                      para mandar os QR Codes para o endereço novo.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button type="submit" loading={busy === `edit-${r.code}`}>
                        Salvar
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setEditing(null)}
                      >
                        Voltar
                      </Button>
                    </div>
                  </form>
                )}
              </Card>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
