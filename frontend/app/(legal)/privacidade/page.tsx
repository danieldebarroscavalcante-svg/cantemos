import type { Metadata } from "next";
import { LegalPage } from "@/components/legal/legal-page";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Política de Privacidade" };

export default function PrivacidadePage() {
  const contact = site.contactEmail ? (
    <a
      className="font-semibold text-primary underline"
      href={`mailto:${site.contactEmail}`}
    >
      {site.contactEmail}
    </a>
  ) : (
    "o e-mail de contato informado nas mensagens do evento"
  );

  return (
    <LegalPage title="Política de Privacidade">
      <p className="text-sm text-muted">Última atualização: {site.updatedAt}</p>
      <p>
        O EVENTMER é a plataforma de inscrições e credenciamento usada pela{" "}
        <strong>{site.orgName}</strong> (controladora dos dados) para os seus
        eventos, como o CANTEMOS. Esta política explica, conforme a Lei Geral de
        Proteção de Dados (Lei nº 13.709/2018 — LGPD), quais dados coletamos,
        por que e quais são os seus direitos.
      </p>

      <h2>Quais dados coletamos</h2>
      <ul>
        <li>
          Do responsável pela inscrição: nome, e-mail e telefone (opcional).
        </li>
        <li>
          Dos acompanhantes: nome, faixa etária (adulto, criança, idoso) e, se
          informada, necessidade de acessibilidade ou atendimento prioritário.
        </li>
        <li>Registro de entrada no evento (data e hora do check-in).</li>
        <li>
          Da equipe organizadora: nome, e-mail e senha (guardada de forma
          criptografada).
        </li>
      </ul>
      <p>Não coletamos CPF, dados de pagamento nem dados biométricos.</p>

      <h2>Para que usamos</h2>
      <ul>
        <li>Confirmar a inscrição e enviar o ingresso com QR Code.</li>
        <li>Controlar a lotação e organizar a entrada no dia do evento.</li>
        <li>
          Garantir atendimento prioritário e acessibilidade a quem precisar.
        </li>
        <li>
          Enviar avisos sobre o evento em que você se inscreveu (lembretes,
          mudanças).
        </li>
      </ul>
      <p>
        A base legal é a execução do serviço que você solicitou (a inscrição) e
        o seu consentimento, registrado no momento da inscrição. Dados de
        acessibilidade são usados apenas para o seu atendimento no evento.
      </p>

      <h2>Com quem compartilhamos</h2>
      <p>
        Não vendemos nem cedemos seus dados. Eles são processados apenas por
        serviços que operam a plataforma: hospedagem (Vercel e Render), banco de
        dados (Aiven) e envio de e-mails (Google/Gmail). Voluntários da recepção
        veem somente o nome, o tipo de ingresso e a indicação de prioridade
        necessários para a entrada.
      </p>

      <h2>Por quanto tempo guardamos</h2>
      <p>
        Os dados de participantes são mantidos enquanto forem necessários para o
        evento e para a organização da edição seguinte, e então excluídos ou
        anonimizados. Você pode pedir a exclusão a qualquer momento.
      </p>

      <h2>Seus direitos</h2>
      <p>
        Você pode solicitar acesso, correção, exportação ou exclusão dos seus
        dados, e revogar o consentimento, pelo contato: {contact}. Também pode
        cancelar sua inscrição pelo link recebido por e-mail.
      </p>

      <h2>Segurança</h2>
      <p>
        Usamos conexão criptografada (HTTPS), senhas protegidas com bcrypt, QR
        Codes sem dados pessoais e acesso da equipe restrito por função.
      </p>
    </LegalPage>
  );
}
