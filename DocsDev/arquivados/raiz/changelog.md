# Changelog

## [2026-07-10] - LojaSync v1.2.6

**Project:** LojaSync  |  **Branch:** main  |  **State:** audited-release-patch

### Summary
- Portada a migracao visual de estados operacionais que ainda nao estava em v1.2.5.
- Adicionada a flag `--llm-monitor-port` ao launcher com cobertura automatizada.
- Classificadas branches/worktrees locais sem duplicar fixes equivalentes nem publicar prototipos bloqueados.
- Sincronizados bundle, metadata, OpenAPI, notas e card da release v1.2.6.

### Validation
- Suite pytest completa aprovada.
- Frontend: 112 testes de logica e build de producao aprovados.
- Smoke visual desktop/mobile aprovado no navegador integrado.

## [2026-07-10] - LojaSync v1.2.5

**Project:** LojaSync  |  **Branch:** main  |  **State:** swarm-integration-patch

### Summary
- Consolidada a rodada pos-v1.2.4 do enxame, com integracao das linhas funcionais e do governor.
- Reforcados escopo de acoes em lote, juncao de duplicados, composicao de conjuntos e undo/redo persistente.
- Resolvidos conflitos de API, frontend, landing, performance e documentacao.
- Preparados patch notes, metadata, OpenAPI, build frontend e card PNG para `v1.2.5`.

### Validation
- Backend: suite pytest final do candidato.
- Frontend: 112 testes de logica aprovados.
- Frontend: build de producao aprovado.

## [2026-07-09] - LojaSync v1.2.4

**Project:** LojaSync  |  **Branch:** main  |  **State:** minimax-guard-release

### Summary
- Minimax `minimax-m3` fixado como rota padrao de IA via LLM3/Ollama compativel.
- Removido fallback padrao para Gemma; configuracoes antigas podem tentar modelo configurado, mas o fallback seguro volta para Minimax.
- Adicionada guarda local para todo resultado Minimax que nao tenha aprovacao automatica antes de persistir produtos.
- Reforcados fatiamento de PDF imagem, erros de IA, UI de importacao e evidencias Agent-First.
- Release `v1.2.4` preparada com versoes runtime/frontend, patch notes, docs de release e card PNG.

### Validation
- `python -m pytest -q`: 152 passed, 5 deselected, 5 subtests passed.
- `cd frontend-ts && npm run test:logic`: 89 passed.
- `git diff --check`: passou.
- `2866.pdf` repetido 3 vezes: 3/3 aprovado com guarda local.
- Super Romaneios parcial final: 15/15 aprovados antes da interrupcao manual.

---

## [2026-07-08] - LojaSync v1.2.3

**Project:** LojaSync  |  **Branch:** main  |  **State:** release-multiagente

### Summary
- Integrados os itens aprovados da rodada pos-`v1.2.2`: SEO publico, pagina Early Access, kit de confianca, code split inicial, onboarding de lista vazia, ledger QA, smoke test de assets e higiene documental.
- Auditados agentes/sessoes citados pelo humano: houve evidencia local de Codex; nao houve sessao ou commit atribuivel a Claude, ZCode, Wispr Flow, OpenCode ou Trae Work desde `v1.2.2`.
- Mantidos fora do release: `f87b1d1` por conflito com a regra de produto sem auth como prioridade, branch `swarm` por conflito/supersedencia e `lojasync-concepts-visual/` por falta de integracao/validacao.
- Release `v1.2.3` preparada com versoes runtime/frontend, patch notes, docs de release e card PNG.

### Validation
- `git diff --check`: passou.
- `python -m pytest`: 135 passed, 5 deselected.
- `cd frontend-ts && npm run build`: passou.
- `cd frontend-ts && npm run test:logic`: 89 passed.

---

## [2026-07-02] - LojaSync v1.2.2

**Project:** LojaSync  |  **Branch:** main  |  **State:** coletor-pos-enxame

### Summary
- Integrados 6 commits aprovados do enxame: busca por codigos, jobs em erro, totais do frontend, parser de grades, GradeBot e normalizacao monetaria OCR.
- Reprovado o commit de auth/sessoes por contrariar a regra local de produto; o revert correspondente ficou fora por ser no-op sem o commit reprovado.
- Release `v1.2.2` preparada com versoes runtime/frontend, patch notes, docs de release e card PNG.

### Validation
- `python -m pytest`: 135 passed, 5 deselected.
- `cd frontend-ts && npm run test:logic`: 89 passed.
- `cd frontend-ts && npm run build`: passou.

---

## [2026-06-07] - Safe Commit Sync (Multi-Agent + PC vs GitHub Research)

**Project:** LojaSync  |  **Branch:** main  |  **State:** grokassets-clean

### PC vs GitHub
- Synced on prior 2026-06-02+clean
- Dirty: grokassets deletes + mds update
- 24h: cleanup + doc

### Summary
Grokassets brand/pitch/social deduplication (removal of duplicated assets now centralized). Patchnotes + changelog refreshed with 2026-06-07 research across active projects.

See patchnotes for details and cross-project note (same sweep in AutoWebGame, LUCA-AI, Kamui, Yume...).

### Files
M changelog, patchnotes ; D grokassets/**/*

---
Prior in git.
<!-- 2026-06-07 safe sync -->

<!-- safe-commit-audit:2026-07-17 -->
## Snapshot detalhado — 2026-07-17

### Linha de base

- **Local:** `69f5b954368a` em `main`, datado de 2026-07-14T12:41:08-03:00.
- **GitHub/upstream:** `69f5b954368a` via `origin/main`; origin `https://github.com/LucasOl1337/LojaSync.git`.
- **Relação no momento da auditoria:** 0 atrás / 0 à frente.
- **Escopo:** commits e mudanças observados nas últimas 500 horas, com o estado não commitado preservado separadamente.

### Histórico de commits na janela de 500 horas

- `69f5b95` — 2026-07-14T12:41:08-03:00 — **LucasOl1337** — release: v1.2.7
- `2489dc5` — 2026-07-14T12:28:47-03:00 — **LucasOl1337** — Revert "style(migracao-visual): usa tokens em status operacionais"
- `d474570` — 2026-07-14T12:22:02-03:00 — **LucasOl1337** — Revert "style(migracao-visual): reforca estados operacionais"
- `d6861e8` — 2026-07-14T12:19:28-03:00 — **LucasOl1337** — Revert "chore(ready-to-ship): rebuild on public assets"
- `ee2aa88` — 2026-07-14T12:10:42-03:00 — **LucasOl1337** — Add release metadata readiness gate
- `909541d` — 2026-07-14T11:55:17-03:00 — **LucasOl1337** — fix(ready-to-ship): reject invalid agent body json
- `d7c1f9f` — 2026-07-14T11:51:39-03:00 — **LucasOl1337** — fix(ready-to-ship): harden agent health smoke
- `5a55c68` — 2026-07-14T11:51:38-03:00 — **LucasOl1337** — chore(ready-to-ship): rebuild on public assets
- `e5bf5dd` — 2026-07-14T11:49:24-03:00 — **LucasOl1337** — Migrate table review visuals to status tokens
- `2ac0c57` — 2026-07-14T11:48:15-03:00 — **LucasOl1337** — style(migracao-visual): reforca estados operacionais
- `69a5dd5` — 2026-07-14T11:43:39-03:00 — **LucasOl1337** — style(migracao-visual): usa tokens em status operacionais
- `d2cc0fc` — 2026-07-14T11:36:51-03:00 — **LucasOl1337** — chore(migracao-visual): centraliza tokens de status
- `c8ebd0a` — 2026-07-14T11:32:30-03:00 — **LucasOl1337** — fix(geral): trata falha de conexao no agent runner
- `12fb598` — 2026-07-14T11:30:52-03:00 — **LucasOl1337** — fix(geral): trata body json invalido no agent runner
- `4f881f4` — 2026-07-14T11:27:44-03:00 — **LucasOl1337** — feat(geral): expose llm monitor port flag
- `cbd61a1` — 2026-07-10T15:18:36-03:00 — **LucasOl1337** — release: v1.2.6
- `567aa23` — 2026-07-10T09:53:33-03:00 — **LucasOl1337** — release: v1.2.5
- `7f4d2f2` — 2026-07-10T09:36:30-03:00 — **LucasOl1337** — docs: integrate release documentation
- `87471f4` — 2026-07-10T09:36:23-03:00 — **LucasOl1337** — perf: integrate governor performance work
- `ed1e825` — 2026-07-10T09:36:09-03:00 — **LucasOl1337** — fix: resolve landing integration
- `4c2c481` — 2026-07-10T09:35:27-03:00 — **LucasOl1337** — fix: resolve agent runner integration
- `3b31828` — 2026-07-10T09:34:54-03:00 — **LucasOl1337** — fix: resolve governor bug integration
- `e3dfd72` — 2026-07-10T09:34:26-03:00 — **LucasOl1337** — release: integrate ready-to-ship governor work
- `6fa73d1` — 2026-07-10T08:13:23-03:00 — **Enxame LojaSync** — feat(importacao): exibir avisos acionaveis
- `736259c` — 2026-07-10T02:05:59-03:00 — **Enxame LojaSync** — fix(undo): desfazer/refazer restaura margem padrao junto com o catalogo
- `6873575` — 2026-07-10T01:13:04-03:00 — **Enxame LojaSync** — fix(conjuntos): bloquear criação que deixaria grades/cores acima do saldo
- `2b8a668` — 2026-07-10T00:40:09-03:00 — **Enxame LojaSync** — feat(grades): proteger rascunho não salvo contra descarte silencioso
- `93f2f77` — 2026-07-09T22:11:41-03:00 — **Enxame LojaSync** — fix: preservar variacoes ao juntar repetidos
- `dba5f11` — 2026-07-09T22:04:38-03:00 — **Enxame LojaSync** — fix(frontend): scope duplicate merge to visible products
- `78a12c6` — 2026-07-09T21:56:47-03:00 — **Enxame LojaSync** — fix(frontend): scope bulk actions to visible products
- `c234a84` — 2026-07-09T21:41:41-03:00 — **Enxame LojaSync** — fix(frontend): confirmar limpeza do catalogo
- `cc3be55` — 2026-07-09T21:34:09-03:00 — **Enxame LojaSync** — perf(frontend): render catalog progressively
- `4d710b9` — 2026-07-09T21:24:31-03:00 — **Enxame LojaSync** — feat(frontend): add daily usage pulse
- `e16f211` — 2026-07-09T21:16:17-03:00 — **Enxame LojaSync** — feat: adiciona visao comercial do catalogo
- `cabdbba` — 2026-07-09T21:02:59-03:00 — **Enxame LojaSync** — feat: reutilizar produto como modelo de cadastro
- `743b591` — 2026-07-09T20:52:58-03:00 — **Enxame LojaSync** — feat: exportar catalogo visivel em CSV
- `c10acff` — 2026-07-09T20:45:05-03:00 — **Enxame LojaSync** — feat(frontend): reutilizar indice de busca de produtos
- `b0d73fb` — 2026-07-09T10:33:49-03:00 — **LucasOl1337** — docs: add public docs index
- `7a573ce` — 2026-07-09T09:34:54-03:00 — **LucasOl1337** — Improve landing mobile metadata
- `6d6fa35` — 2026-07-09T09:15:22-03:00 — **LucasOl1337** — perf: count product quick filters in one pass
- `50c9ddc` — 2026-07-09T08:55:24-03:00 — **LucasOl1337** — fix product patch null core fields
- `ee43419` — 2026-07-09T08:10:17-03:00 — **LucasOl1337** — docs(documentacao): add matriz de validacao rapida
- `530d9f5` — 2026-07-09T06:26:04-03:00 — **LucasOl1337** — feat(landing): add accessible offer skip link
- `e90d6c6` — 2026-07-09T06:21:07-03:00 — **LucasOl1337** — perf(performance): reduz trabalho na ordenacao visual
- `8603e7b` — 2026-07-09T06:15:54-03:00 — **LucasOl1337** — fix(bugs): preserva quantidade decimal no payload de grades
- `9104bfb` — 2026-07-09T06:05:12-03:00 — **LucasOl1337** — docs(documentacao): clarify DocsDev canon
- `e6b64fb` — 2026-07-09T05:49:50-03:00 — **LucasOl1337** — docs(documentacao): add headless agent gate
- `a062954` — 2026-07-09T05:37:13-03:00 — **LucasOl1337** — feat(landing): adiciona dados estruturados da oferta
- `6066694` — 2026-07-09T05:29:57-03:00 — **LucasOl1337** — perf(performance): evita recomputar termos de busca
- `ac9e29e` — 2026-07-09T05:26:05-03:00 — **LucasOl1337** — fix(bugs): aceitar quantidades decimais normalizadas
- `32ba961` — 2026-07-09T05:14:55-03:00 — **LucasOl1337** — docs(documentacao): add DocsDev index
- `cad0b82` — 2026-07-09T04:53:26-03:00 — **LucasOl1337** — test(ready-to-ship): cover bundled asset serving
- `3f56842` — 2026-07-09T04:32:49-03:00 — **LucasOl1337** — docs(migracao-visual): registra validacao do governor
- `045786d` — 2026-07-09T04:32:10-03:00 — **LucasOl1337** — wip(migracao-visual): checkpoint nao validado do governor
- `4584466` — 2026-07-09T04:13:57-03:00 — **LucasOl1337** — feat(landing): improve early access hero metadata
- `600b6b3` — 2026-07-09T03:53:40-03:00 — **LucasOl1337** — perf(performance): otimiza ordenacao manual de produtos
- `86d122e` — 2026-07-09T03:33:25-03:00 — **LucasOl1337** — bugs: add agent CLI path override
- `c2339a9` — 2026-07-09T03:13:01-03:00 — **LucasOl1337** — collector geral: integrate agent CLI path override
- `23ded33` — 2026-07-09T01:34:11-03:00 — **LucasOl1337** — geral: add agent CLI path override
- `393d086` — 2026-07-09T00:29:33-03:00 — **LucasOl1337** — release: v1.2.4
- … e mais 15 commit(s).

### Mudanças do working tree que compõem o próximo estado

#### Versionadas/modificadas

- Nenhuma mudança versionada pendente.

#### Novas/não rastreadas

- `showcase-site/`

### Decisões de reconciliação

- O histórico remoto foi pesquisado após atualização das refs; os hashes acima fixam a comparação usada neste documento.
- Commits remotos não serão sobrescritos por *force push*.
- Mudanças paralelas equivalentes são consideradas já absorvidas quando o conteúdo canônico contém a mesma intenção e testes iguais ou mais completos.
- Mudanças paralelas disjuntas devem ser integradas por commit/cherry-pick ou merge normal, mantendo autoria e evidência.
- Arquivos operacionais ou sensíveis detectados permanecem locais e são explicitamente excluídos do stage.

### Estado desta entrada

**Preparado para safe commit**, condicionado à revisão do stage, verificação de segredos, sincronização não destrutiva com o upstream e checks do repositório.
