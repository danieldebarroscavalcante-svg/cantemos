/* eslint-disable @next/next/no-img-element -- logo vem da API (em cache) */
import Link from "next/link";

/** Rodapé público com a igreja que realiza o evento. */
export function OrganizerFooter({
  name,
  logoUrl,
}: {
  name: string | null | undefined;
  logoUrl: string | null | undefined;
}) {
  return (
    <footer className="space-y-4 pt-4">
      <div className="divider-bronze" aria-hidden />
      {name && (
        <div className="flex items-center gap-3">
          {logoUrl && (
            <img
              src={logoUrl}
              alt=""
              className="h-12 w-auto max-w-[120px] object-contain"
            />
          )}
          <p className="text-sm text-muted">
            Realização
            <span className="block font-semibold text-fg">{name}</span>
          </p>
        </div>
      )}
      <nav className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-subtle">
        <Link href="/privacidade" className="hover:underline">
          Privacidade
        </Link>
        <Link href="/termos" className="hover:underline">
          Termos de uso
        </Link>
      </nav>
    </footer>
  );
}
