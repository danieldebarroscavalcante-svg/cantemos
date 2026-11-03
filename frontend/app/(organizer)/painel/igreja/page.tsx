"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LogoField } from "@/components/ui/logo-field";
import { api, ApiError, apiUpload } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Organization = {
  name: string;
  logo_url: string | null;
  can_edit: boolean;
};

export default function OrganizationPage() {
  const me = useMe();
  const [org, setOrg] = useState<Organization | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api<Organization>("/org/organization")
      .then((data) => {
        setOrg(data);
        setName(data.name);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [me]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const data = await api<Organization>("/org/organization", {
        method: "PUT",
        body: JSON.stringify({ name }),
      });
      setOrg(data);
      setName(data.name);
      setNotice("Nome salvo.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setSaving(false);
    }
  }

  if (!me || !org) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Igreja
        </h1>
        <p className="text-muted">
          Nome e logo de quem realiza os eventos. Aparecem como “Realização” nas
          páginas públicas, no e-mail do ingresso e nas páginas de Privacidade e
          Termos.
        </p>
      </div>

      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            label="Nome da igreja"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            maxLength={150}
            disabled={!org.can_edit}
          />
          {org.can_edit && (
            <Button type="submit" loading={saving}>
              Salvar nome
            </Button>
          )}
        </form>
      </Card>

      <Card>
        <LogoField
          label="Logo da igreja"
          hint="PNG com fundo transparente (ou SVG), pensado para fundo escuro, até 1 MB."
          url={org.logo_url}
          disabled={!org.can_edit}
          onUpload={async (file) =>
            setOrg(
              await apiUpload<Organization>("/org/organization/logo", file),
            )
          }
          onRemove={async () =>
            setOrg(
              await api<Organization>("/org/organization/logo", {
                method: "DELETE",
              }),
            )
          }
        />
      </Card>

      {notice && (
        <p
          role="status"
          className="rounded-xl bg-success/10 px-4 py-3 text-sm text-success"
        >
          {notice}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
        >
          {error}
        </p>
      )}
    </main>
  );
}
