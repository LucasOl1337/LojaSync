# LojaSync v1.2.3 - Patch Notes

Data: 2026-07-08

Esta release consolida a rodada multiagente posterior ao v1.2.2 com foco em venda controlada, primeira experiencia, performance perceptivel do frontend, smoke tests de distribuicao e higiene documental. Tambem deixa explicitamente fora trabalhos que priorizavam auth/senha como melhoria de produto, por conflito com as regras locais do LojaSync.

## Destaques

- Pagina publica de oferta Early Access em `/oferta.html`, com piloto inicial sugerido de R$ 497, escopo claro, limites honestos e CTA de validacao.
- Kit de confianca para venda controlada com FAQ, privacidade resumida, termos comerciais, checklist do piloto e scripts de WhatsApp.
- SEO e preview social basicos no shell publico, incluindo meta tags, Open Graph, Twitter card e `site.webmanifest`.
- Primeira experiencia melhorada: estado vazio da lista agora guia o primeiro lote com CTAs para importar romaneio ou cadastrar manualmente.
- Performance perceptivel melhor: `AuthShell` carrega o painel operacional via `React.lazy`, separando o gate inicial do bundle pesado do app.
- Smoke test novo protege `frontend-ts/dist/index.html` contra referencias a assets versionados inexistentes.

## Sessoes e agentes auditados

- **Codex / ShipSwarm:** SEO publico, kit de confianca, pagina Early Access, code split do frontend e onboarding da lista vazia.
- **Codex / DailyBugSwarm:** ledger de QA diario e smoke test de assets do frontend versionado.
- **Codex / DocsSwarm:** classificacao documental, pontes entre `docs/` e `DocsDev/`, marcacao de historicos/superseded e atualizacao das instrucoes sobre auth opcional.
- **Claude:** nenhuma sessao ou commit atribuivel encontrado localmente desde `v1.2.2`; apenas referencia historica ao `CLAUDE.md` do CodeGraph.
- **ZCode, Wispr Flow, OpenCode e Trae Work:** nenhuma sessao ou commit atribuivel encontrado localmente desde `v1.2.2`.

## Melhorias

- `frontend-ts/index.html` e `frontend-ts/public/site.webmanifest`: adicionam metadados comerciais para busca e compartilhamento.
- `frontend-ts/public/oferta.html`: apresenta a oferta controlada de piloto pago com fluxo de validacao, limites e entregaveis.
- `frontend-ts/public/early-access-hero.png`: adiciona arte bitmap propria para a campanha Early Access.
- `frontend-ts/src/AuthShell.tsx`: divide o carregamento inicial do app para reduzir o JS necessario antes do painel operacional.
- `frontend-ts/src/App.tsx`, `frontend-ts/src/productTable.tsx` e `frontend-ts/src/styles.css`: transformam lista vazia em roteiro de primeiro lote com acoes reais.

## Correcoes e sistemas

- `tests/test_http_frontend.py`: valida que scripts e estilos locais referenciados por `frontend-ts/dist/index.html` existem no build versionado.
- `DailyBugSwarm.md`, `ShipSwarm.md` e `DocsSwarm.md`: registram rodadas, evidencias, riscos e decisoes para futuras auditorias.
- `AGENTS.md`, `README.md`, `DocsDev/*` e `docs/*`: alinham a documentacao viva ao estado atual do produto, deixando auth/senha como infraestrutura opcional/legada e JSON/JSONL como legado de migracao para SQLite.
- `automation/crawler-setup.md`: marcado como historico/experimental para nao ser confundido com runtime vivo de LLM/OCR/importacao/automacao.

## Itens auditados e deixados fora

- `f87b1d1` (`Improve unauthenticated access gate`): reprovado para este release porque transforma login/senha em narrativa comercial ativa, contrariando `AGENTS.md`.
- Branch `swarm` / `05d6bb1`: nao integrada como branch porque e uma alternativa SEO paralela e conflitante com o `main`; o SEO aprovado ja esta no fluxo principal.
- `lojasync-concepts-visual/`: mantido fora do release por ser prototipo visual nao conectado ao app e sem validacao visual final.
- Snapshots `refs/codex/snapshots/*`: auditados como memoria de worktree; nao foram integrados automaticamente.

## Validacao da release

- `codegraph status .`: OK antes da preparacao; apos o smoke test novo, o indice apontou 1 arquivo modificado e foi sincronizado durante a preparacao.
- `git diff --check`: passou; apenas avisos LF/CRLF esperados no Windows.
- `python -m pytest`: 135 passed, 5 deselected.
- `python -m pytest tests/test_http_frontend.py` na worktree `e6dd`: 5 passed antes do cherry-pick.
- `cd frontend-ts && npm run build`: passou; build versionado com `index-CXySh6k9.css`, `App-WUILa4KL.js` e `index-vXSbsgx9.js`.
- `cd frontend-ts && npm run test:logic`: 89 passed.

## Riscos conhecidos

- A automacao desktop continua dependente de Windows, posicoes de tela e disponibilidade do Byte Empresa.
- O fallback por LLM depende do servico configurado em `LLM_BASE_URL`/`LLM_HOST`/`LLM_PORT`.
- A pagina de oferta e material comercial nao implementam billing, paywall, assinatura ou licenciamento remoto.
- O fluxo de auth/senha segue tratado como infraestrutura opcional/legada, nao como melhoria ativa do produto principal.
