"use client";

import { useId } from "react";
import { cn } from "@/lib/cn";

type NumberFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
  hint?: string;
  className?: string;
};

/** Campo numérico com botões − / + grandes, confortável no celular. */
export function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max = 100_000,
  step = 1,
  suffix,
  hint,
  className,
}: NumberFieldProps) {
  const id = useId();
  const clamp = (n: number) =>
    Math.min(max, Math.max(min, Number.isFinite(n) ? n : min));
  const stepButton =
    "grid min-h-touch min-w-[44px] place-items-center text-xl font-semibold text-primary " +
    "hover:bg-line/[0.07] disabled:opacity-40";

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-soft">
        {label}
      </label>
      <div className="flex items-stretch overflow-hidden rounded-xl border border-border bg-line/[0.03] focus-within:ring-2 focus-within:ring-primary/30">
        <button
          type="button"
          aria-label={`Diminuir ${label}`}
          className={stepButton}
          disabled={value <= min}
          onClick={() => onChange(clamp(value - step))}
        >
          −
        </button>
        <div className="flex flex-1 items-center justify-center gap-1 border-x border-border">
          <input
            id={id}
            type="number"
            inputMode="numeric"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(clamp(parseInt(e.target.value, 10)))}
            className="w-full min-w-0 bg-transparent py-2 text-center text-lg font-semibold tabular-nums focus:outline-none"
          />
          {suffix && <span className="pr-3 text-muted">{suffix}</span>}
        </div>
        <button
          type="button"
          aria-label={`Aumentar ${label}`}
          className={stepButton}
          disabled={value >= max}
          onClick={() => onChange(clamp(value + step))}
        >
          +
        </button>
      </div>
      {hint && <p className="text-sm text-muted">{hint}</p>}
    </div>
  );
}
