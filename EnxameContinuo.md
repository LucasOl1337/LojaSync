# Enxame Continuo - LojaSync

Arquivo de coordenacao da automacao `enxame-cont-nuo-lojasync` na worktree
`C:\Projetos\LojaSync-enxame` e branch `enxame/lojasync/continuo`.

## BACKLOG DO ENXAME

- [ ] Isolar o CodeGraph da worktree: `codegraph status .` resolve o projeto como
  `C:\Projetos` e mistura milhares de arquivos externos; `codegraph index . --force`
  foi tentado nesta rodada, mas tambem herdou o indice ancestral.

## Claims ativos

| Sessao | Area | Entrega | Arquivos reivindicados | Status |
|---|---|---|---|---|
| - | - | - | - | nenhum claim ativo |

## Rodadas concluidas

### 2026-07-09-01 - Busca responsiva em catalogos grandes

- Area sorteada: Performance perceptivel.
- Entrega: o texto pesquisavel dos produtos agora e normalizado e compactado uma
  vez por atualizacao/ordenacao do catalogo; consultas digitadas reutilizam esse
  indice em memoria.
- Arquivos: `frontend-ts/src/productFilters.ts`, `frontend-ts/src/App.tsx`,
  `frontend-ts/test/productFilters.test.mjs`, `frontend-ts/dist/**`.
- Antes: o benchmark de 20.000 produtos e 12 consultas reconstruiu o texto de
  todos os produtos a cada consulta, com `median_ms=733.93` e `p95_ms=954.33`.
- Depois: o mesmo benchmark reutilizou o indice, preservou o checksum `3029025`
  e mediu `median_ms=27.58` e `p95_ms=41.75` (96,2% menos tempo mediano).
- Evidencia literal: `SEARCH_BENCHMARK strategy=per-query-normalization products=20000 queries=12 median_ms=733.93 p95_ms=954.33 checksum=3029025`.
- Evidencia literal: `SEARCH_BENCHMARK strategy=prebuilt-index products=20000 queries=12 median_ms=27.58 p95_ms=41.75 checksum=3029025`.
- Evidencia literal: `tests 90`, `pass 90`, `fail 0`.
- Evidencia literal do build: `47 modules transformed.` e `built in 181ms`.
- Commit: este commit.
