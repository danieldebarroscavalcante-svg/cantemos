"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    setLoading(true);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      router.replace("/painel");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.");
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-12">
      <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-primary">EVENTMER</p>
      <h1 className="mb-6 text-2xl font-bold">Entrar no painel</h1>
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          <Input
            label="E-mail"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            required
          />
          <Input
            label="Senha"
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
          {error && (
            <p role="alert" className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" block loading={loading}>
            Entrar
          </Button>
        </form>
      </Card>
    </main>
  );
}
