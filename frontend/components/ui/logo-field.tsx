"use client";

/* eslint-disable @next/next/no-img-element -- logos vêm da API (já otimizados e em cache) */
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

type Props = {
  wide?: boolean; // banner (proporção 3:1)
  label: string;
  hint: string;
  url: string | null;
  disabled?: boolean;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
};

/** Envio de logo com prévia sobre o fundo escuro do site. */
export function LogoField({
  wide,
  label,
  hint,
  url,
  disabled,
  onUpload,
  onRemove,
}: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível enviar. Tente de novo.",
      );
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-soft">{label}</p>
      <div
        className={
          wide
            ? "grid aspect-[3/1] place-items-center overflow-hidden rounded-2xl border border-dashed border-border bg-bg"
            : "grid min-h-[140px] place-items-center rounded-2xl border border-dashed border-border bg-bg p-4"
        }
      >
        {url ? (
          <img
            src={url}
            alt={`Prévia: ${label}`}
            className={
              wide
                ? "h-full w-full object-cover"
                : "max-h-32 w-auto max-w-full object-contain"
            }
          />
        ) : (
          <p className="text-sm text-subtle">
            {wide ? "Nenhum banner enviado" : "Nenhum logo enviado"}
          </p>
        )}
      </div>
      <p className="text-sm text-muted">{hint}</p>
      <input
        ref={input}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/svg+xml"
        className="sr-only"
        aria-label={`Escolher arquivo: ${label}`}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) run(() => onUpload(file));
        }}
      />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          loading={busy}
          disabled={disabled}
          onClick={() => input.current?.click()}
        >
          {url
            ? `Trocar ${wide ? "banner" : "logo"}`
            : `Enviar ${wide ? "banner" : "logo"}`}
        </Button>
        {url && (
          <Button
            type="button"
            variant="ghost-danger"
            disabled={disabled || busy}
            onClick={() => {
              if (
                window.confirm(
                  wide ? "Remover este banner?" : "Remover este logo?",
                )
              )
                run(onRemove);
            }}
          >
            Remover
          </Button>
        )}
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger"
        >
          {error}
        </p>
      )}
    </div>
  );
}
