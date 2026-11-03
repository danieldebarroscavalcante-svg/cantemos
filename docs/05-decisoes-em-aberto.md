# 05 · Decisões em aberto

Perguntas que a coordenação precisa responder. Cada decisão tomada deve ser registrada aqui (coluna **Decisão**) e refletida nos demais documentos.

| # | Pergunta | Impacta | Proposta | Decisão |
|---|---|---|---|---|
| D1 | Qual a **data da próxima edição do CANTEMOS** e quando abrem as inscrições? | Roadmap inteiro | Fase 1 em produção ≥ 4 semanas antes da abertura | ✅ **19/11/2026 (quinta)**. Inscrições abrem em 09/11 — ver Plano Express no [roadmap](03-roadmap.md) |
| D2 | Domínio da plataforma (`eventmer.com.br`?) e quem será o titular | Fase 0 | Registrar em nome da igreja | ✅ **2026: sem domínio próprio**, endereço gratuito `*.vercel.app`. Domínio próprio depois do evento |
| D3 | O CANTEMOS será **gratuito** ou terá ingresso pago / contribuição? | Fase 1 x Fase 3 | MVP gratuito; contribuição voluntária na F3 | ✅ **Gratuito**. Pagamentos ficam para a F3 |
| D4 | Gateway de pagamento: **Mercado Pago** ou **Asaas**? Recebimento na conta PJ da igreja? | Fase 3 | Escolher pela menor taxa de PIX e facilidade de reembolso | _pendente_ |
| D5 | Provedor de e-mail transacional | Fase 0/1 | Resend ou Brevo (plano gratuito cobre o volume inicial) | ✅ **Conta Gmail**, enviando pela API do Gmail (o Render gratuito bloqueia SMTP). Ver [hospedagem](06-hospedagem-gratuita.md) |
| D6 | Quantas sessões, qual a **lotação** de cada uma e quantas **portas de entrada**? | EVT-02, CHK-10 | — | ✅ **Sessão única, 120 lugares, início 18h30** (portas às 18h00 — ajustável), **1 porta de entrada principal** |
| D7 | Lugares **livres** ou **marcados**? Haverá área reservada PCD/idosos? | TKT-04, TKT-15 | Lugares livres; cota de ~10 lugares "Prioridade" (PCD, idosos, gestantes) dentro dos 120 | ✅ Lugares livres; **cota de prioridade = 10, configurável no painel** (para mais e para menos) |
| D8 | Limite de ingressos por inscrição (ex.: até 6 por família)? | TKT-05 | Com só 120 lugares: **até 5 por pedido**, 1 pedido por e-mail | ✅ **Até 5 por inscrição, configurável no painel** |
| D9 | Coletar **CPF**? | LGPD, TKT-05 | Não no MVP (e-mail + telefone bastam) | _pendente_ |
| D10 | Haverá **pré-inscrição** para membros, coral e convidados? | TKT-08 | Sim, via código de acesso na F2 (ou cota reservada manualmente na F1) | _pendente_ |
| D11 | Caravanas de outras igrejas: quantas costumam vir e como são organizadas hoje? | TKT-10 | — | _pendente_ |
| D12 | Quem serão os **administradores** e quantos voluntários de recepção por sessão? | AUTH-04, ensaio geral | — | ✅ **~10 voluntários** na recepção, entrando com o **código da recepção** (sem conta), gerado e trocado no painel. Administradores: a definir |
| D13 | Orçamento mensal de infraestrutura | Hospedagem | Começar em planos gratuitos/baixos e escalar só nos dias críticos | ✅ **Gratuito**: Vercel + Render + Aiven + Gmail + UptimeRobot. Ver [hospedagem](06-hospedagem-gratuita.md) |
| D14 | Identidade visual (logo EVENTMER, cores) e identidade do CANTEMOS na página do evento | Design system | — | ✅ **Tema escuro "neon mint"** (fonte Sora, verde-menta `#36EDB3` como única cor de ação) — ver [design system](07-design-system.md). Logo: a definir |
| D15 | Aceitar inscrições **acima de 120** para compensar faltas (evento gratuito costuma ter 20–40% de no-show)? | TKT-06, lotação do templo | Abrir 120 + lista de espera; em 16/11 pedir cancelamento de quem não vai e chamar a lista. Margem extra só se o templo comportar pessoas em pé ou em espaço anexo | ✅ **Sim, com margem configurável** — padrão 20% (144 inscrições). ⚠️ Definir o plano para quem ficar sem lugar sentado se todos vierem (cadeiras extras, anexo, telão) |
| D16 | Quantos lugares ficam **reservados** para família do coral, equipe e convidados (fora da inscrição pública)? | TKT-01, TKT-08 | Cota fixa emitida pela secretaria antes de abrir ao público | ✅ **Cotas personalizadas no painel** (nome e quantidade livres, ex.: "Família do coral: 15"). Começa sem cotas |
