# EVENTMER · Frontend

React + **Next.js 14** (App Router, TypeScript) + **Tailwind CSS**. Mobile-first e instalável como PWA.

Um único app atende as três experiências:

- **Público**: página do evento e inscrição (`/e/[slug]`, em construção)
- **Participante**: "Meus ingressos" (`/meus-ingressos`, em construção)
- **Organizador / Recepção**: login (`/login`), painel (`/painel`) e check-in (`/checkin/[sessionId]`, em construção)

## Rodando localmente

Com o backend rodando em `http://localhost:8000`:

```bash
cp .env.example .env.local
```

```bash
npm install
```

```bash
npm run dev
```

O Next.js faz proxy de `/api/v1/*` para o `BACKEND_URL`. Assim o navegador fala só com um domínio e o cookie `httpOnly` de refresh funciona sem CORS. O access token fica apenas em memória.

## Qualidade

```bash
npm run lint && npm run typecheck && npm run build
```

## Design system

Cores definidas como tokens CSS em `app/globals.css` (tema claro e escuro) e expostas no Tailwind (`bg-primary`, `text-muted`, `border-border`…). As cores são provisórias até a definição da identidade visual (decisão D14). Componentes base ficam em `components/ui/`.
