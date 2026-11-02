"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NumberField } from "@/components/ui/number-field";
import {
  api,
  ApiError,
  type EventSettings,
  type EventSettingsInput,
  type ReservedQuota,
} from "@/lib/api";
import { useMe } from "@/lib/use-me";

const toInput = (value: string | null) => (value ? value.slice(0, 16) : "");

function Row({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 ${strong ? "font-semibold" : ""}`}>
      <dt className={strong ? "" : "text-muted"}>{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}

export default function EventSettingsPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const [saved, setSaved] = useState<EventSettings | null>(null);
  const [form, setForm] = useState<EventSettingsInput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canEdit = me?.memberships.some((m) => m.role === "owner" || m.role === "admin") ?? false;

  useEffect(() => {
    if (!me) return;
    api<EventSettings>(`/org/events/${params.slug}/settings`)
      .then((data) => {
        setSaved(data);
        setForm({
          starts_at: toInput(data.starts_at),
          doors_open_at: toInput(data.doors_open_at),
          capacity: data.capacity,
          overbooking_percent: data.overbooking_percent,
          max_tickets_per_order: data.max_tickets_per_order,
          priority_quota: data.priority_quota,
          reserved_quotas: data.reserved_quotas.map(({ id, name, quantity }) => ({
            id,
            name,
            quantity,
          })),
        });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Falha ao carregar."));
  }, [me, params.slug]);

  // Prévia calculada no navegador (o servidor recalcula e valida ao salvar).
  const preview = useMemo(() => {
    if (!form) return null;
    const limit = form.capacity + Math.floor((form.capacity * form.overbooking_percent) / 100);
    const reserved = form.reserved_quotas.reduce((sum, q) => sum + (q.quantity || 0), 0);
    return { limit, reserved, general: limit - form.priority_quota - reserved };
  }, [form]);

  function update<K extends keyof EventSettingsInput>(key: K, value: EventSettingsInput[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setNotice(null);
  }

  function updateQuota(index: number, changes: Partial<ReservedQuota>) {
    if (!form) return;
    update(
      "reserved_quotas",
      form.reserved_quotas.map((q, i) => (i === index ? { ...q, ...changes } : q)),
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const data = await api<EventSettings>(`/org/events/${params.slug}/settings`, {
        method: "PUT",
        body: JSON.stringify({ ...form, doors_open_at: form.doors_open_at || null }),
      });
      setSaved(data);
      setForm((current) =>
        current
          ? {
              ...current,
              reserved_quotas: data.reserved_quotas.map(({ id, name, quantity }) => ({
                id,
                name,
                quantity,
              })),
            }
          : current,
      );
      setNotice("Configurações salvas.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  if (!form || !saved || !preview) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted" aria-busy>
        {error ?? "Carregando…"}
      </main>
    );
  }

  const issuedFor = (id?: string) => saved.reserved_quotas.find((q) => q.id === id)?.issued ?? 0;

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 md:py-10">
      <Link href="/painel" className="text-sm font-semibold text-primary">
        ← Painel
      </Link>
      <h1 className="mb-1 mt-2 text-2xl font-bold">Configurações · {saved.title}</h1>
      <p className="mb-6 text-muted">
        Todos os limites podem ser aumentados ou reduzidos a qualquer momento — só não podem
        ficar abaixo do que já foi emitido.
      </p>

      <form onSubmit={onSubmit} className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <fieldset disabled={!canEdit || saving} className="space-y-6">
          <Card className="space-y-4">
            <h2 className="text-lg font-semibold">Data e horário</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Início"
                type="datetime-local"
                value={form.starts_at}
                onChange={(e) => update("starts_at", e.target.value)}
                required
              />
              <Input
                label="Abertura das portas"
                type="datetime-local"
                value={form.doors_open_at ?? ""}
                onChange={(e) => update("doors_open_at", e.target.value)}
              />
            </div>
          </Card>

          <Card className="space-y-4">
            <h2 className="text-lg font-semibold">Lotação e inscrições</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <NumberField
                label="Lugares no local"
                value={form.capacity}
                min={1}
                onChange={(v) => update("capacity", v)}
              />
              <NumberField
                label="Margem para faltas"
                value={form.overbooking_percent}
                max={100}
                step={5}
                suffix="%"
                hint={`Aceita até ${preview.limit} inscrições.`}
                onChange={(v) => update("overbooking_percent", v)}
              />
              <NumberField
                label="Máximo de ingressos por inscrição"
                value={form.max_tickets_per_order}
                min={1}
                max={50}
                hint="Quantas pessoas um responsável pode inscrever de uma vez."
                onChange={(v) => update("max_tickets_per_order", v)}
              />
              <NumberField
                label="Cota de prioridade"
                value={form.priority_quota}
                hint="PCD, idosos e gestantes."
                onChange={(v) => update("priority_quota", v)}
              />
            </div>
          </Card>

          <Card className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Lugares reservados</h2>
              <p className="text-sm text-muted">
                Cotas fora da inscrição pública — ex.: família do coral, equipe, convidados. A
                secretaria emite esses ingressos.
              </p>
            </div>
            {form.reserved_quotas.length === 0 && (
              <p className="rounded-xl bg-bg px-4 py-3 text-sm text-muted">
                Nenhuma cota reservada.
              </p>
            )}
            <ul className="space-y-4">
              {form.reserved_quotas.map((quota, index) => {
                const issued = issuedFor(quota.id);
                return (
                  <li
                    key={quota.id ?? `nova-${index}`}
                    className="grid gap-3 rounded-xl border border-border p-4 sm:grid-cols-[1fr_200px_auto] sm:items-end"
                  >
                    <Input
                      label="Nome da cota"
                      value={quota.name}
                      placeholder="Ex.: Família do coral"
                      onChange={(e) => updateQuota(index, { name: e.target.value })}
                      required
                      minLength={2}
                    />
                    <NumberField
                      label="Lugares"
                      value={quota.quantity}
                      min={issued}
                      hint={issued ? `${issued} já emitidos` : undefined}
                      onChange={(v) => updateQuota(index, { quantity: v })}
                    />
                    <Button
                      type="button"
                      variant="ghost-danger"
                      disabled={issued > 0}
                      title={issued > 0 ? "Cota com ingressos emitidos" : undefined}
                      onClick={() =>
                        update(
                          "reserved_quotas",
                          form.reserved_quotas.filter((_, i) => i !== index),
                        )
                      }
                    >
                      Remover
                    </Button>
                  </li>
                );
              })}
            </ul>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                update("reserved_quotas", [...form.reserved_quotas, { name: "", quantity: 0 }])
              }
            >
              + Adicionar cota reservada
            </Button>
          </Card>
        </fieldset>

        <aside className="lg:sticky lg:top-6 lg:self-start">
          <Card className="space-y-4">
            <h2 className="text-lg font-semibold">Resumo</h2>
            <dl className="space-y-2">
              <Row label="Lugares no local" value={form.capacity} />
              <Row
                label={`Margem (${form.overbooking_percent}%)`}
                value={preview.limit - form.capacity}
              />
              <Row label="Total de inscrições aceitas" value={preview.limit} strong />
              <hr className="border-border" />
              <Row label="Prioridade" value={form.priority_quota} />
              <Row label="Reservados" value={preview.reserved} />
              <Row label="Inscrição pública" value={preview.general} strong />
              <hr className="border-border" />
              <Row label="Inscritos até agora" value={saved.registered} />
            </dl>
            {preview.general < 0 && (
              <p className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">
                Prioridade + reservados ultrapassam o total aceito.
              </p>
            )}
            {preview.limit > form.capacity && (
              <p className="rounded-xl bg-warning/15 px-4 py-3 text-sm">
                Se todos comparecerem, {preview.limit - form.capacity} pessoas ficarão sem lugar
                sentado. Tenha um plano para elas (cadeiras extras, anexo, telão).
              </p>
            )}
            {error && (
              <p role="alert" className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">
                {error}
              </p>
            )}
            {notice && (
              <p role="status" className="rounded-xl bg-success/10 px-4 py-3 text-sm text-success">
                {notice}
              </p>
            )}
            {canEdit ? (
              <Button type="submit" block loading={saving} disabled={preview.general < 0}>
                Salvar configurações
              </Button>
            ) : (
              <p className="text-sm text-muted">Somente administradores podem alterar.</p>
            )}
          </Card>
        </aside>
      </form>
    </main>
  );
}
