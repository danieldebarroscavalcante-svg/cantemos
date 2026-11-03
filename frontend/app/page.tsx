import Link from "next/link";
import { Card } from "@/components/ui/card";
import type { PublicEvent } from "@/lib/api";
import { formatEventDateTime } from "@/lib/format";
import { fetchPublicEvent } from "@/lib/server-api";

const FEATURED_SLUG = "cantemos-2026";

async function featuredEvent(): Promise<PublicEvent | null> {
  try {
    return await fetchPublicEvent(FEATURED_SLUG);
  } catch {
    return null; // a página inicial nunca deve quebrar por instabilidade da API
  }
}

export default async function HomePage() {
  const event = await featuredEvent();
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

      <Card className="space-y-3 border-primary/35">
        <p className="eyebrow">Próximo evento</p>
        <h2 className="text-[1.75rem] font-normal leading-tight text-strong">
          {event?.title ?? "CANTEMOS 2026"}
        </h2>
        <p className="text-muted">
          {event
            ? `${formatEventDateTime(event.starts_at)} · Entrada gratuita`
            : "Quinta-feira, 19 de novembro · Entrada gratuita"}
        </p>
        {event ? (
          <Link
            href={`/e/${event.slug}`}
            className="inline-flex min-h-touch w-full items-center justify-center rounded-xl bg-brand px-5 font-bold uppercase tracking-wide text-primary-fg shadow-sm transition hover:-translate-y-px hover:shadow-cta sm:w-auto"
          >
            {open ? "Fazer minha inscrição" : "Ver detalhes do evento"}
          </Link>
        ) : (
          <p className="text-sm text-muted">
            As inscrições serão abertas em breve.
          </p>
        )}
      </Card>

      <footer className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted">
        <span>
          É da equipe?{" "}
          <Link
            href="/login"
            className="font-semibold text-primary underline-offset-4 hover:underline"
          >
            Entrar no painel
          </Link>
        </span>
        <Link href="/privacidade" className="hover:underline">
          Privacidade
        </Link>
        <Link href="/termos" className="hover:underline">
          Termos de uso
        </Link>
      </footer>
    </main>
  );
}
