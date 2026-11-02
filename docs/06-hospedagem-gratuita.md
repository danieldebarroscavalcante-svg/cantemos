# 06 · Hospedagem gratuita (CANTEMOS 2026)

Decisão D13: começar **sem custo**. Tudo é feito pelo navegador, sem instalar nada no computador. Tempo estimado: **1h30 a 2h**.

| Peça | Serviço (plano gratuito) | Observações |
|---|---|---|
| Site (Next.js) | **Vercel — Hobby** | Uso não comercial (evento gratuito de igreja se enquadra). Endereço `*.vercel.app` |
| API (FastAPI) | **Render — Free** | "Dorme" após 15 min sem acesso → resolvido com o monitor. **Bloqueia SMTP**, por isso o e-mail sai pela API do Gmail |
| Banco MySQL 8 | **Aiven for MySQL — Free** | 1 GB de disco — sobra para o CANTEMOS |
| E-mail | **Gmail + API do Gmail** | ~500 e-mails/dia: suficiente para 144 inscrições + lembretes |
| Monitor | **UptimeRobot — Free** | Acessa a API a cada 5 min (mantém acordada e avisa se cair) |

> Os planos gratuitos mudam com frequência; se alguma tela estiver diferente do descrito, o caminho geral é o mesmo.

## Antes de começar

- Tenha à mão um **bloco de notas privado** (ou gerenciador de senhas) para guardar os valores marcados com 📋. **Não envie esses valores por chat, e-mail ou WhatsApp** — eles dão acesso ao sistema.
- Use a **mesma conta Gmail do evento** para criar todas as contas, assim nada fica preso ao e-mail pessoal de ninguém.

---

## Passo 1 — Conta Gmail do evento (5 min)

1. Crie uma conta Gmail exclusiva, ex.: `cantemos.suaigreja@gmail.com`. É ela que vai **enviar os ingressos**, então escolha um nome que o público reconheça.
2. Ative a verificação em duas etapas (Conta Google → Segurança).

## Passo 2 — Liberar o envio de e-mails pelo Gmail (20 min)

1. Entre em **console.cloud.google.com** com a conta do evento e aceite os termos. Não precisa de cartão.
2. No topo, **Selecionar projeto → Novo projeto** → nome `eventmer` → Criar. Confirme que o projeto `eventmer` está selecionado.
3. Menu ☰ → **APIs e serviços → Biblioteca** → pesquise **Gmail API** → **Ativar**.
4. Menu ☰ → **APIs e serviços → Tela de permissão OAuth** (ou *Google Auth Platform*) → **Começar**:
   - Nome do app: `EVENTMER`; e-mail de suporte: a conta do evento.
   - Público: **Externo**.
   - Dados de contato: a conta do evento → concluir.
5. Em **Público** (*Audience*), clique **Publicar aplicativo** → confirmar, para o status ficar **Em produção**.
   ⚠️ Não pule: em modo *Teste* a autorização expira em 7 dias e os ingressos param de ser enviados no meio das inscrições.
6. Em **Clientes** (*Credenciais*) → **Criar cliente** (*ID do cliente OAuth*):
   - Tipo: **Aplicativo da Web**; nome: `eventmer`.
   - Em **URIs de redirecionamento autorizados**, adicione exatamente: `https://developers.google.com/oauthplayground`
   - Criar → copie 📋 **ID do cliente** e 📋 **Chave secreta do cliente**.
7. Abra **developers.google.com/oauthplayground**:
   - Clique na engrenagem ⚙️ (canto superior direito) → marque **Use your own OAuth credentials** → cole o ID e a chave secreta → feche.
   - À esquerda, no campo *Input your own scopes*, cole `https://www.googleapis.com/auth/gmail.send` → **Authorize APIs**.
   - Entre com a **conta do evento**. Vai aparecer "O Google não verificou este app" → **Avançado → Acessar eventmer (não seguro)** → **Continuar**. É esperado: o app é seu e só a sua conta vai usá-lo.
   - De volta ao Playground, clique **Exchange authorization code for tokens** → copie 📋 o **Refresh token**.

## Passo 3 — Banco de dados (Aiven) (10 min)

1. Crie a conta em **aiven.io** (pode entrar com a conta Google do evento).
2. **Create service → MySQL** → plano **Free** → região mais próxima disponível → nome `eventmer-db` → Create.
3. Aguarde o status ficar **Running** (alguns minutos).
4. Na aba **Overview / Connection information**:
   - Copie 📋 a **Service URI** (começa com `mysql://avnadmin:...`). Pode copiar como está.
   - Em **CA certificate**, clique para mostrar/baixar e copie 📋 **todo o texto**, de `-----BEGIN CERTIFICATE-----` até `-----END CERTIFICATE-----`.

## Passo 4 — API no Render (15 min)

1. Crie a conta em **render.com** com **GitHub** e autorize o acesso ao repositório `cantemos`.
2. **New → Blueprint** → escolha o repositório `cantemos` → nome do blueprint `eventmer`.
3. O Render lê o arquivo `render.yaml` e pede estas variáveis:

   | Variável | O que colocar |
   |---|---|
   | `ORGANIZATION_NAME` | Nome da igreja (ex.: `Igreja Batista Central`) |
   | `BOOTSTRAP_ADMIN_EMAIL` | **Seu** e-mail de login no painel |
   | `BOOTSTRAP_ADMIN_NAME` | Seu nome |
   | `BOOTSTRAP_ADMIN_PASSWORD` | Uma senha forte (mín. 8 caracteres) para entrar no painel 📋 |
   | `DATABASE_URL` | Service URI do Passo 3 |
   | `DATABASE_SSL_CA` | Texto completo do CA certificate do Passo 3 |
   | `EMAIL_FROM_ADDRESS` | Gmail do evento (Passo 1) |
   | `GMAIL_CLIENT_ID` | ID do cliente (Passo 2) |
   | `GMAIL_CLIENT_SECRET` | Chave secreta do cliente (Passo 2) |
   | `GMAIL_REFRESH_TOKEN` | Refresh token (Passo 2) |
   | `FRONTEND_URL` | Por enquanto `https://example.com` — será trocado no Passo 6 |

4. **Apply / Deploy**. O primeiro deploy leva de 5 a 10 minutos. Ao subir, a API cria as tabelas, **o seu usuário administrador** e **o evento CANTEMOS 2026** sozinha.
5. Copie 📋 o endereço do serviço (ex.: `https://eventmer-api.onrender.com`) e abra `<endereço>/api/v1/health` no navegador. Deve aparecer `{"status":"ok"}`.

## Passo 5 — Site na Vercel (10 min)

1. Crie a conta em **vercel.com** com **GitHub** (plano *Hobby*) e autorize o repositório `cantemos`.
2. **Add New → Project** → importe `cantemos`.
3. **Root Directory:** clique *Edit* e escolha `frontend`. Framework: Next.js (detectado sozinho).
4. **Environment Variables:** `BACKEND_URL` = endereço do Render do Passo 4 (sem `/` no final).
5. **Deploy**.
6. Em **Settings → Domains**, edite o endereço para algo como `cantemos2026.vercel.app` (se estiver livre). Copie 📋 o endereço final.

## Passo 6 — Ligar o site à API (2 min)

No Render → serviço `eventmer-api` → **Environment** → troque `FRONTEND_URL` pelo endereço da Vercel (ex.: `https://cantemos2026.vercel.app`) → **Save changes** (o serviço reinicia sozinho).

## Passo 7 — Monitor (UptimeRobot) (5 min)

1. Crie a conta em **uptimerobot.com**.
2. **New monitor** → tipo **HTTP(s)** → URL: `<endereço do Render>/api/v1/health` → intervalo **5 minutos** → Create.
3. Em *Alert contacts*, mantenha o e-mail e, se quiser, instale o app no celular para receber alertas.

## Passo 8 — Conferir tudo pelo celular (5 min)

1. Abra o endereço da Vercel no celular → **Entrar no painel** → entre com o e-mail e a senha do Passo 4.
2. No painel, clique **Enviar e-mail de teste** e confira se chegou (olhe também o spam e marque como "Não é spam" se for o caso).
3. Abra **Configurações** do CANTEMOS 2026 e confira: 19/11 às 18h30, portas às 18h00, 120 lugares, margem 20%, até 5 por inscrição, prioridade 10. Ajuste o que precisar e crie as cotas reservadas.
4. Opcional: no menu do navegador, **Adicionar à tela inicial** para abrir o painel como um app.
5. Por segurança, depois do primeiro login, apague `BOOTSTRAP_ADMIN_PASSWORD` no Render (Environment). Seu usuário continua existindo; a variável só é usada na criação.

## Passo 9 — Avisar o desenvolvimento

Envie apenas: **o endereço do site**, **o endereço da API** e o resultado do e-mail de teste. **Nunca** envie senhas, chaves ou tokens.

---

## Problemas comuns

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| Deploy do Render falha com erro de conexão ao banco | `DATABASE_URL` ou `DATABASE_SSL_CA` incompletos | Copie de novo a Service URI e o certificado inteiro (com as linhas BEGIN/END) |
| Login diz "E-mail ou senha incorretos" | Senha diferente da `BOOTSTRAP_ADMIN_PASSWORD` do primeiro deploy | A senha é definida só no primeiro deploy; peça ao desenvolvimento para redefinir |
| E-mail de teste: "Falha ao renovar o token do Gmail" | App em modo *Teste*, refresh token errado, ou ID/chave trocados | Confira o Passo 2.5 (Em produção) e gere um novo refresh token (Passo 2.7) |
| Site abre mas o login fica girando ~1 min | API estava dormindo | Normal só no primeiro acesso; com o monitor (Passo 7) deixa de acontecer |

## Limites e riscos do plano gratuito

| Risco | Impacto | Mitigação |
|---|---|---|
| API dormindo | 1º acesso demora ~1 min | UptimeRobot a cada 5 min |
| Limite de e-mails do Gmail (~500/dia) | Folgado para 144 inscrições. Envio em massa precisa ser espaçado | Lembretes em lotes; ingresso também fica na tela de confirmação |
| Instância pequena (pouca CPU/RAM) | Abertura das inscrições com muita gente ao mesmo tempo pode ficar lenta | Teste de carga antes de 09/11. **Opcional:** plano pago do Render (~US$ 7) só em novembro |
| Backups do banco gratuito são limitados | Perda de dados em incidente | Exportação diária durante as inscrições e na véspera do evento |
| Sem domínio próprio | Endereço `*.vercel.app` | Suficiente para 2026; domínio próprio depois (D2) |
| Publicação automática a cada atualização do código | Uma mudança com erro iria direto para o ar | Criar a branch `main` como versão de produção antes do *code freeze* (16/11) |
