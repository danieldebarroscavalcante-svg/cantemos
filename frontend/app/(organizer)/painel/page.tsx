"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, logout, refreshSession, type Me } from "@/lib/api";

const roleLabel: Record<string, string> = {
  owner: "Responsável",
  admin: "Administrador",
  manager: "Produção",
  checkin: "Recepção",
};

export default function PainelPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const user = await api<Me>("/auth/me");
        if (active) setMe(user);
      } catch {
        // Recarregou a página: o access token (em memória) sumiu; tenta o cookie de refresh.
        if ((await refreshSession()) && active) setMe(await api<Me>("/auth/me"));
        else router.replace("/login");
      }
    })();
    return () => {
      active = false;
    };
  }, [router]);

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  if (!me) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted" aria-busy>
        Carregando…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">Painel</p>
          <h1 className="text-2xl font-bold">Olá, {me.name.split(" ")[0]}</h1>
        </div>
        <Button variant="secondary" onClick={onLogout}>
          Sair
        </Button>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {me.memberships.map((m) => (
          <Card key={m.organization_id}>
            <p className="text-sm text-muted">{roleLabel[m.role] ?? m.role}</p>
            <p className="text-lg font-semibold">{m.organization_name}</p>
          </Card>
        ))}
        <Card className="md:col-span-2">
          <p className="font-semibold">CANTEMOS 2026</p>
          <p className="text-muted">
            Inscrições, painel em tempo real e check-in chegam nas próximas entregas do Plano
            Express.
          </p>
        </Card>
      </div>
    </main>
  );
}
