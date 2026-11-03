"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useMe } from "@/lib/use-me";

type TestOrder = {
  code: string;
  token: string;
  email: string;
  people: number;
  valid: number;
  present: number;
  cancelled: number;
  email_sent: boolean;
};

type Step = { id: string; title: string; detail: string; link?: (o: TestOrder) => string };

const STEPS: Step[] = [
  {
    id: "email",
    title: "Receber o e-mail do ingresso",
    detail:
      "Abra o e-mail “Seu ingresso · …” (olhe também o spam). Confira logo, data, local, o bloco do responsável e os 3 QR Codes.",
  },
  {
    id: "tickets",
    title: "Abrir a página dos ingressos",
    detail: "Pelo botão do e-mail ou aqui. Os QR Codes devem aparecer grandes e legíveis.",
    link: (o) => `/ingresso/${o.token}`,
  },
  {
    id: "scan",
    title: "Ler o QR Code na recepção (outro aparelho)",
    detail:
      "Abra a recepção em outro celular ou tablet, entre com o código da recepção e aponte a câmera para o 1º QR Code. Deve aparecer a tela verde “ENTRADA LIBERADA”.",
    link: () => "recepcao",
  },
  {
    id: "again",
    title: "Ler o mesmo QR de novo",
    detail: "Deve aparecer a tela amarela “JÁ ENTROU ÀS … POR …”.",
  },
  {
    id: "family",
    title: "Registrar a família e ver a prioridade",
    detail:
      "Use “Registrar entrada de mais 2” ou a aba “Buscar nome” (digite TESTE). A idosa aparece com o selo ♿ Prioritário · Cadeirante.",
  },
  {
    id: "undo",
    title: "Desfazer uma entrada",
    detail: "Na busca por nome, toque em “Desfazer” em uma das pessoas.",
  },
  {
    id: "cancel",
    title: "Cancelar uma pessoa",
    detail:
      "Na página dos ingressos, toque em “Esta pessoa não vai” em quem ainda não entrou. Na recepção, o QR dela passa a dar tela vermelha.",
    link: (o) => `/ingresso/${o.token}`,
  },
  {
    id: "numbers",
    title: "Conferir números e lista impressa",
    detail:
      "Em Números e lembretes, os totais devem refletir o teste. Na Recepção, abra a Lista de presença e a planilha.",
    link: () => "acompanhamento",
  },
  {
    id: "messages",
    title: "Testar as outras mensagens",
    detail:
      "Em Mensagens de e-mail, use “Enviar teste para mim” nos lembretes e na lista de espera.",
    link: () => "mensagens",
  },
];

const storageKey = (slug: string) => `eventmer:teste-geral:${slug}`;

export default function GeneralTestPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const base = `/org/events/${params.slug}`;
  const [orders, setOrders] = useState<TestOrder[] | null>(null);
  const [done, setDone] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState<"create" | "delete" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<TestOrder[]>(`${base}/test-registrations`)
      .then(setOrders)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Sem conexão."));
  }, [base]);

  useEffect(() => {
    if (!me) return;
    load();
    const timer = setInterval(load, 5000); // acompanha as entradas feitas em outro aparelho
    return () => clearInterval(timer);
  }, [me, load]);

  useEffect(() => {
    try {
      setDone(JSON.parse(localStorage.getItem(storageKey(params.slug)) ?? "{}"));
    } catch {
      /* navegação privada */
    }
  }, [params.slug]);

  function toggle(id: string) {
    setDone((d) => {
      const next = { ...d, [id]: !d[id] };
      try {
        localStorage.setItem(storageKey(params.slug), JSON.stringify(next));
      } catch {
        /* navegação privada */
      }
      return next;
    });
  }

  async function create() {
    setBusy("create");
    setNotice(null);
    setError(null);
    try {
      const order = await api<TestOrder>(`${base}/test-registration`, { method: "POST" });
      setNotice(
        order.email_sent
          ? `Inscrição de teste ${order.code} criada. O e-mail foi enviado para ${order.email}.`
          : `Inscrição de teste ${order.code} criada, mas o e-mail falhou. Use o link dos ingressos abaixo.`,
      );
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(null);
    }
  }

  async function removeAll() {
    if (!window.confirm("Remover todas as inscrições de teste e devolver as vagas?")) return;
    setBusy("delete");
    setNotice(null);
    try {
      const { removed } = await api<{ removed: number }>(`${base}/test-registrations`, {
        method: "DELETE",
      });
      setNotice(`${removed} inscrição(ões) de teste removida(s). As vagas foram devolvidas.`);
      setDone({});
      try {
        localStorage.removeItem(storageKey(params.slug));
      } catch {
        /* navegação privada */
      }
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(null);
    }
  }

  if (!me || orders === null) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  const latest = orders[0];
  const total = STEPS.length;
  const completed = STEPS.filter((s) => done[s.id]).length;
  const href = (step: Step) => {
    if (!step.link || !latest) return null;
    const target = step.link(latest);
    return target.startsWith("/") ? target : `/painel/eventos/${params.slug}/${target}`;
  };

  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">Teste geral</h1>
        <p className="text-muted">
          Cria uma inscrição de verdade para o seu e-mail ({me.email}) com 3 pessoas — adulto,
          criança e idosa com atendimento prioritário — para conferir todo o caminho do
          participante e da recepção. Funciona mesmo com as inscrições fechadas.
        </p>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-title font-semibold text-strong">Inscrições de teste</h2>
            <p className="text-sm text-muted">
              Ocupam vagas até serem removidas. Não recebem os lembretes em massa e não impedem
              sua inscrição real.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button loading={busy === "create"} onClick={create}>
              Criar inscrição de teste
            </Button>
            {orders.length > 0 && (
              <Button variant="ghost-danger" loading={busy === "delete"} onClick={removeAll}>
                Remover testes
              </Button>
            )}
          </div>
        </div>
        {orders.length === 0 ? (
          <p className="rounded-xl bg-line/[0.05] px-4 py-3 text-sm text-muted">
            Nenhuma inscrição de teste no momento.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {orders.map((o) => (
              <li key={o.code} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="font-semibold tracking-wider text-fg">{o.code}</p>
                  <p className="text-sm text-muted">
                    {o.people} pessoas · {o.present} dentro · {o.valid} aguardando ·{" "}
                    {o.cancelled} canceladas · e-mail {o.email_sent ? "enviado" : "não enviado"}
                  </p>
                </div>
                <a
                  href={`/ingresso/${o.token}`}
                  target="_blank"
                  className="inline-flex min-h-touch items-center justify-center whitespace-nowrap rounded-xl border border-border bg-line/[0.03] px-5 text-sm font-semibold hover:bg-line/[0.07]"
                >
                  Abrir ingressos ↗
                </a>
              </li>
            ))}
          </ul>
        )}
        {notice && (
          <p role="status" className="rounded-xl bg-success/10 px-4 py-3 text-sm text-success">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-title font-semibold text-strong">Roteiro de verificação</h2>
          <p className="text-sm text-muted">
            {completed} de {total} concluídos
          </p>
        </div>
        <ol className="space-y-3">
          {STEPS.map((step, index) => {
            const link = href(step);
            return (
              <li
                key={step.id}
                className={cn(
                  "flex gap-3 rounded-xl border p-4",
                  done[step.id] ? "border-success/30 bg-success/5" : "border-border",
                )}
              >
                <input
                  type="checkbox"
                  aria-label={`Concluído: ${step.title}`}
                  checked={!!done[step.id]}
                  onChange={() => toggle(step.id)}
                  className="mt-1 size-5 shrink-0 accent-[rgb(var(--rgb-brand))]"
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className={cn("font-semibold", done[step.id] ? "text-muted" : "text-fg")}>
                    {index + 1}. {step.title}
                  </p>
                  <p className="text-sm text-muted">{step.detail}</p>
                  {link && (
                    <a
                      href={link}
                      target={link.startsWith("/ingresso") ? "_blank" : undefined}
                      className="inline-block text-sm font-semibold text-primary underline"
                    >
                      Abrir
                    </a>
                  )}
                </div>
              </li>
            );
          })}
          <li className="flex gap-3 rounded-xl border border-border p-4">
            <span aria-hidden className="mt-0.5 text-lg">
              🧹
            </span>
            <div className="space-y-1">
              <p className="font-semibold text-fg">{total + 1}. Remover os testes</p>
              <p className="text-sm text-muted">
                Ao terminar, use “Remover testes” acima: apaga as inscrições e entradas de teste e
                devolve as vagas.
              </p>
            </div>
          </li>
        </ol>
      </Card>
    </main>
  );
}
