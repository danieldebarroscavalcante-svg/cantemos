"use client";

/* eslint-disable @next/next/no-img-element -- imagens vêm da API (em cache) */
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LogoField } from "@/components/ui/logo-field";
import { api, ApiError, apiUpload } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Identity = {
  title: string;
  subtitle: string | null;
  logo_url: string | null;
  banner_url: string | null;
};

export default function IdentityPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const base = `/org/events/${params.slug}`;
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canEdit =
    me?.memberships.some((m) => m.role === "owner" || m.role === "admin") ??
    false;

  useEffect(() => {
    if (!me) return;
    api<Identity>(`${base}/identity`)
      .then((data) => {
        setIdentity(data);
        setTitle(data.title);
        setSubtitle(data.subtitle ?? "");
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [me, base]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const data = await api<Identity>(`${base}/identity`, {
        method: "PUT",
        body: JSON.stringify({ title, subtitle: subtitle || null }),
      });
      setIdentity(data);
      setNotice("Nome e tema salvos.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setSaving(false);
    }
  }

  if (!me || !identity) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Identidade visual
        </h1>
        <p className="text-muted">
          Como o evento aparece na página pública, nos ingressos, na recepção e
          nos e-mails.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <Card>
            <form onSubmit={onSubmit} className="space-y-4">
              <h2 className="text-title font-semibold text-strong">
                Nome e tema
              </h2>
              <Input
                label="Nome do evento"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                minLength={2}
                maxLength={150}
                disabled={!canEdit}
              />
              <Input
                label="Tema"
                placeholder="Ex.: Uma história contada em música"
                hint="Aparece abaixo do nome, na página do evento e nos e-mails ({tema})."
                value={subtitle}
                onChange={(e) => setSubtitle(e.target.value)}
                maxLength={255}
                disabled={!canEdit}
              />
              {canEdit && (
                <Button type="submit" loading={saving}>
                  Salvar nome e tema
                </Button>
              )}
            </form>
          </Card>

          <Card>
            <LogoField
              wide
              label="Banner do evento"
              hint="Imagem larga no topo da página do evento e no destaque da página inicial. Use 1500 × 500 px (proporção 3:1), JPG ou PNG, até 2 MB. Evite texto nas bordas: no celular as laterais podem ser cortadas."
              url={identity.banner_url}
              disabled={!canEdit}
              onUpload={async (file) =>
                setIdentity(await apiUpload<Identity>(`${base}/banner`, file))
              }
              onRemove={async () =>
                setIdentity(
                  await api<Identity>(`${base}/banner`, { method: "DELETE" }),
                )
              }
            />
          </Card>

          <Card>
            <LogoField
              label="Logo do evento"
              hint="Aparece no lugar do nome na página do evento, nos ingressos, na recepção e no topo dos e-mails. PNG com fundo transparente (ou SVG) para fundo escuro, até 1 MB. Para aparecer no e-mail, use PNG ou JPG."
              url={identity.logo_url}
              disabled={!canEdit}
              onUpload={async (file) => {
                const { logo_url } = await apiUpload<{ logo_url: string }>(
                  `${base}/logo`,
                  file,
                );
                setIdentity((i) => (i ? { ...i, logo_url } : i));
              }}
              onRemove={async () => {
                await api(`${base}/logo`, { method: "DELETE" });
                setIdentity((i) => (i ? { ...i, logo_url: null } : i));
              }}
            />
          </Card>
        </div>

        <aside className="space-y-3 lg:sticky lg:top-6 lg:self-start">
          <p className="eyebrow">Prévia da página do evento</p>
          <div className="overflow-hidden rounded-2xl border border-border-subtle bg-bg shadow-card">
            {identity.banner_url && (
              <img
                src={identity.banner_url}
                alt=""
                className="aspect-[3/1] w-full object-cover"
              />
            )}
            <div className="space-y-1 p-5">
              {identity.logo_url ? (
                <img
                  src={identity.logo_url}
                  alt={title}
                  className="h-16 w-auto max-w-full object-contain"
                />
              ) : (
                <p className="text-3xl font-normal leading-tight text-strong">
                  {title}
                </p>
              )}
              {subtitle && <p className="text-muted">{subtitle}</p>}
            </div>
          </div>
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
        </aside>
      </div>
    </main>
  );
}
