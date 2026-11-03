"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NumberField } from "@/components/ui/number-field";
import { api, ApiError, type PublicEvent } from "@/lib/api";

type Joined = { position: number; quantity: number; already: boolean };

export function WaitlistForm({ event }: { event: PublicEvent }) {
  const [quantity, setQuantity] = useState(1);
  const [consent, setConsent] = useState(false);
  const [joined, setJoined] = useState<Joined | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    if (!consent) {
      setError(
        "Para continuar, aceite os termos de uso e a política de privacidade.",
      );
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setJoined(
        await api<Joined>(`/public/events/${event.slug}/waitlist`, {
          method: "POST",
          body: JSON.stringify({
            name: form.get("name"),
            email: form.get("email"),
            phone: form.get("phone") || null,
            quantity,
            consent,
            website: form.get("website") || null,
          }),
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (joined) {
    return (
      <Card role="status" className="space-y-2 border-success/40 text-center">
        <p className="text-lg font-bold">
          {joined.already
            ? "Você já está na lista de espera"
            : "Você entrou na lista de espera!"}
        </p>
        <p className="text-muted">
          Posição <strong className="text-fg">{joined.position}</strong> ·{" "}
          {joined.quantity} {joined.quantity === 1 ? "pessoa" : "pessoas"}. Se
          abrir vaga, você recebe um e-mail com um link — a vaga fica guardada
          por 24 horas.
        </p>
      </Card>
    );
  }

  return (
    <Card className="space-y-4">
      <div>
        <h3 className="text-title font-semibold text-strong">
          Entrar na lista de espera
        </h3>
        <p className="text-sm text-muted">
          {event.waitlist_waiting > 0
            ? `${event.waitlist_waiting} ${event.waitlist_waiting === 1 ? "inscrição aguarda" : "inscrições aguardam"} na fila. `
            : ""}
          Quando alguém cancelar, avisamos por ordem de chegada.
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <div
          aria-hidden
          className="absolute -left-[9999px] h-0 overflow-hidden"
        >
          <input type="text" name="website" tabIndex={-1} autoComplete="off" />
        </div>
        <Input
          label="Nome completo"
          name="name"
          required
          minLength={2}
          autoComplete="name"
        />
        <Input
          label="E-mail"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
        />
        <Input
          label="WhatsApp (opcional)"
          name="phone"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
        />
        <NumberField
          label="Quantas pessoas?"
          value={quantity}
          min={1}
          max={event.max_tickets_per_order}
          onChange={setQuantity}
        />
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1 size-5 shrink-0 accent-[rgb(var(--rgb-brand))]"
          />
          <span className="text-sm">
            Li e aceito os{" "}
            <Link
              href="/termos"
              target="_blank"
              className="font-semibold text-primary underline"
            >
              termos de uso
            </Link>{" "}
            e a{" "}
            <Link
              href="/privacidade"
              target="_blank"
              className="font-semibold text-primary underline"
            >
              política de privacidade
            </Link>
            .
          </span>
        </label>
        {error && (
          <p
            role="alert"
            className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
          >
            {error}
          </p>
        )}
        <Button type="submit" block loading={loading}>
          Entrar na lista de espera
        </Button>
      </form>
    </Card>
  );
}
