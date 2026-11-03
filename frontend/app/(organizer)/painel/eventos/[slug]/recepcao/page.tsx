"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { QrCode } from "@/components/qr-code";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, apiDownload, ApiError } from "@/lib/api";
import { useEventAccess } from "@/lib/use-event-access";
import { useMe } from "@/lib/use-me";

type Reception = { code: string | null; checkin_path: string };

export default function ReceptionPage({
  params,
}: {
  params: { slug: string };
}) {
  const me = useMe();
  const [info, setInfo] = useState<Reception | null>(null);
  const [origin, setOrigin] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const access = useEventAccess(params.slug, !!me);
  const canEdit = access?.permissions.edit_event ?? false;

  useEffect(() => setOrigin(window.location.origin), []);
  useEffect(() => {
    if (!me) return;
    api<Reception>(`/org/events/${params.slug}/reception`)
      .then(setInfo)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [me, params.slug]);

  const url = info ? `${origin}${info.checkin_path}` : "";
  const message = info?.code
    ? `Recepção do CANTEMOS 2026\n1) Abra: ${url}\n2) Código da recepção: ${info.code}\n3) Digite seu nome e permita o uso da câmera.`
    : "";

  async function regenerate() {
    if (
      info?.code &&
      !window.confirm(
        "Gerar um novo código? Quem entrou com o código atual precisará entrar de novo.",
      )
    )
      return;
    setBusy(true);
    try {
      setInfo(
        await api<Reception>(`/org/events/${params.slug}/reception/code`, {
          method: "POST",
        }),
      );
      setNotice("Novo código gerado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(false);
    }
  }

  async function copyMessage() {
    await navigator.clipboard.writeText(message);
    setNotice("Mensagem copiada — cole no grupo de WhatsApp da equipe.");
  }

  async function exportCsv() {
    setError(null);
    try {
      await apiDownload(
        `/org/events/${params.slug}/attendees.csv`,
        `inscritos-${params.slug}.csv`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    }
  }

  if (!me || !info) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Recepção e credenciamento
        </h1>
        <p className="text-muted">
          Os voluntários entram com o código abaixo — sem criar conta. Eles veem
          só nome, faixa etária e prioridade, nunca e-mail ou telefone.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="space-y-4 text-center">
          <p className="text-sm font-semibold text-muted">Código da recepção</p>
          {info.code ? (
            <p className="select-all text-5xl font-black tracking-[0.25em]">
              {info.code}
            </p>
          ) : (
            <p className="text-muted">Nenhum código gerado ainda.</p>
          )}
          {canEdit && (
            <Button
              variant={info.code ? "secondary" : "primary"}
              loading={busy}
              onClick={regenerate}
            >
              {info.code ? "Gerar novo código" : "Gerar código"}
            </Button>
          )}
          {info.code && (
            <>
              <Button variant="secondary" block onClick={copyMessage}>
                Copiar instruções para o WhatsApp
              </Button>
              <p className="text-sm text-muted">
                Troque o código se ele vazar: quem usa o antigo sai na hora.
              </p>
            </>
          )}
        </Card>

        <Card className="space-y-3 text-center">
          <p className="text-sm font-semibold text-muted">
            Voluntários: apontem a câmera aqui
          </p>
          {url && (
            <QrCode
              value={url}
              label="QR Code para abrir a recepção"
              size={200}
            />
          )}
          <p className="break-all text-sm text-muted">{url}</p>
          <Link
            href={info.checkin_path}
            className="inline-flex min-h-touch shrink-0 whitespace-nowrap w-full items-center justify-center rounded-xl bg-brand px-5 font-bold uppercase tracking-wide text-primary-fg shadow-sm transition hover:-translate-y-px hover:shadow-cta"
          >
            Abrir a recepção neste aparelho
          </Link>
        </Card>
      </div>

      <Card className="space-y-3">
        <h2 className="text-title font-semibold text-strong">
          Plano B (sem internet)
        </h2>
        <p className="text-muted">
          Imprima a lista de presença na véspera e tenha uma cópia na porta.
          Exporte a planilha para conferências e para a secretaria.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          <Link
            href={`/painel/eventos/${params.slug}/lista`}
            className="inline-flex min-h-touch shrink-0 whitespace-nowrap items-center justify-center rounded-xl border border-border bg-line/[0.03] px-5 text-sm font-semibold hover:bg-line/[0.07]"
          >
            Lista de presença (imprimir)
          </Link>
          <Button variant="secondary" onClick={exportCsv}>
            Exportar planilha (CSV)
          </Button>
        </div>
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
