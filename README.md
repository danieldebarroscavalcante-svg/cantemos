# EVENTMER

> Plataforma de eventos com foco em **inscrição, emissão de ingressos e credenciamento** — online, responsiva e pensada para funcionar bem no celular e no tablet.

O primeiro caso de uso real é o **CANTEMOS**, a cantata de final de ano da nossa igreja: uma história contada em música, com várias apresentações, público familiar e grande procura por lugares. Tudo o que construirmos precisa resolver bem esse cenário antes de crescer para outros eventos.

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

## Estrutura do repositório

```
.
├── backend/              # API FastAPI (Python)
├── frontend/             # App Next.js 14 (Organizador + Participante)
├── docs/                 # Documentação de produto e técnica
├── docker-compose.yml    # MySQL 8 para desenvolvimento local
└── README.md
```

> A aplicação ainda não foi gerada: o scaffolding do Next.js e do FastAPI é a primeira entrega da **Fase 0** do [roadmap](docs/03-roadmap.md).

## Ambiente local (prévia)

Subir o banco de dados de desenvolvimento:

```bash
docker compose up -d mysql
```
