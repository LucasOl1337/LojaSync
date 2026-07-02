# Changelog

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
