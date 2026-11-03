"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useEventAccess } from "@/lib/use-event-access";
import { useMe } from "@/lib/use-me";

type Texts = {
  subject: string;
  heading: string;
  body: string;
  button_label: string;
};
type Message = Texts & {
  kind: string;
  title: string;
  description: string;
  custom: boolean;
  fields: { key: string; label: string }[];
};
type FieldName = keyof Texts;

const FIELD_LABEL: Record<FieldName, string> = {
  subject: "Assunto do e-mail",
  heading: "Título",
  body: "Texto",
  button_label: "Texto do botão",
};

const inputClass =
  "w-full rounded-xl border border-border bg-line/[0.03] px-4 text-base text-fg placeholder:text-subtle focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/30";

export default function MessagesPage({ params }: { params: { slug: string } }) {
  const me = useMe();
  const base = `/org/events/${params.slug}/messages`;
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [kind, setKind] = useState<string>("confirmation");
  const [draft, setDraft] = useState<Texts | null>(null);
  const [preview, setPreview] = useState<{
    subject: string;
    html: string;
  } | null>(null);
  const [frameHeight, setFrameHeight] = useState(900);
  const [busy, setBusy] = useState<"save" | "test" | "reset" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastField = useRef<{
    name: FieldName;
    el: HTMLInputElement | HTMLTextAreaElement;
  } | null>(null);
  const access = useEventAccess(params.slug, !!me);
  const canEdit = access?.permissions.edit_event ?? false;

  const current = messages?.find((m) => m.kind === kind) ?? null;
  const dirty =
    !!current &&
    !!draft &&
    (["subject", "heading", "body", "button_label"] as FieldName[]).some(
      (k) => draft[k] !== current[k],
    );

  useEffect(() => {
    if (!me) return;
    api<Message[]>(base)
      .then((list) => {
        setMessages(list);
        const first = list[0];
        setDraft({
          subject: first.subject,
          heading: first.heading,
          body: first.body,
          button_label: first.button_label,
        });
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Falha ao carregar."),
      );
  }, [me, base]);

  // Prévia em tempo real: renderiza no servidor (mesmo HTML do envio) 400 ms após a última tecla.
  const valid =
    !!draft && Object.values(draft).every((value) => value.trim().length >= 2);
  useEffect(() => {
    if (!draft || !valid) return;
    const timer = setTimeout(() => {
      api<{ subject: string; html: string }>(`${base}/${kind}/preview`, {
        method: "POST",
        body: JSON.stringify(draft),
      })
        .then(setPreview)
        .catch(() => undefined);
    }, 400);
    return () => clearTimeout(timer);
  }, [draft, kind, base, valid]);

  function selectKind(next: string) {
    if (
      dirty &&
      !window.confirm("Há alterações não salvas nesta mensagem. Descartar?")
    )
      return;
    const message = messages?.find((m) => m.kind === next);
    if (!message) return;
    setKind(next);
    setDraft({
      subject: message.subject,
      heading: message.heading,
      body: message.body,
      button_label: message.button_label,
    });
    setNotice(null);
    setError(null);
  }

  function update(name: FieldName, value: string) {
    setDraft((d) => (d ? { ...d, [name]: value } : d));
    setNotice(null);
  }

  function insertField(key: string) {
    const target = lastField.current;
    const token = `{${key}}`;
    if (!target || !draft) {
      update("body", `${draft?.body ?? ""}${token}`);
      return;
    }
    const { name, el } = target;
    const start = el.selectionStart ?? draft[name].length;
    const end = el.selectionEnd ?? start;
    const value = draft[name].slice(0, start) + token + draft[name].slice(end);
    update(name, value);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  }

  function replaceMessage(saved: Message) {
    setMessages(
      (list) => list?.map((m) => (m.kind === saved.kind ? saved : m)) ?? list,
    );
    setDraft({
      subject: saved.subject,
      heading: saved.heading,
      body: saved.body,
      button_label: saved.button_label,
    });
  }

  async function run(action: "save" | "test" | "reset") {
    if (!draft) return;
    if (
      action === "reset" &&
      !window.confirm("Voltar ao texto padrão desta mensagem?")
    )
      return;
    setBusy(action);
    setNotice(null);
    setError(null);
    try {
      if (action === "save") {
        replaceMessage(
          await api<Message>(`${base}/${kind}`, {
            method: "PUT",
            body: JSON.stringify(draft),
          }),
        );
        setNotice("Mensagem salva. Os próximos envios já usam este texto.");
      } else if (action === "reset") {
        replaceMessage(
          await api<Message>(`${base}/${kind}`, { method: "DELETE" }),
        );
        setNotice("Texto padrão restaurado.");
      } else {
        const { sent_to } = await api<{ sent_to: string }>(
          `${base}/${kind}/test`,
          {
            method: "POST",
            body: JSON.stringify(draft),
          },
        );
        setNotice(`Teste enviado para ${sent_to}, com dados de exemplo.`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(null);
    }
  }

  if (!me || !messages || !draft || !current) {
    return (
      <main className="grid min-h-dvh place-items-center px-4 text-center text-muted">
        {error ?? "Carregando…"}
      </main>
    );
  }

  const field = (name: FieldName, multiline = false) => (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={`f-${name}`} className="text-sm font-medium text-soft">
        {FIELD_LABEL[name]}
      </label>
      {multiline ? (
        <textarea
          id={`f-${name}`}
          rows={9}
          value={draft[name]}
          disabled={!canEdit}
          onFocus={(e) => (lastField.current = { name, el: e.currentTarget })}
          onChange={(e) => update(name, e.target.value)}
          className={cn(inputClass, "py-3 leading-relaxed")}
        />
      ) : (
        <input
          id={`f-${name}`}
          value={draft[name]}
          disabled={!canEdit}
          onFocus={(e) => (lastField.current = { name, el: e.currentTarget })}
          onChange={(e) => update(name, e.target.value)}
          className={cn(inputClass, "min-h-touch")}
        />
      )}
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 md:py-10">
      <div>
        <Link href="/painel" className="text-sm font-semibold text-primary">
          ← Painel
        </Link>
        <h1 className="mt-2 text-3xl font-normal leading-tight text-strong">
          Mensagens de e-mail
        </h1>
        <p className="text-muted">
          Personalize o texto de cada e-mail. A prévia ao lado mostra como a
          mensagem chega, com dados de exemplo.
        </p>
      </div>

      <div
        className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1"
        role="tablist"
      >
        {messages.map((m) => (
          <button
            key={m.kind}
            role="tab"
            aria-selected={m.kind === kind}
            onClick={() => selectKind(m.kind)}
            className={cn(
              "min-h-touch shrink-0 whitespace-nowrap rounded-xl border px-4 text-sm font-semibold",
              m.kind === kind
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-line/[0.03] text-fg hover:bg-line/[0.07]",
            )}
          >
            {m.title}
            {m.custom && (
              <span className="ml-2 text-xs text-subtle">editado</span>
            )}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card className="space-y-4">
          <div>
            <h2 className="text-title font-semibold text-strong">
              {current.title}
            </h2>
            <p className="text-sm text-muted">{current.description}</p>
          </div>
          {field("subject")}
          {field("heading")}
          {field("body", true)}
          <p className="-mt-2 text-xs text-subtle">
            Deixe uma linha em branco para começar um novo parágrafo.
          </p>
          {field("button_label")}

          <div className="space-y-2">
            <p className="text-sm font-medium text-soft">Campos automáticos</p>
            <p className="text-xs text-subtle">
              Clique para inserir onde está o cursor. Cada pessoa recebe os
              próprios dados.
            </p>
            <div className="flex flex-wrap gap-2">
              {current.fields.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  disabled={!canEdit}
                  onClick={() => insertField(f.key)}
                  title={f.label}
                  className="min-h-[36px] whitespace-nowrap rounded-md border border-border bg-line/[0.03] px-3 font-mono text-xs text-fg hover:border-primary/40 hover:text-primary disabled:opacity-50"
                >
                  {`{${f.key}}`}
                  <span className="ml-1.5 font-sans text-subtle">
                    {f.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {canEdit && (
            <div className="flex flex-wrap gap-2 pt-2">
              <Button
                loading={busy === "save"}
                disabled={!dirty || !valid}
                onClick={() => run("save")}
              >
                Salvar mensagem
              </Button>
              <Button
                variant="secondary"
                loading={busy === "test"}
                disabled={!valid}
                onClick={() => run("test")}
              >
                Enviar teste para mim
              </Button>
              {current.custom && (
                <Button
                  variant="ghost"
                  loading={busy === "reset"}
                  onClick={() => run("reset")}
                >
                  Restaurar padrão
                </Button>
              )}
            </div>
          )}
          {!valid && (
            <p className="text-sm text-danger">
              Preencha todos os campos (mínimo 2 caracteres).
            </p>
          )}
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
        </Card>

        <section
          aria-label="Prévia do e-mail"
          className="space-y-2 lg:sticky lg:top-6 lg:self-start"
        >
          <div className="flex items-baseline justify-between gap-3">
            <p className="eyebrow">Prévia em tempo real</p>
            {dirty && <p className="text-xs text-subtle">não salvo</p>}
          </div>
          <div className="rounded-2xl border border-border-subtle bg-surface p-3 text-sm">
            <span className="text-subtle">Assunto: </span>
            <span className="font-semibold text-fg">
              {preview?.subject ?? "…"}
            </span>
          </div>
          <iframe
            title="Prévia do e-mail"
            sandbox="allow-same-origin"
            srcDoc={preview?.html ?? ""}
            onLoad={(e) => {
              const doc = e.currentTarget.contentDocument;
              if (doc) setFrameHeight(doc.documentElement.scrollHeight + 8);
            }}
            style={{ height: frameHeight }}
            className="w-full rounded-2xl border border-border-subtle bg-bg"
          />
        </section>
      </div>
    </main>
  );
}
