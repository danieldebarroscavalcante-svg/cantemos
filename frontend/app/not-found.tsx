import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 px-4 text-center">
      <p className="eyebrow">EVENTMER</p>
      <h1 className="text-3xl font-normal leading-tight text-strong">
        Página não encontrada
      </h1>
      <p className="text-muted">
        O endereço pode estar incompleto, ou o evento ainda não foi publicado.
      </p>
      <Link href="/" className="font-semibold text-primary underline">
        Voltar ao início
      </Link>
    </main>
  );
}
