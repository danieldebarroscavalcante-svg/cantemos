import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "ghost-danger" | "danger";

// DESIGN.md: primário em gradiente da marca, MAIÚSCULO, peso 700, brilho verde só no hover.
const variants: Record<Variant, string> = {
  primary:
    "bg-brand text-primary-fg font-bold uppercase tracking-wide shadow-sm hover:-translate-y-px hover:shadow-cta",
  secondary:
    "border border-border bg-line/[0.03] text-fg text-sm font-semibold hover:bg-line/[0.07]",
  ghost: "text-fg font-semibold hover:bg-line/[0.07]",
  "ghost-danger": "text-danger font-semibold hover:bg-danger/10",
  danger: "bg-danger text-strong font-bold hover:bg-danger/90",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
  block?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      loading,
      block,
      className,
      children,
      disabled,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={cn(
          // Botões nunca quebram linha: o texto fica sempre em uma linha só.
          "inline-flex min-h-touch shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-5 text-sm",
          "transition-[box-shadow,transform,background-color] duration-200",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
          "disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none",
          variants[variant],
          block && "w-full",
          className,
        )}
        {...props}
      >
        {loading && (
          <span
            aria-hidden
            className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
        )}
        {children}
      </button>
    );
  },
);
