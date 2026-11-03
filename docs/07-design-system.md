# Design System — tema escuro "neon mint" (cor de ação: laranja, ver §7)

> Instrução para o Claude Code: use **sempre** os tokens de `tokens.css`. Nunca escreva cores, fontes, raios ou sombras "soltos" no código — referencie as variáveis CSS.

## 1. Conceito
Interface escura, quase preta, com **um único verde-menta neon** como cor de ação. Tipografia geométrica (Sora), títulos grandes porém **leves (peso 400)**, textos de apoio em verde-acinzentado e muito respiro. Acentos pastel só para categorizar.

## 2. Regras de uso
| Caixinha | Regra |
|---|---|
| **Fundo** | `--bg-base` (preto) + `--bg-glow` no topo. Seções alternam `--bg-surface-1`; cards em `--bg-surface-2`. |
| **Cor de ação** | `--brand` apenas em CTAs, links ativos, eyebrows e indicadores. Nunca em grandes áreas. |
| **Botão primário** | `--brand-gradient`, texto `--on-brand`, MAIÚSCULO, peso 700, raio 9px. Glow verde só no hover. |
| **Títulos** | Display 54/56px peso 400 em branco puro. Títulos de card 17px peso 600, tracking negativo. |
| **Texto corrido** | 16px, line-height 1.85, cor `--text-muted`. |
| **Labels/eyebrows** | 11px, peso 700, maiúsculo, espaçado, em `--brand`. |
| **Cards** | Fundo `--bg-surface-2`, borda `--border-subtle`, raio 12px, fio de luz interno no topo + sombra `--shadow-md`. |
| **Categorias** | Cada categoria = uma cor de acento (`.tag--*`): texto na cor cheia, fundo a 4%. |
| **Divisores** | Faixas `--stripe-bronze` / `--stripe-forest` com 1–2px de altura. |

## 3. Escalas
- **Tipo:** 54 · 48 · 28 · 17 · 16 · 14 · 12 · 11 · 9 px
- **Pesos:** 400 · 500 · 600 · 700 · 800
- **Raios:** 3 · 5 · 8 · 9 · 12 px · 50% (avatares/ícones)
- **Espaçamento sugerido:** base 4px → 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96

## 4. Tailwind (opcional)
```js
// tailwind.config.js → theme.extend
colors: {
  bg: { base:'#000', s1:'#020907', s2:'#0B0D0E', s3:'#08110F' },
  brand: { DEFAULT:'#36EDB3', light:'#8AF7D3', dark:'#29DBA4', on:'#020706' },
  ink: { strong:'#FFF', DEFAULT:'#F3F8F6', soft:'#DBE6DC', muted:'#9EB4A9', subtle:'#A0AAA4' },
  accent: { lavender:'#BDA7FF', lime:'#A9E486', peach:'#EDBB95', violet:'#C69CF2', mint:'#92E4BD', sand:'#F0D5AA' },
},
fontFamily: { sans: ['Sora','Arial','sans-serif'] },
borderRadius: { btn:'9px', card:'12px' },
```

## 5. Fora do escopo
Logotipos, nome de marca, imagens, ícones e textos do site de referência **não** foram copiados. Use os ativos da sua própria marca.

## 6. Como está aplicado no EVENTMER
- **Fonte da verdade:** `frontend/styles/tokens.css` (importado em `app/layout.tsx`). A fonte Sora é servida pelo próprio site (`@fontsource-variable/sora`), não pelo Google Fonts.
- **Tailwind:** `frontend/tailwind.config.ts` só referencia tokens. Os canais RGB usados para opacidade (`bg-primary/10`) ficam em `app/globals.css` — ao mudar uma cor em `tokens.css`, atualize o canal correspondente.
- **Nomes no Tailwind:** `bg` (fundo), `surface` / `surface-1` / `surface-3`, `strong` / `fg` / `soft` / `muted` / `subtle` (texto), `primary` (marca; `bg-brand` = gradiente), `border` / `border-subtle`, `line` (base das bordas com opacidade), `shadow-card`, `shadow-cta`, `rounded-xl` = 9px (botões/campos), `rounded-2xl` = 12px (cartões). Classes prontas: `.eyebrow`, `.title-display`, `.text-body`, `.divider-forest`.
- **Exceções deliberadas:**
  - *Estados* (`success` = cor da marca, `warning` âmbar, `danger` vermelho) — usados na tela de leitura da recepção e em alertas, onde a cor precisa ser entendida à distância.
  - *QR Codes* sempre em fundo branco (leitura pela câmera).
  - *E-mails* repetem os valores dos tokens em estilo inline (clientes de e-mail não aceitam variáveis CSS) — `backend/app/modules/tickets/emails.py` e `backend/app/modules/waitlist/service.py`.
  - *Impressão* (lista de presença): `@media print` troca os canais para papel branco e texto preto.

## 7. Alteração: cor de ação laranja (03/11/2026)
A coordenação trocou o verde-menta por **laranja** em botões e destaques. Tudo o que o documento acima chama de "verde-menta" / `--brand` passa a ser:

| Token | Antes | Agora |
|---|---|---|
| `--brand` | `#36EDB3` | `#FF8A3D` |
| `--brand-light` | `#8AF7D3` | `#FFB37A` |
| `--brand-dark` | `#29DBA4` | `#F26B1D` |
| `--on-brand` | `#020706` | `#1A0B02` |
| `--brand-gradient` | menta | `linear-gradient(115deg, #FFB37A, #FF8A3D 48%, #F26B1D)` |
| `--glow-brand`, `--bg-glow`, `--border-brand` | menta | mesmo laranja com a mesma opacidade |

- O estado de **sucesso** deixou de usar a cor da marca e passou a verde (`#22C55E`), para "entrada liberada" não se confundir com o âmbar de "já entrou".
- O divisor da página do evento usa `--stripe-bronze`, que combina com o laranja.
- Superfícies, textos e bordas continuam os da referência.

## 8. Logos (enviados pelo painel)
- **Logo do evento:** painel → evento → *Configurações* → "Logo do evento". Aparece no lugar do título na página do evento, na página inicial, nos ingressos, na recepção e no topo do e-mail.
- **Logo e nome da igreja:** painel → *Igreja*. Aparecem no rodapé "Realização" das páginas públicas, no e-mail e nas páginas de Privacidade/Termos.
- **Formatos:** PNG, JPG, WEBP ou SVG, até 1 MB, de preferência com fundo transparente e cores pensadas para fundo escuro. O e-mail só exibe PNG/JPG (SVG fica de fora do e-mail).
- As imagens ficam no banco de dados (tabela `assets`), porque a hospedagem gratuita apaga arquivos do disco a cada atualização.
