# Changelog

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
