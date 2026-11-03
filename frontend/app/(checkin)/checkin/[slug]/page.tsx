"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Scanner } from "@/components/checkin/scanner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import {
  checkinApi,
  currentOperator,
  deviceId,
  feedback,
  saveVolunteerToken,
  volunteerLogin,
  type Attendee,
  type CheckinResult,
  type Operator,
  type OrderBrief,
  type Summary,
} from "@/lib/checkin";
import { cn } from "@/lib/cn";

const AGE = { adulto: "Adulto", crianca: "Criança", idoso: "Idoso" } as const;

function PriorityBadge({
  attendee,
  large,
}: {
  attendee: Attendee;
  large?: boolean;
}) {
  if (!attendee.priority) return null;
  const need =
    attendee.accessibility_need &&
    attendee.accessibility_need !== "Atendimento prioritário"
      ? ` · ${attendee.accessibility_need}`
      : "";
  return (
    <span
      className={cn(
        "inline-block rounded-full bg-primary-fg font-bold text-warning ring-1 ring-warning/70",
        large ? "px-4 py-2 text-lg" : "px-2 py-0.5 text-xs",
      )}
    >
      ♿ Prioritário{need}
    </span>
  );
}

// ------------------------------------------------------------------ entrada do voluntário

function LoginCard({
  slug,
  onLogged,
}: {
  slug: string;
  onLogged: (op: Operator) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setLoading(true);
    setError(null);
    try {
      onLogged(
        await volunteerLogin(
          slug,
          String(form.get("code")),
          String(form.get("name")),
        ),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.",
      );
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-10">
      <p className="eyebrow">EVENTMER</p>
      <h1 className="mb-1 text-3xl font-normal leading-tight text-strong">
        Recepção
      </h1>
      <p className="mb-6 text-muted">
        Digite o código que a coordenação passou para a equipe.
      </p>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            label="Código da recepção"
            name="code"
            required
            autoComplete="off"
            autoCapitalize="characters"
            maxLength={12}
            className="text-center text-2xl font-bold uppercase tracking-[0.3em]"
          />
          <Input
            label="Seu nome"
            name="name"
            required
            minLength={2}
            maxLength={60}
            autoComplete="given-name"
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
            Entrar na recepção
          </Button>
        </form>
      </Card>
    </main>
  );
}

// ------------------------------------------------------------------ contador

function Counter({ summary }: { summary: Summary | null }) {
  if (!summary) return <div className="h-16" />;
  const pct = Math.min(
    100,
    Math.round((summary.present / Math.max(1, summary.capacity)) * 100),
  );
  const full = summary.present >= summary.capacity;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-3xl font-bold tabular-nums">
          {summary.present}
          <span className="text-title font-semibold text-strong text-muted">
            {" "}
            / {summary.capacity} lugares
          </span>
        </p>
        <p className="text-right text-sm text-muted">
          {summary.registered} inscritos
          <br />
          {summary.priority_present} prioritários presentes
        </p>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-line/10">
        <div
          className={cn(
            "h-full transition-all",
            full ? "bg-danger" : pct >= 85 ? "bg-warning" : "bg-success",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {full && (
        <p
          role="alert"
          className="rounded-xl bg-danger px-3 py-2 text-center font-bold text-strong"
        >
          Lotação atingida — avise a coordenação
        </p>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ resultado da leitura

const RESULT_STYLE: Record<CheckinResult["result"], string> = {
  ok: "bg-success text-primary-fg",
  already: "bg-warning text-primary-fg",
  cancelled: "bg-danger text-strong",
  invalid: "bg-danger text-strong",
  other_event: "bg-danger text-strong",
};

function ResultOverlay({
  result,
  busy,
  onFamily,
  onClose,
}: {
  result: CheckinResult;
  busy: boolean;
  onFamily: () => void;
  onClose: () => void;
}) {
  const others =
    result.order?.tickets.filter((t) => t.id !== result.ticket?.id) ?? [];
  const pending = others.filter((t) => t.status === "valid");
  return (
    <div
      role="alertdialog"
      aria-live="assertive"
      className={cn(
        "fixed inset-0 z-50 flex flex-col overflow-y-auto p-5",
        RESULT_STYLE[result.result],
      )}
    >
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center gap-4 text-center">
        <p className="text-6xl" aria-hidden>
          {result.result === "ok"
            ? "✓"
            : result.result === "already"
              ? "!"
              : "✕"}
        </p>
        <p className="text-3xl font-black uppercase">{result.message}</p>
        {result.ticket && (
          <div className="space-y-2">
            <p className="text-4xl font-bold">{result.ticket.name}</p>
            <p className="text-xl opacity-90">{AGE[result.ticket.age_group]}</p>
            <PriorityBadge attendee={result.ticket} large />
          </div>
        )}
        {others.length > 0 && (
          <div className="rounded-2xl bg-bg/20 p-4 text-left">
            <p className="mb-2 font-semibold">
              Mesma inscrição ({result.order?.code}) ·{" "}
              {result.order?.buyer_name}
            </p>
            <ul className="space-y-1">
              {others.map((t) => (
                <li
                  key={t.id}
                  className="flex flex-wrap items-center justify-between gap-2"
                >
                  <span>
                    {t.name}{" "}
                    <span className="opacity-75">· {AGE[t.age_group]}</span>{" "}
                    <PriorityBadge attendee={t} />
                  </span>
                  <span className="text-sm font-semibold">
                    {t.status === "used"
                      ? "✓ dentro"
                      : t.status === "valid"
                        ? "aguardando"
                        : "cancelado"}
                  </span>
                </li>
              ))}
            </ul>
            {pending.length > 0 && (
              <button
                type="button"
                onClick={onFamily}
                disabled={busy}
                className="mt-3 min-h-touch w-full rounded-xl bg-strong/90 px-4 font-bold text-primary-fg disabled:opacity-60"
              >
                Registrar entrada de mais {pending.length}
              </button>
            )}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="mx-auto mt-4 min-h-[56px] w-full max-w-lg rounded-2xl bg-bg/25 text-xl font-bold"
      >
        Próximo
      </button>
    </div>
  );
}

// ------------------------------------------------------------------ busca por nome

function OrderCard({
  order,
  operator,
  busy,
  onCheckin,
  onAll,
  onUndo,
}: {
  order: OrderBrief;
  operator: Operator;
  busy: boolean;
  onCheckin: (id: string) => void;
  onAll: () => void;
  onUndo: (id: string) => void;
}) {
  const pending = order.tickets.filter((t) => t.status === "valid");
  return (
    <Card className="space-y-3 p-4 sm:p-4">
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-semibold">{order.buyer_name}</p>
        <p className="text-sm tracking-wider text-muted">{order.code}</p>
      </div>
      <ul className="divide-y divide-border">
        {order.tickets.map((t) => (
          <li
            key={t.id}
            className="flex flex-wrap items-center justify-between gap-2 py-2"
          >
            <div>
              <p
                className={cn(
                  "font-medium",
                  t.status === "cancelled" && "text-muted line-through",
                )}
              >
                {t.name}
              </p>
              <p className="text-sm text-muted">
                {AGE[t.age_group]}{" "}
                {t.status === "used" &&
                  `· entrou ${t.checked_in_at?.slice(11, 16) ?? ""}${t.checked_in_by ? ` (${t.checked_in_by})` : ""}`}
                {t.status === "cancelled" && "· cancelado"}
              </p>
              <PriorityBadge attendee={t} />
            </div>
            {t.status === "valid" && (
              <Button
                onClick={() => onCheckin(t.id)}
                disabled={busy}
                className="min-w-[110px]"
              >
                Entrada
              </Button>
            )}
            {t.status === "used" &&
              (operator.can_undo || t.checked_in_by === operator.name) && (
                <Button
                  variant="ghost"
                  onClick={() => onUndo(t.id)}
                  disabled={busy}
                  className="text-sm"
                >
                  Desfazer
                </Button>
              )}
          </li>
        ))}
      </ul>
      {pending.length > 1 && (
        <Button variant="secondary" block onClick={onAll} disabled={busy}>
          Entrada de todos ({pending.length})
        </Button>
      )}
    </Card>
  );
}

function SearchPanel({
  slug,
  operator,
  onSummary,
}: {
  slug: string;
  operator: Operator;
  onSummary: () => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<OrderBrief[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (q: string) => {
      if (q.trim().length < 2) {
        setResults(null);
        return;
      }
      try {
        setResults(
          await checkinApi<OrderBrief[]>(
            slug,
            `/search?q=${encodeURIComponent(q)}`,
          ),
        );
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Sem conexão.");
      }
    },
    [slug],
  );

  useEffect(() => {
    const timer = setTimeout(() => run(query), 300);
    return () => clearTimeout(timer);
  }, [query, run]);

  async function act(fn: () => Promise<unknown>, sound: "ok" | "warn") {
    setBusy(true);
    try {
      await fn();
      feedback(sound);
      await run(query);
      onSummary();
    } catch (err) {
      feedback("error");
      setError(err instanceof ApiError ? err.message : "Sem conexão.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <Input
        label="Buscar por nome, responsável ou código"
        type="search"
        autoComplete="off"
        placeholder="Ex.: Maria, Souza, CAN-3K4BV"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
        >
          {error}
        </p>
      )}
      {results?.length === 0 && (
        <p className="text-muted">Ninguém encontrado com “{query}”.</p>
      )}
      <div className="space-y-3">
        {results?.map((order) => (
          <OrderCard
            key={order.code}
            order={order}
            operator={operator}
            busy={busy}
            onCheckin={(id) =>
              act(
                () =>
                  checkinApi(slug, `/tickets/${id}/checkin`, {
                    method: "POST",
                  }),
                "ok",
              )
            }
            onAll={() =>
              act(
                () =>
                  checkinApi(slug, `/orders/${order.code}/checkin`, {
                    method: "POST",
                  }),
                "ok",
              )
            }
            onUndo={(id) =>
              act(
                () =>
                  checkinApi(slug, `/tickets/${id}/undo`, { method: "POST" }),
                "warn",
              )
            }
          />
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ tela principal

export default function CheckinPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const [operator, setOperator] = useState<Operator | null | undefined>(
    undefined,
  );
  const [summary, setSummary] = useState<Summary | null>(null);
  const [tab, setTab] = useState<"camera" | "busca">("camera");
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);
  const lastScan = useRef<{ value: string; at: number }>({ value: "", at: 0 });
  const closeTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    currentOperator(slug).then(setOperator);
  }, [slug]);

  const refreshSummary = useCallback(() => {
    checkinApi<Summary>(slug, "/summary")
      .then((s) => {
        setSummary(s);
        setOffline(false);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) setOperator(null);
        else setOffline(true);
      });
  }, [slug]);

  useEffect(() => {
    if (!operator) return;
    refreshSummary();
    const timer = setInterval(refreshSummary, 10_000);
    return () => clearInterval(timer);
  }, [operator, refreshSummary]);

  const close = useCallback(() => {
    clearTimeout(closeTimer.current);
    setResult(null);
  }, []);

  const show = useCallback(
    (res: CheckinResult) => {
      setResult(res);
      setSummary(res.summary);
      feedback(
        res.result === "ok"
          ? "ok"
          : res.result === "already"
            ? "warn"
            : "error",
      );
      const familyPending = res.order?.tickets.some(
        (t) => t.id !== res.ticket?.id && t.status === "valid",
      );
      clearTimeout(closeTimer.current);
      if (res.result === "ok" && !familyPending)
        closeTimer.current = setTimeout(close, 2500);
    },
    [close],
  );

  const onScan = useCallback(
    async (value: string) => {
      const now = Date.now();
      if (result || busy) return;
      if (value === lastScan.current.value && now - lastScan.current.at < 4000)
        return;
      lastScan.current = { value, at: now };
      setBusy(true);
      try {
        show(
          await checkinApi<CheckinResult>(slug, "/scan", {
            method: "POST",
            body: JSON.stringify({ qr: value, device_id: deviceId() }),
          }),
        );
        setOffline(false);
      } catch (err) {
        feedback("error");
        if (err instanceof ApiError && err.status === 401) setOperator(null);
        else setOffline(true);
      } finally {
        setBusy(false);
      }
    },
    [busy, result, show, slug],
  );

  async function checkInFamily() {
    if (!result?.order) return;
    setBusy(true);
    try {
      const order = await checkinApi<OrderBrief>(
        slug,
        `/orders/${result.order.code}/checkin`,
        { method: "POST" },
      );
      feedback("ok");
      setResult({ ...result, order });
      refreshSummary();
      clearTimeout(closeTimer.current);
      closeTimer.current = setTimeout(close, 2000);
    } catch {
      feedback("error");
    } finally {
      setBusy(false);
    }
  }

  function leave() {
    saveVolunteerToken(slug, null);
    setOperator(null);
  }

  if (operator === undefined) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted">
        Carregando…
      </main>
    );
  }
  if (operator === null)
    return <LoginCard slug={slug} onLogged={setOperator} />;

  return (
    <main className="mx-auto w-full max-w-6xl space-y-4 px-4 py-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          {operator.event_logo_url && (
            // eslint-disable-next-line @next/next/no-img-element -- logo vem da API (em cache)
            <img
              src={operator.event_logo_url}
              alt=""
              className="mb-2 h-10 w-auto max-w-[160px] object-contain"
            />
          )}
          <p className="eyebrow">Recepção</p>
          <h1 className="text-xl font-semibold leading-tight text-strong">
            {operator.event_title}
          </h1>
          <p className="text-sm text-muted">Operando: {operator.name}</p>
        </div>
        {!operator.can_undo && (
          <Button variant="ghost" onClick={leave} className="text-sm">
            Sair
          </Button>
        )}
      </header>

      {offline && (
        <p
          role="alert"
          className="rounded-xl bg-danger px-4 py-2 text-center font-semibold text-strong"
        >
          Sem conexão com o servidor — use a busca quando voltar, ou a lista
          impressa.
        </p>
      )}

      <Card className="p-4 sm:p-4">
        <Counter summary={summary} />
      </Card>

      {/* Celular: abas. Tablet deitado / desktop: câmera e busca lado a lado. */}
      <div
        className="grid grid-cols-2 gap-2 rounded-2xl bg-line/[0.05] p-1 md:hidden"
        role="tablist"
      >
        {(["camera", "busca"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={cn(
              "min-h-touch rounded-xl font-semibold",
              tab === t ? "bg-surface shadow-sm" : "text-muted",
            )}
          >
            {t === "camera" ? "📷 Ler QR Code" : "🔎 Buscar nome"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <section
          className={cn(tab !== "camera" && "hidden md:block")}
          aria-label="Leitor de QR Code"
        >
          <Scanner
            onScan={onScan}
            paused={Boolean(result) || tab !== "camera"}
          />
          <p className="mt-2 text-center text-sm text-muted">
            Aponte a câmera para o QR Code do ingresso.
          </p>
        </section>
        <section
          className={cn(tab !== "busca" && "hidden md:block")}
          aria-label="Busca por nome"
        >
          <SearchPanel
            slug={slug}
            operator={operator}
            onSummary={refreshSummary}
          />
        </section>
      </div>

      {result && (
        <ResultOverlay
          result={result}
          busy={busy}
          onFamily={checkInFamily}
          onClose={close}
        />
      )}
    </main>
  );
}
