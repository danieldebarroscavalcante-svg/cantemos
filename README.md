# EVENTMER

> Plataforma de eventos com foco em **inscrição, emissão de ingressos e credenciamento** — online, responsiva e pensada para funcionar bem no celular e no tablet.

O primeiro caso de uso real é o **CANTEMOS**, a cantata de final de ano da nossa igreja: uma história contada em música, com várias apresentações, público familiar e grande procura por lugares. Tudo o que construirmos precisa resolver bem esse cenário antes de crescer para outros eventos.

> 📅 **CANTEMOS 2026 — quinta-feira, 19/11/2026, 18h30 · entrada gratuita · 120 lugares (+ margem configurável).** Inscrições previstas para abrir em 09/11. Cronograma no [Plano Express](docs/03-roadmap.md#plano-express--cantemos-2026-0211--1911).

---

## Duas versões, um só produto

| Versão | Para quem | O que faz |
|---|---|---|
| **Organizador** | Equipe da igreja (administradores, produção, voluntários de recepção) | Cria eventos e sessões, configura ingressos, acompanha inscrições em tempo real, faz o check-in pelo celular/tablet, exporta relatórios |
| **Participante** | Quem se inscreveu ou comprou ingresso | Faz a inscrição (com familiares), recebe o ingresso com QR Code, consulta, transfere ou cancela, recebe lembretes |

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React + Next.js 14 + Tailwind CSS |
| Backend | Python + FastAPI |
| Banco | MySQL 8.0 |
| Auth | JWT + bcrypt |

Detalhes, bibliotecas de apoio e decisões de infraestrutura: [`docs/04-arquitetura.md`](docs/04-arquitetura.md).

## Documentação

| # | Documento | Conteúdo |
|---|---|---|
| 01 | [Benchmark de mercado](docs/01-benchmark.md) | Estudo de Sympla, Ticketmaster, Eventim, Ingresse, Fever, Eventbrite, Doity e Even3, matriz de funcionalidades e lacunas |
| 02 | [Escopo](docs/02-escopo.md) | O que **faremos** e o que **não faremos**, personas, requisitos por módulo |
| 03 | [Roadmap](docs/03-roadmap.md) | Fases, entregas, critérios de pronto e marcos |
| 04 | [Arquitetura](docs/04-arquitetura.md) | Arquitetura, modelo de dados inicial, segurança, responsividade, hospedagem |
| 05 | [Decisões em aberto](docs/05-decisoes-em-aberto.md) | Perguntas que precisam de resposta da organização antes ou durante o desenvolvimento |
| 06 | [Hospedagem gratuita](docs/06-hospedagem-gratuita.md) | Vercel + Render + Aiven + Gmail: passo a passo para colocar no ar |
| 07 | [Design system](docs/07-design-system.md) | Tema escuro com cor de ação laranja: regras de uso; valores em `frontend/styles/tokens.css` |

## Estrutura do repositório

```
.
├── backend/              # API FastAPI (Python)
├── frontend/             # App Next.js 14 (Organizador + Participante)
├── docs/                 # Documentação de produto e técnica
├── .github/workflows/    # CI (lint, testes, migrations em MySQL 8, build)
├── docker-compose.yml    # MySQL 8 para desenvolvimento local
├── render.yaml           # Blueprint da API no Render (plano gratuito)
└── README.md
```

## Ambiente local

Subir o banco de dados de desenvolvimento:

```bash
docker compose up -d mysql
```

Depois siga [`backend/README.md`](backend/README.md) (API, migrations, criação do admin e do evento) e [`frontend/README.md`](frontend/README.md).

## Status

| Entrega | Situação |
|---|---|
| Fase 0: scaffolding, banco, migrations, CI, login da equipe (JWT + refresh rotativo) | ✅ |
| Configurações do evento no painel (horário, lotação, margem, limite por inscrição, prioridade, cotas reservadas) | ✅ |
| Envio de e-mail pelo Gmail (API) | ✅ |
| Deploy gratuito: site em https://cantemos-frontend.vercel.app (Vercel) · API em https://eventmer-api.onrender.com (Render) · MySQL Free (Aiven) | ✅ 02/11 |
| Publicar o app do Google (token de e-mail definitivo) | ⏳ antes de 09/11 |
| Página pública + inscrição familiar + ingresso com QR por e-mail | ✅ 03/11 |
| Meus ingressos (link do e-mail), cancelamento total ou por pessoa, reenvio do ingresso | ✅ 03/11 |
| Lista de espera com vaga guardada por 24 h, lembretes por e-mail (16/11 e 18/11) e números para a coordenação | ✅ 03/11 |
| Check-in: câmera (QR) e busca por nome, entrada da família, contador ao vivo, acesso de voluntários por código da recepção, lista de presença para imprimir, planilha CSV | ✅ 03/11 |
| Identidade visual (tema escuro, laranja) e logos personalizáveis: logo do evento e logo/nome da igreja enviados pelo painel | ✅ 03/11 |
| Identidade visual do evento (banner, nome, tema, logo), mensagens de e-mail editáveis com prévia em tempo real e novo layout dos e-mails | ✅ 03/11 |
| Favicon/ícone do app ("e" laranja) e edição de perfil (nome e troca de senha) | ✅ 03/11 |
