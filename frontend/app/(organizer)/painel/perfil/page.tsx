"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError, setAccessToken, type Me } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const ROLE: Record<string, string> = {
  owner: "Responsável",
  admin: "Administrador",
  manager: "Produção",
  checkin: "Recepção",
};

function Feedback({ ok, text }: { ok: boolean; text: string }) {
  return (
    <p
      role={ok ? "status" : "alert"}
      className={`rounded-xl px-4 py-3 text-sm ${ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}
    >
      {text}
    </p>
  );
}

export default function ProfilePage() {
  const me = useMe();
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameMsg, setNameMsg] = useState<{ ok: boolean; text: string } | null>(
    null,
  );
  const [passwords, setPasswords] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [savingPass, setSavingPass] = useState(false);
  const [passMsg, setPassMsg] = useState<{ ok: boolean; text: string } | null>(
    null,
  );

  useEffect(() => {
    if (me) setName(me.name);
  }, [me]);

  async function saveName(e: FormEvent) {
    e.preventDefault();
    setSavingName(true);
    setNameMsg(null);
    try {
      const updated = await api<Me>("/auth/me", {
        method: "PUT",
        body: JSON.stringify({ name }),
      });
      setName(updated.name);
      setNameMsg({ ok: true, text: "Nome salvo." });
    } catch (err) {
      setNameMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : "Sem conexão.",
      });
    } finally {
      setSavingName(false);
    }
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    setPassMsg(null);
    if (passwords.next !== passwords.confirm) {
      setPassMsg({
        ok: false,
        text: "A confirmação não é igual à nova senha.",
      });
      return;
    }
    setSavingPass(true);
    try {
      await api("/auth/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwords.current,
          new_password: passwords.next,
        }),
      });
      // O servidor renovou a sessão deste aparelho; o próximo pedido pega um token novo.
      setAccessToken(null);
      setPasswords({ current: "", next: "", confirm: "" });
      setPassMsg({
        ok: true,
        text: "Senha alterada. Os outros aparelhos conectados precisarão entrar de novo.",
      });
    } catch (err) {
      setPassMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : "Sem conexão.",
      });
    } finally {
      setSavingPass(false);
    }
  }

  if (!me) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted">
        Carregando…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Meu perfil
        </h1>
        <p className="text-muted">
          {me.memberships
            .map((m) => `${ROLE[m.role] ?? m.role} · ${m.organization_name}`)
            .join(" · ")}
        </p>
      </div>

      <Card>
        <form onSubmit={saveName} className="space-y-4">
          <h2 className="text-title font-semibold text-strong">Dados</h2>
          <Input
            label="Nome"
            hint="Aparece no painel e no registro de quem fez cada check-in."
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            maxLength={150}
            autoComplete="name"
          />
          <Input
            label="E-mail (login)"
            value={me.email}
            readOnly
            disabled
            hint="Para trocar o e-mail de acesso, fale com o responsável pelo sistema."
          />
          <Button
            type="submit"
            loading={savingName}
            disabled={name.trim() === me.name}
          >
            Salvar nome
          </Button>
          {nameMsg && <Feedback {...nameMsg} />}
        </form>
      </Card>

      <Card>
        <form onSubmit={savePassword} className="space-y-4">
          <h2 className="text-title font-semibold text-strong">Trocar senha</h2>
          <Input
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            required
            value={passwords.current}
            onChange={(e) =>
              setPasswords({ ...passwords, current: e.target.value })
            }
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            hint="Mínimo de 8 caracteres."
            required
            minLength={8}
            value={passwords.next}
            onChange={(e) =>
              setPasswords({ ...passwords, next: e.target.value })
            }
          />
          <Input
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={passwords.confirm}
            onChange={(e) =>
              setPasswords({ ...passwords, confirm: e.target.value })
            }
          />
          <Button type="submit" variant="secondary" loading={savingPass}>
            Trocar senha
          </Button>
          {passMsg && <Feedback {...passMsg} />}
        </form>
      </Card>
    </main>
  );
}
