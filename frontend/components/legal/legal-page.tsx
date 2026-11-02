import Link from "next/link";
import type { ReactNode } from "react";

export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
      <Link href="/" className="text-sm font-semibold text-primary">
        ← EVENTMER
      </Link>
      <h1 className="mb-6 mt-3 text-3xl font-bold">{title}</h1>
      <div className="space-y-4 leading-relaxed text-fg [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1">
        {children}
      </div>
    </main>
  );
}
