# 01 · Benchmark de mercado

Objetivo: entender o que as principais plataformas de eventos oferecem, decidir o que o EVENTMER precisa copiar, o que pode ignorar e **onde estão as lacunas** que nenhuma delas resolve bem para o nosso caso (evento de igreja, gratuito ou de baixo custo, público familiar, várias sessões).

> Levantamento feito a partir das funcionalidades divulgadas publicamente por cada plataforma. Antes de cada fase vale revisar a plataforma de referência daquele módulo, porque os recursos mudam com frequência.

---

## 1. Visão geral das plataformas

### Sympla — referência principal
Líder no Brasil para eventos B2C (festas, shows, eventos culturais, feiras, cursos).
- **Criação rápida** de página do evento, com descrição, mapa, imagens e política de cancelamento.
- **Ingressos em lotes** (virada automática por data ou quantidade), ingressos gratuitos e pagos, meia-entrada, cupons de desconto e ingressos ocultos por código.
- **Formulário de inscrição personalizável** (perguntas por participante).
- **Pagamento** por cartão, PIX e boleto, com repasse ao produtor e taxa de serviço configurável (absorvida pelo produtor ou repassada ao comprador).
- **App de check-in** para a equipe, com leitura de QR Code, busca por nome e funcionamento offline.
- **Painel em tempo real** de vendas e check-ins, exportação de participantes, e-mails para inscritos.
- **Transferência de titularidade** do ingresso e cancelamento/reembolso dentro da política.
- Descoberta de eventos (marketplace) e área "Meus ingressos" para o comprador.

**O que levamos:** fluxo de criação de evento, lotes, formulário customizado, app de check-in offline, painel em tempo real, área do participante.

### Ticketmaster
Grandes shows internacionais, musicais e espetáculos em estádios e arenas.
- **Mapa de assentos** interativo com setores e preços por setor.
- **Fila virtual** para picos de acesso na abertura de vendas.
- **Ingresso digital dinâmico** (QR/código que muda periodicamente) para combater print e revenda.
- Limite de ingressos por CPF/conta, revenda oficial, transferência pelo app.

**O que levamos:** a ideia de **proteção contra pico** (abertura de inscrições do CANTEMOS gera corrida) e de **limite por pessoa**. Mapa de assentos fica para depois.

### Eventim
Grandes shows, festivais e eventos esportivos.
- Vendas com **pré-venda** para grupos (clientes de banco, fã-clubes) via código.
- Mapa de lugares, entrega de ingresso digital e retirada em bilheteria.
- Venda em pontos físicos (bilheteria / PDV).

**O que levamos:** **pré-venda / janela exclusiva por código** — útil para dar prioridade a membros, coral e convidados antes da abertura ao público.

### Ingresse
Festas, festivais de música eletrônica, blocos e entretenimento jovem.
- **Transferência de ingresso** entre amigos pelo app de forma simples.
- **Promoters / links de divulgação** com rastreamento de vendas por promoter.
- Ingresso no app, PIX, pagamento parcelado.

**O que levamos:** **links rastreáveis de divulgação** (saber de qual igreja, célula ou rede social veio cada inscrição) e transferência simples.

### Fever
Experiências imersivas, concertos Candlelight, eventos culturais urbanos.
- **Várias sessões/horários** para a mesma experiência, com lotação por sessão.
- **Lista de espera** quando a sessão esgota.
- Curadoria e descoberta personalizada, avaliações pós-evento.

**O que levamos:** **modelo de evento com várias sessões** (exatamente o que a cantata precisa) e **lista de espera**. Pesquisa de satisfação pós-evento.

### Eventbrite
Eventos de diversos portes, forte em ferramentas de gestão.
- **Organizer app** com check-in, venda na porta e estatísticas.
- **E-mail marketing** para a base de participantes.
- Eventos recorrentes, formulários de inscrição detalhados, códigos de acesso, integrações (API, webhooks, Zapier).
- Equipe com **permissões por papel**.

**O que levamos:** **papéis e permissões** da equipe (administrador x recepção), comunicação com os inscritos, eventos recorrentes (o CANTEMOS acontece todo ano).

### Doity / Even3
Eventos acadêmicos e corporativos (congressos, simpósios, palestras).
- **Inscrição por categoria** (estudante, profissional etc.) com preços diferentes.
- **Programação com atividades** e check-in por atividade.
- **Credenciamento com impressão de etiquetas/crachás** no local.
- **Certificados** automáticos por presença.
- Submissão e avaliação de trabalhos.

**O que levamos:** **credenciamento presencial** (busca rápida por nome, impressão de etiqueta para equipe e coral), categorias de inscrição, check-in por sessão. Certificados e submissão de trabalhos ficam fora.

---

## 2. Matriz de funcionalidades

Legenda: ✅ oferece · ➖ parcial/limitado · ❌ não oferece ou não é o foco · **Fase** = quando entra no EVENTMER (ver [roadmap](03-roadmap.md)).

| Funcionalidade | Sympla | Ticketmaster | Eventim | Ingresse | Fever | Eventbrite | Doity/Even3 | **EVENTMER** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Página pública do evento | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** |
| Várias sessões por evento | ✅ | ✅ | ✅ | ➖ | ✅ | ✅ | ➖ | **F1** |
| Ingresso gratuito com inscrição | ✅ | ❌ | ❌ | ✅ | ➖ | ✅ | ✅ | **F1** |
| Inscrição de vários participantes no mesmo pedido | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ➖ | **F1** |
| Formulário de inscrição personalizado | ✅ | ❌ | ❌ | ➖ | ❌ | ✅ | ✅ | **F2** |
| Ingresso com QR Code por e-mail | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** |
| Área "Meus ingressos" | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** |
| Check-in por QR (celular/tablet) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** |
| Check-in offline | ✅ | ✅ | ✅ | ➖ | ➖ | ✅ | ➖ | **F2** |
| Busca manual por nome/CPF na portaria | ✅ | ➖ | ➖ | ➖ | ➖ | ✅ | ✅ | **F1** |
| Painel em tempo real | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** |
| Papéis da equipe (admin / recepção) | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | ✅ | **F1** |
| Lista de espera | ➖ | ➖ | ❌ | ❌ | ✅ | ✅ | ➖ | **F2** |
| Cancelamento pelo participante | ✅ | ➖ | ➖ | ✅ | ➖ | ✅ | ✅ | **F1** |
| Transferência de titularidade | ✅ | ✅ | ➖ | ✅ | ❌ | ➖ | ➖ | **F2** |
| Lotes / virada automática | ✅ | ➖ | ➖ | ✅ | ➖ | ✅ | ✅ | **F3** |
| Cupons e códigos de acesso / pré-venda | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | ✅ | **F2** (código) / **F3** (cupom) |
| Pagamento PIX / cartão | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F3** |
| Reembolso automatizado | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F3** |
| Links rastreáveis / promoters | ➖ | ❌ | ❌ | ✅ | ❌ | ✅ | ➖ | **F2** |
| E-mails e lembretes aos inscritos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **F1** (transacional) / **F2** (lembretes) |
| WhatsApp | ➖ | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | **F2** (link) / **F4** (API) |
| Ingresso na carteira (Apple/Google Wallet) | ➖ | ✅ | ✅ | ➖ | ✅ | ✅ | ❌ | **F4** |
| Mapa de assentos | ➖ | ✅ | ✅ | ➖ | ➖ | ✅ | ❌ | **F4** |
| Fila virtual para pico | ➖ | ✅ | ✅ | ➖ | ➖ | ➖ | ❌ | **F2** (controle de concorrência) / **F4** (fila) |
| QR dinâmico antifraude | ❌ | ✅ | ➖ | ➖ | ❌ | ❌ | ❌ | **F4** |
| Impressão de crachá/etiqueta | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | **F4** |
| Pesquisa pós-evento | ➖ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | **F4** |
| Certificados | ➖ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | Não faremos |
| Submissão de trabalhos | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | Não faremos |
| Marketplace / descoberta de eventos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ➖ | Não faremos |
| Revenda secundária | ➖ | ✅ | ➖ | ➖ | ❌ | ❌ | ❌ | Não faremos |

---

## 3. Lacunas: o que o CANTEMOS precisa e o mercado não resolve bem

Essas são as funcionalidades que justificam ter uma plataforma própria em vez de usar o Sympla. Estão marcadas como **diferenciais** no [escopo](02-escopo.md).

| # | Lacuna | Por que importa para nós | Fase |
|---|---|---|---|
| L1 | **Inscrição familiar com dependentes** — uma pessoa responsável inscreve cônjuge, filhos e idosos sem precisar de e-mail de cada um | O público da cantata vem em família; exigir e-mail por pessoa trava a inscrição | F1 |
| L2 | **Controle de no-show em evento gratuito** — confirmação de presença ("ainda vai?") dias antes e liberação automática das vagas não confirmadas para a lista de espera | Evento gratuito tem alta taxa de falta; teatro lotado na plataforma e vazio no dia | F2 |
| L3 | **Caravanas / grupos de outras igrejas** — um líder reserva um bloco de lugares e depois nomeia os participantes | Igrejas convidadas vêm em ônibus; hoje isso é feito por planilha | F2 |
| L4 | **Pré-venda para membros, coral e convidados** por código ou lista, antes da abertura ao público | Garante lugar para família do elenco e voluntários | F2 |
| L5 | **Acessibilidade e prioridades** — reserva de lugares PCD, idosos, gestantes e cadeirantes, marcados no ingresso e visíveis na portaria | Recepção precisa saber quem conduzir para onde | F1 (marcação) / F4 (assento) |
| L6 | **Contagem de lotação ao vivo por sessão e por porta** | Segurança do templo e decisão de abrir espaço extra (telão, anexo) | F1 |
| L7 | **Zero taxa para eventos gratuitos e contribuição voluntária opcional** (oferta/doação no fim da inscrição) | Plataformas comerciais cobram ou não oferecem doação integrada | F3 |
| L8 | **Gestão de voluntários de recepção** — login simples, sem acesso a dados sensíveis, escala por porta/sessão | Recepcionistas mudam a cada sessão e não devem ver relatórios | F1 (papel) / F4 (escala) |
| L9 | **Credenciamento da equipe interna** (coral, músicos, técnicos, voluntários) com crachá e controle de acesso aos bastidores | Mesma ferramenta para público e equipe | F4 |
| L10 | **Edição anual (recorrência)** — duplicar o CANTEMOS do ano anterior com sessões, ingressos e equipe, mantendo o histórico de público | Evento acontece todo ano | F2 |
| L11 | **Origem da inscrição** — de qual igreja, célula, rede social ou convite a pessoa veio | Medir o alcance evangelístico da cantata | F2 |
| L12 | **Comunicação por WhatsApp** — é o canal que nosso público realmente lê | E-mail tem baixa abertura nesse público | F2 / F4 |
