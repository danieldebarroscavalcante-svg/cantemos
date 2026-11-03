import Link from "next/link";
import { Card } from "@/components/ui/card";
import type { PublicEvent } from "@/lib/api";
import { formatEventDateTime } from "@/lib/format";
import { OrganizerFooter } from "@/components/public/organizer-footer";
import { fetchOrganization, fetchPublicEvent } from "@/lib/server-api";

const FEATURED_SLUG = "cantemos-2026";

async function featuredEvent(): Promise<PublicEvent | null> {
  try {
    return await fetchPublicEvent(FEATURED_SLUG);
  } catch {
    return null; // a página inicial nunca deve quebrar por instabilidade da API
  }
}

export default async function HomePage() {
  const [event, organization] = await Promise.all([
    featuredEvent(),
    fetchOrganization(),
  ]);
  const open = event?.status === "open" && event.available > 0;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col justify-center gap-8 px-4 py-12">
      <header className="space-y-3">
        <p className="eyebrow">EVENTMER</p>
        <h1 className="title-display">
          Inscrições, ingressos e credenciamento sem fila.
        </h1>
        <p className="text-lg text-muted">
          Plataforma de eventos da nossa igreja — pensada para o celular e o
          tablet.
        </p>
      </header>

      <Card className="space-y-3 overflow-hidden border-primary/35">
        {event?.banner_url && (
          // eslint-disable-next-line @next/next/no-img-element -- banner vem da API (em cache)
          <img
            src={event.banner_url}
            alt=""
            className="-mx-5 -mt-5 mb-2 aspect-[3/1] w-[calc(100%+2.5rem)] max-w-none object-cover sm:-mx-6 sm:-mt-6 sm:w-[calc(100%+3rem)]"
          />
        )}
        <p className="eyebrow">Próximo evento</p>
        {event?.logo_url ? (
          <h2>
            {/* eslint-disable-next-line @next/next/no-img-element -- logo vem da API (em cache) */}
            <img
              src={event.logo_url}
              alt={event.title}
              className="h-20 w-auto max-w-full object-contain sm:h-24"
            />
          </h2>
        ) : (
          <h2 className="text-[1.75rem] font-normal leading-tight text-strong">
            {event?.title ?? "CANTEMOS 2026"}
          </h2>
        )}
        <p className="text-muted">
          {event
            ? `${formatEventDateTime(event.starts_at)} · Entrada gratuita`
            : "Quinta-feira, 19 de novembro · Entrada gratuita"}
        </p>
        {event ? (
          <Link
            href={`/e/${event.slug}`}
            className="inline-flex min-h-touch shrink-0 whitespace-nowrap w-full items-center justify-center rounded-xl bg-brand px-5 font-bold uppercase tracking-wide text-primary-fg shadow-sm transition hover:-translate-y-px hover:shadow-cta sm:w-auto"
          >
            {open ? "Fazer minha inscrição" : "Ver detalhes do evento"}
          </Link>
        ) : (
          <p className="text-sm text-muted">
            As inscrições serão abertas em breve.
          </p>
        )}
      </Card>

      <p className="text-sm text-muted">
        É da equipe?{" "}
        <Link
          href="/login"
          className="font-semibold text-primary underline-offset-4 hover:underline"
        >
          Entrar no painel
        </Link>
      </p>

      <OrganizerFooter
        name={organization?.name ?? event?.organization_name}
        logoUrl={organization?.logo_url ?? event?.organization_logo_url}
      />
    </main>
  );
}
