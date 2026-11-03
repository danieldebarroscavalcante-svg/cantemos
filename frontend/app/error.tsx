"use client";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold">Não conseguimos carregar esta página</h1>
      <p className="text-muted">
        Pode ser uma instabilidade momentânea. Aguarde alguns segundos e tente de novo.
      </p>
      <Button onClick={reset}>Tentar de novo</Button>
    </main>
  );
}
