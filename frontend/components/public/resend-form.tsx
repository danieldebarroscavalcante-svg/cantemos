"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";

export function ResendForm({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = String(new FormData(event.currentTarget).get("email"));
    setLoading(true);
    try {
      const res = await api<{ detail: string }>(`/public/events/${slug}/resend`, {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(res.detail);
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Sem conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="min-h-touch text-sm font-semibold text-primary underline"
      >
        Já se inscreveu? Reenviar meu ingresso
      </button>
    );
  }
  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <Input
        label="E-mail usado na inscrição"
        name="email"
        type="email"
        inputMode="email"
        autoComplete="email"
        required
      />
      <Button type="submit" variant="secondary" loading={loading} block>
        Reenviar ingresso
      </Button>
      {message && (
        <p role="status" className="text-sm text-muted">
          {message}
        </p>
      )}
    </form>
  );
}
