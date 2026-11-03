"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError, setAccessToken } from "@/lib/api";

export default function InvitePage({ params }: { params: { token: string } }) {
  const router = useRouter();
  const [info, setInfo] = useState<{ name: string; email: string } | null>(
    null,
  );
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [invalid, setInvalid] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<{ name: string; email: string }>(`/auth/invite/${params.token}`)
      .then((data) => {
        setInfo(data);
        setName(data.name);
      })
      .catch((err) =>
        setInvalid(
          err instanceof ApiError
            ? err.message
            : "Sem conexão. Tente novamente.",
        ),
      );
  }, [params.token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("A confirmação não é igual à senha.");
      return;
    }
    setLoading(true);
    try {
      const { access_token } = await api<{ access_token: string }>(
        `/auth/invite/${params.token}`,
        { method: "POST", body: JSON.stringify({ name, password }) },
      );
      setAccessToken(access_token);
      router.replace("/painel");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.",
      );
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-12">
      <p className="eyebrow">EVENTMER</p>
      <h1 className="mb-1 text-3xl font-normal leading-tight text-strong">
        Criar sua senha
      </h1>
      {invalid ? (
        <Card className="mt-4 space-y-3">
          <p className="text-fg">{invalid}</p>
          <a href="/login" className="font-semibold text-primary underline">
            Ir para o login
          </a>
        </Card>
      ) : !info ? (
        <p className="text-muted">Verificando o convite…</p>
      ) : (
        <>
          <p className="mb-6 text-muted">
            Você foi convidado(a) para a equipe. Seu login será{" "}
            <strong className="text-fg">{info.email}</strong>.
          </p>
          <Card>
            <form onSubmit={onSubmit} className="space-y-4">
              <Input
                label="Seu nome"
                required
                minLength={2}
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Input
                label="Senha"
                type="password"
                hint="Mínimo de 8 caracteres."
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Input
                label="Confirmar senha"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
              {error && (
                <p
                  role="alert"
                  className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
                >
                  {error}
                </p>
              )}
              <Button type="submit" block loading={loading}>
                Criar senha e entrar
              </Button>
            </form>
          </Card>
        </>
      )}
    </main>
  );
}
