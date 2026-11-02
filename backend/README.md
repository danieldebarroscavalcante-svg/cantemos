# EVENTMER · Backend

**Python 3.12 + FastAPI**, SQLAlchemy 2, Alembic, Pydantic v2, MySQL 8, JWT + bcrypt.

API REST em `/api/v1`, documentada em `/docs` (OpenAPI) fora de produção.

## Rodando localmente

Na raiz do repositório, suba o MySQL:

```bash
docker compose up -d mysql
```

No diretório `backend/`:

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements-dev.txt
```

```bash
cp .env.example .env
```

```bash
alembic upgrade head
```

```bash
uvicorn app.main:app --reload
```

## Comandos administrativos

Criar o primeiro usuário da equipe (pede a senha no terminal):

```bash
python -m app.cli create-admin --email voce@igreja.org --name "Seu Nome" --role owner
```

Criar o evento CANTEMOS 2026 (rascunho, 120 lugares = 110 gerais + 10 prioridade):

```bash
python -m app.cli seed-cantemos
```

Horário, lotação e cota de prioridade podem ser ajustados por opção (`--help`).

## Qualidade

```bash
ruff check . && ruff format --check . && pytest -q
```

Os testes usam SQLite em memória; a CI também valida as migrations em MySQL 8.

## Estrutura

```
app/
├── main.py              # app FastAPI e rotas /api/v1
├── cli.py               # comandos administrativos
├── core/                # config, segurança (JWT, bcrypt, QR assinado), dependências
├── db/                  # base, sessão, tipos, registro de modelos
└── modules/
    ├── auth/            # login, refresh rotativo, logout, /me
    ├── organizations/   # organização e papéis (owner, admin, manager, checkin)
    ├── events/          # evento e sessões (lotação com contador)
    ├── tickets/         # tipos de ingresso, pedidos, ingressos
    └── checkin/         # histórico de check-ins
alembic/                 # migrations
tests/
```
