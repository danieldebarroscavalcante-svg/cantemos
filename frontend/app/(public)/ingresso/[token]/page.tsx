"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { EventHeader } from "@/components/public/event-header";
import { OrganizerFooter } from "@/components/public/organizer-footer";
import { QrCode } from "@/components/qr-code";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError, type Order, type Ticket } from "@/lib/api";

const AGE_LABEL = {
  adulto: "Adulto",
  crianca: "Criança",
  idoso: "Idoso",
} as const;
const STATUS_LABEL: Record<Ticket["status"], string> = {
  valid: "Válido",
  used: "Entrada registrada",
  cancelled: "Cancelado",
  transferred: "Transferido",
};

function TicketCard({
  ticket,
  index,
  total,
  onCancel,
  busy,
}: {
  ticket: Ticket;
  index: number;
  total: number;
  onCancel: () => void;
  busy: boolean;
}) {
  const valid = ticket.status === "valid" && ticket.qr;
  return (
    <Card
      className={
        valid ? "space-y-3 text-center" : "space-y-1 text-center opacity-70"
      }
    >
      <p className="text-sm text-muted">
        Ingresso {index + 1} de {total}
      </p>
      {valid ? (
        <QrCode
          value={ticket.qr!}
          label={`QR Code do ingresso de ${ticket.attendee_name}`}
        />
      ) : (
        <p className="py-6 font-semibold text-muted">
          {STATUS_LABEL[ticket.status]}
        </p>
      )}
      <p className="text-xl font-bold">{ticket.attendee_name}</p>
      <p className="text-muted">{AGE_LABEL[ticket.age_group]}</p>
      {ticket.priority && (
        <p className="mx-auto w-fit rounded-full bg-line/[0.08] px-3 py-1 text-sm font-semibold">
          Atendimento prioritário
          {ticket.accessibility_need &&
          ticket.accessibility_need !== "Atendimento prioritário"
            ? ` · ${ticket.accessibility_need}`
            : ""}
        </p>
      )}
      {valid && total > 1 && (
        <Button
          variant="ghost-danger"
          onClick={onCancel}
          disabled={busy}
          className="text-sm"
        >
          Esta pessoa não vai
        </Button>
      )}
    </Card>
  );
}

function OrderView({ token }: { token: string }) {
  const isNew = useSearchParams().get("novo") === "1";
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Order>(`/public/orders/${token}`)
      .then(setOrder)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Sem conexão. Tente novamente.",
        ),
      );
  }, [token]);

  useEffect(load, [load]);

  async function cancel(ticketIds: string[], question: string) {
    if (!window.confirm(question)) return;
    setBusy(true);
    try {
      setOrder(
        await api<Order>(`/public/orders/${token}/cancel`, {
          method: "POST",
          body: JSON.stringify({ ticket_ids: ticketIds }),
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!order) {
    return (
      <main
        className="grid min-h-dvh place-items-center px-4 text-center text-muted"
        aria-busy
      >
        {error ?? "Carregando seus ingressos…"}
      </main>
    );
  }

  const valid = order.tickets.filter((t) => t.status === "valid");
  const cancelled = order.status === "cancelled";

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-4 py-6 md:py-10">
      {isNew && !cancelled && (
        <div
          role="status"
          className="rounded-2xl bg-success/10 p-4 text-success"
        >
          <p className="text-lg font-bold">Inscrição confirmada! 🎉</p>
          <p>
            {order.email_sent
              ? `Enviamos os ingressos para ${order.buyer_email}. Se não encontrar, olhe no spam.`
              : "Não conseguimos enviar o e-mail agora. Salve esta página nos favoritos ou tire um print dos QR Codes."}
          </p>
        </div>
      )}

      <EventHeader event={order.event} compact />

      <Card className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm text-muted">Inscrição</p>
          <p className="text-lg font-bold tracking-wider">{order.code}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted">Responsável</p>
          <p className="font-semibold">{order.buyer_name}</p>
        </div>
      </Card>

      {cancelled ? (
        <Card className="space-y-2 text-center">
          <p className="text-title font-semibold text-strong">
            Inscrição cancelada
          </p>
          <p className="text-muted">
            Obrigado por liberar as vagas para outras famílias.
          </p>
          <Link
            href={`/e/${order.event.slug}`}
            className="font-semibold text-primary underline"
          >
            Fazer nova inscrição
          </Link>
        </Card>
      ) : (
        <>
          <p className="text-center text-muted">
            Na entrada, mostre o QR Code de cada pessoa. Aumente o brilho da
            tela para facilitar a leitura.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {order.tickets.map((ticket, index) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                index={index}
                total={order.tickets.length}
                busy={busy}
                onCancel={() =>
                  cancel(
                    [ticket.id],
                    `Cancelar o ingresso de ${ticket.attendee_name}?`,
                  )
                }
              />
            ))}
          </div>
          {error && (
            <p
              role="alert"
              className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
            >
              {error}
            </p>
          )}
          {valid.length > 0 && (
            <Card className="space-y-3 text-center">
              <p className="text-muted">
                Não vai poder ir? Cancele para liberar a vaga para outra
                família.
              </p>
              <Button
                variant="ghost-danger"
                loading={busy}
                onClick={() =>
                  cancel(
                    [],
                    "Cancelar a inscrição inteira? Todos os ingressos deixarão de valer.",
                  )
                }
              >
                Cancelar minha inscrição
              </Button>
            </Card>
          )}
        </>
      )}

      <OrganizerFooter
        name={order.event.organization_name}
        logoUrl={order.event.organization_logo_url}
      />
    </main>
  );
}

export default function TicketPage({ params }: { params: { token: string } }) {
  return (
    <Suspense>
      <OrderView token={params.token} />
    </Suspense>
  );
}
