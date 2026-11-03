"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, refreshSession, type Me } from "@/lib/api";

/** Carrega o usuário logado; se a sessão não puder ser renovada, manda para o login. */
export function useMe(): Me | null {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const user = await api<Me>("/auth/me");
        if (active) setMe(user);
      } catch {
        // Página recarregada: o access token (em memória) sumiu; tenta o cookie de refresh.
        if ((await refreshSession()) && active)
          setMe(await api<Me>("/auth/me"));
        else router.replace("/login");
      }
    })();
    return () => {
      active = false;
    };
  }, [router]);

  return me;
}
