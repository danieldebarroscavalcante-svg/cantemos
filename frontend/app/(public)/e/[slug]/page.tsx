import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Card } from "@/components/ui/card";
import { EventHeader } from "@/components/public/event-header";
import { RegistrationForm } from "@/components/public/registration-form";
import { ResendForm } from "@/components/public/resend-form";
import { formatEventDateTime } from "@/lib/format";
import { fetchPublicEvent } from "@/lib/server-api";

type Props = { params: { slug: string } };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const event = await fetchPublicEvent(params.slug);
  if (!event) return { title: "Evento" };
  const description = `${formatEventDateTime(event.starts_at)}${
    event.venue_name ? ` · ${event.venue_name}` : ""
  } · Entrada gratuita mediante inscrição.`;
  return {
    title: event.title,
    description,
    openGraph: { title: event.title, description, type: "website", locale: "pt_BR" },
  };
}

function StatusCard({ title, text }: { title: string; text: string }) {
  return (
    <Card className="space-y-1 border-accent/40 text-center">
      <p className="text-lg font-semibold">{title}</p>
      <p className="text-muted">{text}</p>
    </Card>
  );
}

export default async function EventPage({ params }: Props) {
  const event = await fetchPublicEvent(params.slug);
  if (!event) notFound();

  const open = event.status === "open";
  const soldOut = open && event.available <= 0;

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-4 py-6 md:py-10">
      <EventHeader event={event} />

      {event.description && (
        <p className="whitespace-pre-line leading-relaxed text-fg">{event.description}</p>
      )}

      <section aria-labelledby="inscricao" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="inscricao" className="text-2xl font-bold">
            Inscrição gratuita
          </h2>
          {open && !soldOut && event.available <= 30 && (
            <p className="rounded-full bg-warning/15 px-3 py-1 text-sm font-semibold">
              Últimas {event.available} vagas
            </p>
          )}
        </div>

        {event.status === "published" && (
          <StatusCard
            title="As inscrições abrem em breve"
            text="Volte a esta página na data de abertura. Os lugares são limitados."
          />
        )}
        {(event.status === "closed" || event.status === "finished") && (
          <StatusCard title="Inscrições encerradas" text="Obrigado pelo interesse!" />
        )}
        {soldOut && (
          <StatusCard
            title="Inscrições esgotadas"
            text="Todas as vagas foram preenchidas. Se alguém cancelar, a vaga volta a aparecer aqui."
          />
        )}
        {open && !soldOut && <RegistrationForm event={event} />}

        <ResendForm slug={event.slug} />
      </section>
    </main>
  );
}
