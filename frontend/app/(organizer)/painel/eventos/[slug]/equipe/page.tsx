"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useMe } from "@/lib/use-me";

type EventRole = "admin" | "manager" | "checkin";
type Member = {
  id: string;
  name: string;
  email: string;
  role: string;
  label: string;
  source: "igreja" | "evento";
  pending: boolean;
  editable: boolean;
  is_me: boolean;
};
type Team = { members: Member[]; can_manage: boolean };

const LEVELS: Array<{ role: EventRole; label: string; description: string }> = [
  {
    role: "admin",
    label: "Administrador do evento",
    description:
      "Tudo neste evento: configurações, identidade visual, mensagens, lembretes, lista de espera, teste geral, código da recepção e equipe.",
  },
  {
    role: "manager",
    label: "Produção",
    description:
      "Acompanha: números, inscritos, planilha, lista impressa e recepção. Vê as configurações, mas não altera.",
  },
  {
    role: "checkin",
    label: "Recepção",
    description:
      "Só a tela de check-in, com login próprio. Desfaz apenas as próprias leituras.",
  },
];

const selectClass =
  "min-h-touch rounded-xl border border-border bg-surface px-3 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-primary/30";

export default function TeamPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const base = `/org/events/${params.slug}/team`;
  const [team, setTeam] = useState<Team | null>(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    role: "manager" as EventRole,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Team>(base)
      .then(setTeam)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [base]);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  async function run(key: string, fn: () => Promise<unknown>, success: string) {
    setBusy(key);
    setNotice(null);
    setError(null);
    try {
      const result = await fn();
      if (result && typeof result === "object" && "members" in result)
        setTeam(result as Team);
      setNotice(success);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(null);
    }
  }

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const level = LEVELS.find((l) => l.role === form.role)?.label;
    run(
      "add",
      async () => {
        const result = await api<Team>(base, {
          method: "POST",
          body: JSON.stringify(form),
        });
        setForm({ name: "", email: "", role: form.role });
        return result;
      },
      `${form.name.split(" ")[0]} foi adicionado(a) como ${level}. Enviamos um e-mail com o acesso.`,
    );
  }

  if (!me || !team) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  const church = team.members.filter((m) => m.source === "igreja");
  const eventTeam = team.members.filter((m) => m.source === "evento");

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Equipe do evento
        </h1>
        <p className="text-muted">
          Quem pode gerir e ajustar este evento. Os voluntários da porta
          continuam entrando só com o código da recepção, sem conta.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <Card className="space-y-3">
            <h2 className="text-title font-semibold text-strong">
              Equipe deste evento ({eventTeam.length})
            </h2>
            {eventTeam.length === 0 && (
              <p className="rounded-xl bg-line/[0.05] px-4 py-3 text-sm text-muted">
                Ninguém adicionado ainda.
              </p>
            )}
            <ul className="divide-y divide-border">
              {eventTeam.map((m) => (
                <li
                  key={m.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-fg">
                      {m.name}{" "}
                      {m.is_me && (
                        <span className="text-sm text-subtle">(você)</span>
                      )}
                    </p>
                    <p className="truncate text-sm text-muted">{m.email}</p>
                    {m.pending && (
                      <p className="text-xs text-warning">
                        Convite pendente: ainda não criou a senha
                      </p>
                    )}
                  </div>
                  {m.editable ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        aria-label={`Nível de ${m.name}`}
                        value={m.role}
                        disabled={busy !== null}
                        onChange={(e) =>
                          run(
                            `role-${m.id}`,
                            () =>
                              api<Team>(`${base}/${m.id}`, {
                                method: "PUT",
                                body: JSON.stringify({ role: e.target.value }),
                              }),
                            `Nível de ${m.name.split(" ")[0]} atualizado.`,
                          )
                        }
                        className={selectClass}
                      >
                        {LEVELS.map((l) => (
                          <option key={l.role} value={l.role}>
                            {l.label}
                          </option>
                        ))}
                      </select>
                      {m.pending && (
                        <Button
                          variant="ghost"
                          loading={busy === `resend-${m.id}`}
                          onClick={() =>
                            run(
                              `resend-${m.id}`,
                              () =>
                                api(`${base}/${m.id}/resend`, {
                                  method: "POST",
                                }),
                              `Convite reenviado para ${m.email}.`,
                            )
                          }
                        >
                          Reenviar convite
                        </Button>
                      )}
                      <Button
                        variant="ghost-danger"
                        loading={busy === `del-${m.id}`}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Remover ${m.name} da equipe deste evento?`,
                            )
                          )
                            run(
                              `del-${m.id}`,
                              () =>
                                api<Team>(`${base}/${m.id}`, {
                                  method: "DELETE",
                                }),
                              `${m.name.split(" ")[0]} foi removido(a) da equipe.`,
                            );
                        }}
                      >
                        Remover
                      </Button>
                    </div>
                  ) : (
                    <span className="whitespace-nowrap rounded-md bg-line/[0.08] px-3 py-1 text-sm text-soft">
                      {m.label}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Card>

          {team.can_manage && (
            <Card>
              <form onSubmit={onAdd} className="space-y-4">
                <h2 className="text-title font-semibold text-strong">
                  Adicionar pessoa
                </h2>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input
                    label="Nome"
                    required
                    minLength={2}
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                  <Input
                    label="E-mail"
                    type="email"
                    inputMode="email"
                    required
                    value={form.email}
                    onChange={(e) =>
                      setForm({ ...form, email: e.target.value })
                    }
                  />
                </div>
                <fieldset className="space-y-2">
                  <legend className="mb-1 text-sm font-medium text-soft">
                    Nível
                  </legend>
                  {LEVELS.map((l) => (
                    <label
                      key={l.role}
                      className={cn(
                        "flex cursor-pointer gap-3 rounded-xl border p-3",
                        form.role === l.role
                          ? "border-primary/40 bg-primary/10"
                          : "border-border bg-line/[0.03]",
                      )}
                    >
                      <input
                        type="radio"
                        name="role"
                        checked={form.role === l.role}
                        onChange={() => setForm({ ...form, role: l.role })}
                        className="mt-1 size-4 accent-[rgb(var(--rgb-brand))]"
                      />
                      <span>
                        <span className="block font-semibold text-fg">
                          {l.label}
                        </span>
                        <span className="block text-sm text-muted">
                          {l.description}
                        </span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                <p className="text-sm text-muted">
                  Quem ainda não tem conta recebe um convite por e-mail para
                  criar a senha (vale 7 dias). Quem já tem conta recebe só um
                  aviso.
                </p>
                <Button type="submit" loading={busy === "add"}>
                  Adicionar à equipe
                </Button>
              </form>
            </Card>
          )}

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
        </div>

        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <Card className="space-y-3">
            <h2 className="text-title font-semibold text-strong">
              Responsáveis da igreja
            </h2>
            <p className="text-sm text-muted">
              Têm acesso total a todos os eventos. Gerenciados no nível da
              igreja.
            </p>
            <ul className="space-y-2">
              {church.map((m) => (
                <li key={m.id} className="rounded-xl bg-line/[0.05] px-3 py-2">
                  <p className="font-semibold text-fg">
                    {m.name}{" "}
                    {m.is_me && (
                      <span className="text-sm text-subtle">(você)</span>
                    )}
                  </p>
                  <p className="text-xs text-muted">{m.label}</p>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="space-y-3">
            <h2 className="text-title font-semibold text-strong">Níveis</h2>
            <ol className="space-y-3 text-sm">
              <li>
                <p className="font-semibold text-fg">1. Responsável (igreja)</p>
                <p className="text-muted">
                  Tudo em todos os eventos + nome e logo da igreja.
                </p>
              </li>
              {LEVELS.map((l, i) => (
                <li key={l.role}>
                  <p className="font-semibold text-fg">
                    {i + 2}. {l.label}
                  </p>
                  <p className="text-muted">{l.description}</p>
                </li>
              ))}
            </ol>
          </Card>
        </aside>
      </div>
    </main>
  );
}
