"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Row = {
  code: string;
  buyer_name: string;
  attendee_name: string;
  age_group: "adulto" | "crianca" | "idoso";
  priority: boolean;
  accessibility_need: string | null;
  status: "valid" | "used" | "cancelled";
  checked_in_at: string | null;
};

const AGE = { adulto: "Adulto", crianca: "Criança", idoso: "Idoso" } as const;

export default function PrintListPage({
  params,
}: {
  params: { slug: string };
}) {
  const me = useMe();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState("");

  useEffect(() => {
    if (!me) return;
    api<Row[]>(`/org/events/${params.slug}/attendees`)
      .then((data) => {
        setRows(data);
        setGeneratedAt(new Date().toLocaleString("pt-BR"));
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [me, params.slug]);

  // Em ordem alfabética do participante: é assim que se procura na porta.
  const list = useMemo(
    () =>
      (rows ?? [])
        .filter((r) => r.status !== "cancelled")
        .sort((a, b) =>
          a.attendee_name.localeCompare(b.attendee_name, "pt-BR"),
        ),
    [rows],
  );

  if (!rows) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 print:max-w-none print:p-0">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link
          href={`/painel/eventos/${params.slug}/recepcao`}
          className="text-sm font-semibold text-primary"
        >
          ← Recepção
        </Link>
        <Button onClick={() => window.print()}>Imprimir</Button>
      </div>
      <h1 className="text-2xl font-bold">Lista de presença · CANTEMOS 2026</h1>
      <p className="mb-4 text-sm text-muted">
        {list.length} pessoas inscritas · gerada em {generatedAt} · em ordem
        alfabética
      </p>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b-2 border-fg text-left">
            <th className="w-8 py-2">✓</th>
            <th className="py-2">Participante</th>
            <th className="py-2">Faixa</th>
            <th className="py-2">Responsável</th>
            <th className="py-2">Inscrição</th>
          </tr>
        </thead>
        <tbody>
          {list.map((r, i) => (
            <tr
              key={`${r.code}-${i}`}
              className="break-inside-avoid border-b border-border"
            >
              <td className="py-2">
                <span className="inline-block size-4 border border-fg text-center leading-3">
                  {r.status === "used" ? "✓" : ""}
                </span>
              </td>
              <td className="py-2 font-medium">
                {r.attendee_name}
                {r.priority && (
                  <span className="ml-2 rounded bg-warning/30 px-1 text-xs font-semibold">
                    ♿{" "}
                    {r.accessibility_need &&
                    r.accessibility_need !== "Atendimento prioritário"
                      ? r.accessibility_need
                      : "Prioritário"}
                  </span>
                )}
              </td>
              <td className="py-2">{AGE[r.age_group]}</td>
              <td className="py-2">{r.buyer_name}</td>
              <td className="whitespace-nowrap py-2 tracking-wider">{r.code}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
