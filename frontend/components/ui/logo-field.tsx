"use client";

/* eslint-disable @next/next/no-img-element -- logos vêm da API (já otimizados e em cache) */
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

type Size = { width: number; height: number };

type Props = {
  wide?: boolean; // banner (proporção 3:1)
  ideal: Size; // tamanho recomendado em px
  label: string;
  hint: string;
  url: string | null;
  disabled?: boolean;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
};

/** Envio de logo com prévia sobre o fundo escuro do site. */
const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : a);
const ratioLabel = ({ width, height }: Size) => {
  const d = gcd(width, height);
  return `${width / d}:${height / d}`;
};

/** Avisos (não bloqueiam o envio) quando a imagem foge do tamanho/proporção ideais. */
function sizeWarnings(actual: Size, ideal: Size, wide?: boolean): string[] {
  const warnings: string[] = [];
  if (actual.width < ideal.width / 2 || actual.height < ideal.height / 2) {
    warnings.push(
      "Imagem pequena: pode aparecer sem nitidez em telas grandes.",
    );
  }
  const diff = actual.width / actual.height / (ideal.width / ideal.height);
  if (diff < 0.7 || diff > 1.4) {
    warnings.push(
      wide
        ? "Proporção diferente da ideal: partes da imagem serão cortadas."
        : "Proporção diferente da ideal: o logo vai aparecer menor, com espaço sobrando.",
    );
  }
  return warnings;
}

export function LogoField({
  wide,
  ideal,
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
  const [actual, setActual] = useState<Size | null>(null);

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
            onLoad={(e) =>
              setActual({
                width: e.currentTarget.naturalWidth,
                height: e.currentTarget.naturalHeight,
              })
            }
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
      <p className="text-sm font-semibold text-soft">
        Tamanho ideal: {ideal.width} × {ideal.height} px · proporção{" "}
        {ratioLabel(ideal)}
      </p>
      {url && actual && actual.width > 0 && (
        <div className="space-y-1 text-sm">
          <p className="text-muted">
            Imagem atual: {actual.width} × {actual.height} px
          </p>
          {sizeWarnings(actual, ideal, wide).map((w) => (
            <p key={w} className="text-warning">
              {w}
            </p>
          ))}
        </div>
      )}
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
