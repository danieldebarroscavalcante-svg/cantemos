"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  api,
  ApiError,
  type AgeGroup,
  type Order,
  type PublicEvent,
} from "@/lib/api";
import { cn } from "@/lib/cn";

type Attendee = {
  key: number;
  self: boolean;
  name: string;
  age_group: AgeGroup;
  priority: boolean;
  accessibility_need: string;
};

const AGE_OPTIONS: Array<{ value: AgeGroup; label: string }> = [
  { value: "adulto", label: "Adulto" },
  { value: "crianca", label: "Criança" },
  { value: "idoso", label: "Idoso" },
];

let nextKey = 1;
const blank = (self = false): Attendee => ({
  key: nextKey++,
  self,
  name: "",
  age_group: "adulto",
  priority: false,
  accessibility_need: "",
});

function AgePicker({
  value,
  onChange,
}: {
  value: AgeGroup;
  onChange: (v: AgeGroup) => void;
}) {
  const name = useId();
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium">Faixa etária</legend>
      <div className="grid grid-cols-3 gap-2">
        {AGE_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={cn(
              "grid min-h-touch cursor-pointer place-items-center rounded-xl border text-sm font-semibold",
              value === option.value
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-surface text-fg",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function RegistrationForm({
  event,
  waitlistToken,
}: {
  event: PublicEvent;
  waitlistToken?: string;
}) {
  const router = useRouter();
  const [buyer, setBuyer] = useState({ name: "", email: "", phone: "" });
  const [attendees, setAttendees] = useState<Attendee[]>(() => [blank(true)]);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const maxPeople = Math.max(
    0,
    Math.min(event.max_tickets_per_order, event.available),
  );
  const includesSelf = attendees.some((a) => a.self);

  function updateAttendee(key: number, changes: Partial<Attendee>) {
    setAttendees((list) =>
      list.map((a) => (a.key === key ? { ...a, ...changes } : a)),
    );
  }

  function toggleSelf(checked: boolean) {
    setAttendees((list) =>
      checked
        ? [blank(true), ...list]
        : list.filter((a) => !a.self).length
          ? list.filter((a) => !a.self)
          : [blank()],
    );
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    if (!consent) {
      setError(
        "Para continuar, aceite os termos de uso e a política de privacidade.",
      );
      return;
    }
    setLoading(true);
    const website = String(new FormData(e.currentTarget).get("website") ?? "");
    const source = new URLSearchParams(window.location.search).get("origem");
    try {
      const order = await api<Order>(`/public/events/${event.slug}/orders`, {
        method: "POST",
        body: JSON.stringify({
          buyer_name: buyer.name,
          buyer_email: buyer.email,
          buyer_phone: buyer.phone || null,
          consent,
          source,
          website,
          waitlist_token: waitlistToken ?? null,
          attendees: attendees.map((a) => ({
            name: a.self ? buyer.name : a.name,
            age_group: a.age_group,
            priority: a.priority,
            accessibility_need: a.priority
              ? a.accessibility_need || null
              : null,
          })),
        }),
      });
      router.push(`/ingresso/${order.token}?novo=1`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 422 && !err.message.includes(" ")
            ? "Confira os dados preenchidos."
            : err.message
          : "Sem conexão. Verifique a internet e tente de novo.",
      );
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate={false}>
      {/* Campo invisível contra robôs */}
      <div aria-hidden className="absolute -left-[9999px] h-0 overflow-hidden">
        <label>
          Não preencha
          <input type="text" name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Seus dados</h2>
        <Input
          label="Nome completo"
          autoComplete="name"
          required
          minLength={2}
          value={buyer.name}
          onChange={(e) => setBuyer({ ...buyer, name: e.target.value })}
        />
        <Input
          label="E-mail"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          hint="Os ingressos com QR Code chegam neste e-mail."
          value={buyer.email}
          onChange={(e) => setBuyer({ ...buyer, email: e.target.value })}
        />
        <Input
          label="WhatsApp (opcional)"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="(11) 99999-9999"
          value={buyer.phone}
          onChange={(e) => setBuyer({ ...buyer, phone: e.target.value })}
        />
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">Quem vai?</h2>
          <p className="text-sm text-muted">
            {attendees.length} de até {maxPeople}{" "}
            {maxPeople === 1 ? "pessoa" : "pessoas"}
          </p>
        </div>

        <label className="flex min-h-touch cursor-pointer items-center gap-3 rounded-xl bg-bg px-4">
          <input
            type="checkbox"
            checked={includesSelf}
            onChange={(e) => toggleSelf(e.target.checked)}
            className="size-5 accent-[rgb(var(--color-primary))]"
          />
          <span className="font-medium">Eu também vou</span>
        </label>

        <ol className="space-y-4">
          {attendees.map((attendee, index) => (
            <li
              key={attendee.key}
              className="space-y-3 rounded-2xl border border-border p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-muted">
                  Pessoa {index + 1}
                </p>
                {attendees.length > 1 && (
                  <button
                    type="button"
                    className="min-h-touch px-2 text-sm font-semibold text-danger"
                    onClick={() =>
                      setAttendees((list) =>
                        list.filter((a) => a.key !== attendee.key),
                      )
                    }
                  >
                    Remover
                  </button>
                )}
              </div>
              {attendee.self ? (
                <p className="rounded-xl bg-bg px-4 py-3 font-medium">
                  {buyer.name.trim() || "Você"}{" "}
                  <span className="text-muted">(você)</span>
                </p>
              ) : (
                <Input
                  label="Nome"
                  required
                  minLength={2}
                  autoComplete="off"
                  value={attendee.name}
                  onChange={(e) =>
                    updateAttendee(attendee.key, { name: e.target.value })
                  }
                />
              )}
              <AgePicker
                value={attendee.age_group}
                onChange={(age_group) =>
                  updateAttendee(attendee.key, { age_group })
                }
              />
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={attendee.priority}
                  onChange={(e) =>
                    updateAttendee(attendee.key, { priority: e.target.checked })
                  }
                  className="mt-1 size-5 shrink-0 accent-[rgb(var(--color-primary))]"
                />
                <span>
                  <span className="font-medium">
                    Precisa de atendimento prioritário
                  </span>
                  <span className="block text-sm text-muted">
                    Pessoa com deficiência, idoso, gestante ou mobilidade
                    reduzida.
                  </span>
                </span>
              </label>
              {attendee.priority && (
                <Input
                  label="Como podemos ajudar? (opcional)"
                  placeholder="Ex.: cadeirante, precisa de acompanhante"
                  maxLength={200}
                  value={attendee.accessibility_need}
                  onChange={(e) =>
                    updateAttendee(attendee.key, {
                      accessibility_need: e.target.value,
                    })
                  }
                />
              )}
            </li>
          ))}
        </ol>

        {attendees.length < maxPeople ? (
          <Button
            type="button"
            variant="secondary"
            block
            onClick={() => setAttendees((list) => [...list, blank()])}
          >
            + Adicionar pessoa
          </Button>
        ) : (
          <p className="text-sm text-muted">
            Limite de {maxPeople} {maxPeople === 1 ? "pessoa" : "pessoas"} por
            inscrição.
          </p>
        )}
      </Card>

      <Card className="space-y-4">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1 size-5 shrink-0 accent-[rgb(var(--color-primary))]"
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
          Confirmar inscrição
        </Button>
      </Card>
    </form>
  );
}
