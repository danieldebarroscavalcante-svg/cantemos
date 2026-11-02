# 02 · Escopo

Este documento define **o que o EVENTMER vai fazer e o que não vai fazer**. Ele é a referência para dizer "isso entra" ou "isso fica para depois" durante o desenvolvimento. Mudanças de escopo devem atualizar este arquivo.

---

## 1. Visão do produto

**EVENTMER** é uma plataforma web responsiva de eventos que cobre o ciclo completo **divulgar → inscrever/vender → comunicar → credenciar → analisar**, com excelência no **credenciamento** (entrada rápida, confiável e sem filas) e pensada para eventos comunitários e de igreja, começando pelo **CANTEMOS**.

### Princípios
1. **Mobile-first.** Participante usa o celular; equipe de recepção usa celular e tablet. Desktop é o caso secundário.
2. **O dia do evento não pode falhar.** Check-in tem que funcionar com internet ruim, com vários operadores ao mesmo tempo, e ter um plano B (busca por nome, lista impressa).
3. **Simples para quem não é técnico.** Voluntários de recepção aprendem a usar em 2 minutos.
4. **Dados mínimos e protegidos (LGPD).** Só pedimos o que usamos; CPF é opcional.
5. **Um caso real primeiro.** Tudo é validado contra o CANTEMOS antes de generalizar.

---

## 2. Personas e papéis

| Persona | Papel no sistema | Dispositivo principal | Necessidades |
|---|---|---|---|
| **Coordenação do evento** | `owner` / `admin` | Desktop e celular | Criar evento e sessões, definir lotação, acompanhar números, exportar listas, comunicar inscritos |
| **Produção / secretaria** | `manager` | Desktop | Editar inscrições, atender dúvidas, reenviar ingressos, gerenciar caravanas |
| **Voluntário de recepção** | `checkin` | Celular ou tablet | Ler QR, buscar por nome, ver se é PCD/prioridade, ver lotação. **Não** acessa relatórios nem dados completos |
| **Participante / responsável** | `attendee` | Celular | Inscrever-se com a família, receber e encontrar o ingresso fácil, cancelar se não puder ir |
| **Líder de caravana** | `attendee` com reserva de grupo | Celular | Reservar um bloco de lugares e nomear os participantes depois |

---

## 3. O que FAREMOS

Organizado por módulo. Cada item tem um código para ser citado em issues e PRs. A coluna **Fase** remete ao [roadmap](03-roadmap.md).

### 3.1 Contas e acesso (AUTH)
| Código | Requisito | Fase |
|---|---|:-:|
| AUTH-01 | Cadastro e login por e-mail e senha (bcrypt), sessão com JWT (access curto + refresh) | F1 |
| AUTH-02 | Recuperação de senha por e-mail | F1 |
| AUTH-03 | Inscrição sem criar senha (conta "leve" criada pelo e-mail; acesso posterior por link mágico) | F1 |
| AUTH-04 | Papéis por organização: `owner`, `admin`, `manager`, `checkin` | F1 |
| AUTH-05 | Convite de membros da equipe por e-mail | F1 |
| AUTH-06 | Login de recepção por código/PIN temporário por sessão (para voluntários sem conta) | F2 |
| AUTH-07 | Login social (Google) | F4 |

### 3.2 Eventos e sessões (EVT)
| Código | Requisito | Fase |
|---|---|:-:|
| EVT-01 | Criar/editar evento: nome, descrição, banner, local (endereço + mapa), classificação, política de cancelamento | F1 |
| EVT-02 | **Várias sessões** por evento (data, hora, lotação própria, portas de abertura) | F1 |
| EVT-03 | Status do evento: rascunho, publicado, inscrições abertas/encerradas, finalizado | F1 |
| EVT-04 | Página pública responsiva do evento com URL amigável (`/e/cantemos-2026`) | F1 |
| EVT-05 | Agendamento de abertura e encerramento das inscrições | F1 |
| EVT-06 | Duplicar evento (edição do ano seguinte) | F2 |
| EVT-07 | Personalização visual da página (cores, imagens, seções de programação, elenco, FAQ) | F4 |

### 3.3 Ingressos e inscrição (TKT)
| Código | Requisito | Fase |
|---|---|:-:|
| TKT-01 | Tipos de ingresso por sessão (ex.: Geral, PCD/Prioridade, Convidado), com quantidade e limite por pedido | F1 |
| TKT-02 | Ingresso **gratuito** com inscrição | F1 |
| TKT-03 | **Inscrição familiar**: um responsável inscreve vários participantes (nome + faixa etária), sem exigir e-mail de cada um | F1 |
| TKT-04 | Marcação de necessidade de acessibilidade/prioridade por participante | F1 |
| TKT-05 | Limite de ingressos por responsável/e-mail/CPF por evento | F1 |
| TKT-06 | **Controle de concorrência** para não vender acima da lotação na corrida de abertura | F1 |
| TKT-07 | Formulário de inscrição personalizado (perguntas por pedido ou por participante) | F2 |
| TKT-08 | Ingressos ocultos / pré-venda por **código de acesso** ou lista de e-mails | F2 |
| TKT-09 | **Lista de espera** por sessão com oferta automática quando vaga é liberada | F2 |
| TKT-10 | **Reserva de grupo/caravana** com nomeação posterior dos participantes e prazo | F2 |
| TKT-11 | Links de divulgação rastreáveis (origem da inscrição) | F2 |
| TKT-12 | Ingressos pagos com **lotes** e virada automática | F3 |
| TKT-13 | Cupons de desconto | F3 |
| TKT-14 | Contribuição voluntária / doação opcional na inscrição | F3 |
| TKT-15 | Mapa de assentos (lugares marcados) | F4 |

### 3.4 Pagamentos (PAY)
| Código | Requisito | Fase |
|---|---|:-:|
| PAY-01 | Integração com gateway nacional (Mercado Pago ou Asaas) — **PIX** e cartão | F3 |
| PAY-02 | Reserva temporária do ingresso enquanto o pagamento não é confirmado (expira em X minutos) | F3 |
| PAY-03 | Webhooks de confirmação e conciliação | F3 |
| PAY-04 | Reembolso total/parcial conforme política | F3 |
| PAY-05 | Relatório financeiro por evento (bruto, taxas, líquido) | F3 |

### 3.5 Área do participante (PART)
| Código | Requisito | Fase |
|---|---|:-:|
| PART-01 | "Meus ingressos": lista de pedidos e ingressos com QR Code, funcionando bem no celular | F1 |
| PART-02 | Ingresso por e-mail (QR no corpo + PDF) | F1 |
| PART-03 | Cancelar ingresso (libera a vaga) | F1 |
| PART-04 | Editar nomes dos participantes até X horas antes | F1 |
| PART-05 | **Confirmação de presença** ("ainda vai?") com liberação automática de quem não confirmar | F2 |
| PART-06 | Transferir ingresso para outra pessoa | F2 |
| PART-07 | Adicionar à carteira (Apple Wallet / Google Wallet) | F4 |
| PART-08 | Pesquisa de satisfação pós-evento | F4 |

### 3.6 Credenciamento / check-in (CHK) — **núcleo do produto**
| Código | Requisito | Fase |
|---|---|:-:|
| CHK-01 | Leitor de QR Code pela câmera do celular/tablet (web, sem app nativo) | F1 |
| CHK-02 | Feedback imediato e inequívoco: verde (válido), amarelo (já utilizado — mostra quando e por quem), vermelho (inválido / outra sessão / cancelado), com som e vibração | F1 |
| CHK-03 | Busca manual por nome, e-mail ou código do pedido | F1 |
| CHK-04 | Check-in de pedido inteiro (família) ou de participantes individuais | F1 |
| CHK-05 | Destaque visual de prioridade/PCD no resultado | F1 |
| CHK-06 | Contador de lotação ao vivo por sessão (presentes / inscritos / capacidade) | F1 |
| CHK-07 | Vários operadores simultâneos sem check-in duplicado | F1 |
| CHK-08 | Desfazer check-in (com registro de auditoria) | F1 |
| CHK-09 | **Modo offline**: baixa a lista da sessão, valida localmente e sincroniza ao reconectar | F2 |
| CHK-10 | Check-in por porta/entrada (contagem por porta) | F2 |
| CHK-11 | Lista de presença em PDF para contingência (plano B sem internet) | F1 |
| CHK-12 | Credenciamento da equipe interna (coral, músicos, técnicos) com acesso a áreas restritas | F4 |
| CHK-13 | Impressão de crachá/etiqueta (impressora térmica via navegador) | F4 |
| CHK-14 | QR dinâmico antifraude | F4 |

### 3.7 Painel e relatórios (RPT)
| Código | Requisito | Fase |
|---|---|:-:|
| RPT-01 | Dashboard do evento: inscritos, vagas restantes, check-ins por sessão, em tempo real | F1 |
| RPT-02 | Lista de participantes com filtros e exportação CSV/Excel | F1 |
| RPT-03 | Curva de inscrições no tempo, taxa de comparecimento (no-show) por sessão | F2 |
| RPT-04 | Origem das inscrições (links rastreáveis, igreja/caravana) | F2 |
| RPT-05 | Comparativo entre edições (ano a ano) | F4 |

### 3.8 Comunicação (COM)
| Código | Requisito | Fase |
|---|---|:-:|
| COM-01 | E-mails transacionais: confirmação, ingresso, cancelamento, recuperação de senha | F1 |
| COM-02 | Lembretes automáticos (7 dias, 1 dia, dia do evento) | F2 |
| COM-03 | Mensagem em massa para inscritos de uma sessão (e-mail) | F2 |
| COM-04 | Botão "compartilhar / receber pelo WhatsApp" (link `wa.me`) | F2 |
| COM-05 | Envio via API oficial do WhatsApp (Cloud API) | F4 |

### 3.9 Administração, LGPD e segurança (ADM)
| Código | Requisito | Fase |
|---|---|:-:|
| ADM-01 | Aceite de termos e política de privacidade com consentimento registrado | F1 |
| ADM-02 | Log de auditoria de ações sensíveis (check-in desfeito, cancelamentos, exportações) | F1 |
| ADM-03 | Participante pode solicitar exportação e exclusão dos seus dados | F2 |
| ADM-04 | Retenção configurável: anonimizar dados de participantes X meses após o evento | F2 |
| ADM-05 | Rate limiting em login, inscrição e check-in | F1 |
| ADM-06 | Multi-organização (outras igrejas/organizadores usando a plataforma) | F5 |

### 3.10 Requisitos não funcionais (RNF)
| Código | Requisito |
|---|---|
| RNF-01 | Responsivo: 360px (celular) a 1440px+ (desktop); telas de check-in otimizadas para tablet em retrato e paisagem |
| RNF-02 | Instalável como **PWA** (ícone na tela inicial, abre em tela cheia) |
| RNF-03 | Check-in responde em **< 500 ms** online; leitura de QR em **< 1 s** |
| RNF-04 | Suportar a corrida de abertura: **≥ 200 inscrições/minuto** sem overbooking |
| RNF-05 | Acessibilidade WCAG 2.1 AA nas telas do participante (contraste, foco, leitores de tela, fonte ajustável) |
| RNF-06 | Disponibilidade alta nas janelas críticas (abertura de inscrições e dias de evento) com monitoramento e alertas |
| RNF-07 | HTTPS obrigatório, senhas com bcrypt, QR Codes não adivinháveis (token assinado) |
| RNF-08 | Backups diários do banco com teste de restauração antes de cada evento |
| RNF-09 | Interface em português (pt-BR), datas/horas em `America/Sao_Paulo` |

---

## 4. O que NÃO FAREMOS

Decisões explícitas para manter o foco. "Não faremos" significa **fora do escopo atual** — podem ser reavaliadas, mas exigem atualizar este documento.

| Item | Motivo | Alternativa |
|---|---|---|
| **App nativo** (App Store / Play Store) | Custo de manutenção dobrado; câmera e offline já funcionam na web | **PWA** instalável |
| **Marketplace / vitrine pública de eventos** de terceiros | Não é nosso problema; exige moderação e SEO | Página própria de cada evento |
| **Revenda secundária** de ingressos | Risco jurídico e de fraude; não faz sentido em evento de igreja | Transferência gratuita (PART-06) |
| **Eventos online / streaming** | Fora do foco de credenciamento presencial | Link externo (YouTube) na página do evento |
| **Certificados de participação** | Necessidade acadêmica (Even3/Doity), não do nosso público | — |
| **Submissão e avaliação de trabalhos** | Necessidade acadêmica | — |
| **Venda em PDV físico / maquininha / bilheteria integrada** | Hardware e conciliação complexos | Inscrição pelo celular na porta (QR do evento) |
| **Emissão de nota fiscal** | Igreja e eventos gratuitos não exigem no início | Reavaliar se houver evento pago de terceiros (F5) |
| **Pulseiras RFID / cashless / consumo no evento** | Escopo de festival | — |
| **Reconhecimento facial** | Custo, privacidade (LGPD — dado biométrico sensível) | QR Code + busca por nome |
| **Precificação dinâmica / leilão** | Incompatível com o propósito | Lotes fixos (F3) |
| **Programa de afiliados com comissão** | Sem necessidade comercial | Links rastreáveis sem comissão (TKT-11) |
| **Chat em tempo real entre participantes / rede social** | Fora do foco | Grupos de WhatsApp da igreja |
| **Mapa de assentos no MVP** | Complexidade alta; o CANTEMOS pode funcionar com lugares livres + reserva PCD | Entra na F4 |
| **Multi-idioma** | Público brasileiro | pt-BR apenas |

---

## 5. Definição de MVP

O MVP é o conjunto de itens da **Fase 1**: o mínimo para realizar o CANTEMOS **sem usar outra plataforma**, com ingressos gratuitos.

Para o **CANTEMOS 2026 (19/11/2026, gratuito, 120 lugares)** o MVP foi reduzido ao **Plano Express** do [roadmap](03-roadmap.md): inscrição familiar com limite de lotação, ingresso com QR por e-mail, "meus ingressos" por link mágico, cancelamento, lista de espera simples, check-in por câmera e por nome, painel e exportação. O restante da Fase 1 é concluído depois do evento.

**Critério de sucesso do MVP:**
- 100% das inscrições do CANTEMOS feitas pelo EVENTMER.
- Nenhuma sessão com mais inscritos do que a lotação.
- Tempo médio de entrada por família na porta **< 10 segundos**.
- Nenhum voluntário de recepção precisou de mais de 5 minutos de treinamento.
- Zero incidentes de dados pessoais expostos.
