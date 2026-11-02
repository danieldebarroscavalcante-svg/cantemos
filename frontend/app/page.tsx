import Link from "next/link";
import { Card } from "@/components/ui/card";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col justify-center gap-8 px-4 py-12">
      <header className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-widest text-primary">EVENTMER</p>
        <h1 className="text-3xl font-bold leading-tight sm:text-4xl">
          Inscrições, ingressos e credenciamento sem fila.
        </h1>
        <p className="text-lg text-muted">
          Plataforma de eventos da nossa igreja — pensada para o celular e o tablet.
        </p>
      </header>

      <Card className="space-y-2 border-accent/40">
        <p className="text-sm font-semibold text-accent">Próximo evento</p>
        <h2 className="text-2xl font-bold">CANTEMOS 2026</h2>
        <p className="text-muted">Quinta-feira, 19 de novembro · Entrada gratuita · 120 lugares</p>
        <p className="text-sm text-muted">As inscrições serão abertas em breve.</p>
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
