# 06 · Hospedagem gratuita (CANTEMOS 2026)

Decisão D13: começar **sem custo**. Esta é a configuração recomendada e o passo a passo para colocar o EVENTMER no ar.

| Peça | Serviço (plano gratuito) | Observações |
|---|---|---|
| Site (Next.js) | **Vercel — Hobby** | Uso não comercial (evento gratuito de igreja se enquadra). Endereço `*.vercel.app` |
| API (FastAPI) | **Render — Free** | "Dorme" após 15 min sem acesso e leva ~1 min para acordar → resolvido com monitor de uptime (abaixo). **Bloqueia SMTP**, por isso o e-mail sai pela API do Gmail |
| Banco MySQL 8 | **Aiven for MySQL — Free** | 1 CPU, 1 GB RAM, 1 GB de disco — sobra para o CANTEMOS. Conexão com SSL |
| E-mail | **Conta Gmail + API do Gmail** | Limite de ~500 e-mails/dia na conta gratuita: suficiente para 150 inscrições + lembretes |
| Monitor | **UptimeRobot — Free** | Acessa a API a cada 5 min (mantém acordada e avisa se cair) |

> Os planos gratuitos mudam com frequência. Confira os limites atuais em cada site antes de criar as contas.

## Contas a criar

Recomendado: **uma conta Gmail exclusiva da igreja** para o evento (ex.: `cantemos.<igreja>@gmail.com`). Use-a para criar todas as contas abaixo — assim nada fica preso ao e-mail pessoal de alguém.

---

## Passo 1 — Banco de dados (Aiven)

1. Crie a conta em aiven.io e um serviço **MySQL** no plano **Free**.
2. Na página do serviço, copie **Host, Port, User, Password, Database** e baixe o **CA certificate**.
3. Monte a URL de conexão:

   ```
   mysql+pymysql://USUARIO:SENHA@HOST:PORTA/defaultdb?charset=utf8mb4
   ```

4. Do seu computador (no diretório `backend/`, com o `.env` apontando para o Aiven: `DATABASE_URL` e `DATABASE_SSL_CA` com o conteúdo do certificado), crie as tabelas, o primeiro administrador e o evento:

   ```bash
   alembic upgrade head
   ```

   ```bash
   python -m app.cli create-admin --email voce@exemplo.com --name "Seu Nome" --role owner
   ```

   ```bash
   python -m app.cli seed-cantemos
   ```

   O evento nasce com 19/11/2026 às **18h30** (portas às 18h00), **120 lugares + 20% de margem = 144 inscrições**, **até 5 ingressos por inscrição** e **10 lugares de prioridade**. Tudo isso, e as cotas reservadas, é ajustável depois no painel → *Configurações*.

## Passo 2 — E-mail (Gmail via API)

Por que API e não senha de app: o Render gratuito bloqueia as portas SMTP (25/465/587) desde set/2025. A API do Gmail usa HTTPS e funciona.

1. Entre em console.cloud.google.com com a conta Gmail do evento e crie um projeto (ex.: `eventmer`). Não precisa de cartão.
2. **APIs e serviços → Biblioteca →** ative a **Gmail API**.
3. **Tela de consentimento OAuth:** tipo *Externo*, nome `EVENTMER`, e-mail de suporte = a conta do evento. Adicione o escopo `https://www.googleapis.com/auth/gmail.send`.
4. **Publique o app** ("Publicar aplicativo" → *Em produção*). ⚠️ Se ficar em *Teste*, o token expira em 7 dias e os e-mails param de sair no meio das inscrições. O Google mostrará o aviso "app não verificado" na autorização — é esperado, porque só a própria conta do evento vai autorizar.
5. **Credenciais → Criar credenciais → ID do cliente OAuth →** *Aplicativo da Web*. Em *URIs de redirecionamento autorizados*, adicione `https://developers.google.com/oauthplayground`. Guarde o **Client ID** e o **Client Secret**.
6. Abra developers.google.com/oauthplayground:
   - Na engrenagem ⚙️, marque **Use your own OAuth credentials** e cole Client ID e Client Secret.
   - No passo 1, digite o escopo `https://www.googleapis.com/auth/gmail.send` e clique *Authorize APIs*; entre com a **conta do evento** e aceite.
   - No passo 2, clique *Exchange authorization code for tokens* e copie o **Refresh token**.
7. Teste do seu computador (no `.env`: `EMAIL_BACKEND=gmail_api`, `EMAIL_FROM_ADDRESS`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`):

   ```bash
   python -m app.cli send-test-email --to seu-email@exemplo.com
   ```

## Passo 3 — API (Render)

1. Crie a conta em render.com conectando o GitHub e autorize o repositório.
2. **New → Blueprint →** escolha o repositório. O arquivo `render.yaml` já define o serviço `eventmer-api` (plano free, Docker, health check, segredos JWT/QR gerados automaticamente).
3. Preencha as variáveis pedidas:

   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | URL do Passo 1 |
   | `DATABASE_SSL_CA` | conteúdo completo do CA certificate do Aiven |
   | `EMAIL_FROM_ADDRESS` | Gmail do evento |
   | `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` | do Passo 2 |
   | `FRONTEND_URL` e `CORS_ORIGINS` | endereço do Vercel (Passo 4), ex.: `https://cantemos.vercel.app` |

4. Ao subir, a API aplica as migrations sozinha. Confira em `https://<seu-servico>.onrender.com/api/v1/health` → `{"status":"ok"}`.

## Passo 4 — Site (Vercel)

1. Crie a conta em vercel.com com o GitHub → **Add New → Project →** importe o repositório.
2. **Root Directory:** `frontend`. Framework: Next.js (detectado).
3. Variável de ambiente: `BACKEND_URL = https://<seu-servico>.onrender.com`.
4. Em *Settings → Domains*, escolha o endereço (ex.: `cantemos.vercel.app`) e volte ao Render para colocá-lo em `FRONTEND_URL` e `CORS_ORIGINS`.

## Passo 5 — Monitor (UptimeRobot)

1. Crie a conta em uptimerobot.com → **Add New Monitor →** HTTP(s).
2. URL: `https://<seu-servico>.onrender.com/api/v1/health`, intervalo **5 minutos**.
3. Alerta por e-mail (e app no celular) para a equipe técnica.

Isso mantém a API acordada (o plano gratuito do Render dá horas suficientes para um serviço ligado o mês todo) e avisa se algo cair.

---

## Limites e riscos do plano gratuito

| Risco | Impacto | Mitigação |
|---|---|---|
| API dormindo | 1º acesso demora ~1 min | UptimeRobot a cada 5 min |
| Limite de e-mails do Gmail (~500/dia) | Com 144 inscrições, folgado. Envio em massa precisa ser espaçado | Lembretes enviados em lotes; ingresso também fica na tela de confirmação |
| Instância pequena (pouca CPU/RAM) | Abertura das inscrições com muita gente ao mesmo tempo pode ficar lenta | Teste de carga antes de 09/11. **Opcional:** subir o Render para o plano pago (~US$ 7) só em novembro e voltar ao gratuito depois |
| Backups do banco gratuito são limitados | Perda de dados em incidente | Exportação manual (`mysqldump`) diária durante as inscrições e na véspera do evento |
| Sem domínio próprio | Endereço `*.vercel.app` | Suficiente para 2026; domínio próprio fica para depois (D2) |
