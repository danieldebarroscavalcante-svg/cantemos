import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/legal/legal-page";
import { fetchOrganization } from "@/lib/server-api";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Termos de Uso" };

export const revalidate = 60;

export default async function TermosPage() {
  const orgName = (await fetchOrganization())?.name ?? site.orgName;
  return (
    <LegalPage title="Termos de Uso">
      <p className="text-sm text-muted">Última atualização: {site.updatedAt}</p>
      <p>
        Ao se inscrever em um evento pelo EVENTMER, plataforma usada pela{" "}
        <strong>{orgName}</strong>, você concorda com estes termos.
      </p>

      <h2>Inscrição e ingressos</h2>
      <ul>
        <li>
          As inscrições são gratuitas e limitadas à lotação definida pela
          organização.
        </li>
        <li>
          Cada inscrição tem um número máximo de participantes; os nomes
          informados devem ser verdadeiros.
        </li>
        <li>
          O ingresso é pessoal. O QR Code será lido na entrada e vale para uma
          única entrada.
        </li>
        <li>
          Se não puder comparecer, cancele sua inscrição pelo link recebido por
          e-mail para liberar a vaga a outra pessoa.
        </li>
      </ul>

      <h2>Lotação e entrada</h2>
      <p>
        Para compensar ausências, a organização pode aceitar inscrições acima do
        número de lugares. A inscrição não garante lugar sentado; recomendamos
        chegar no horário de abertura das portas. A organização pode recusar a
        entrada em caso de lotação esgotada por motivo de segurança.
      </p>

      <h2>Conduta</h2>
      <p>
        É proibido fazer inscrições em massa, revender ingressos ou tentar
        burlar os limites da plataforma. Inscrições nessas condições podem ser
        canceladas.
      </p>

      <h2>Dados pessoais</h2>
      <p>
        O uso dos seus dados está descrito na{" "}
        <Link
          href="/privacidade"
          className="font-semibold text-primary underline"
        >
          Política de Privacidade
        </Link>
        .
      </p>

      <h2>Alterações</h2>
      <p>
        A organização pode alterar data, horário ou condições do evento por
        motivo de força maior, avisando os inscritos por e-mail.
      </p>
    </LegalPage>
  );
}
