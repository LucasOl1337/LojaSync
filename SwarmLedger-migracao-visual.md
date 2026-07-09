# Swarm Ledger - migracao-visual

## 2026-07-09T08:54Z - governor

- Branch: `swarm-gov/lojasync/migracao-visual`
- Mudanca: migrei bordas de status do diario operacional, chip de execucao e prontidao para os tokens CSS `--status-*-rgb`, removendo RGBs crus remanescentes do tema visual.
- Validacao: `rg "rgba\\((47, 210, 127|255, 179, 79|241, 72, 72)" frontend-ts/src/styles.css` nao retornou ocorrencias; `cd frontend-ts && npm run build` passou.
- Risco: baixo; altera apenas a origem dos valores de cor e recompila o `frontend-ts/dist` versionado.

## 2026-07-09T08:40Z - governor

- Branch: `swarm-gov/lojasync/migracao-visual`
- Mudanca: centralizei os tons de status dos diagnosticos de importacao em variaveis CSS (`--status-*-rgb/text`) e recompilei o `frontend-ts/dist` versionado.
- Validacao: `cd frontend-ts && npm run build` passou.
- Risco: baixo; preserva os valores visuais existentes e muda apenas a origem dos tokens CSS.

## 2026-07-09T07:24Z - executor

- Branch: `swarm-gov/lojasync/migracao-visual`
- Mudanca: a ordenacao visual de grades agora reconhece o tamanho adulto `32` antes de `34/36/38`, alinhando a prioridade base ao preset de familias adultas.
- Testes: `cd frontend-ts && npm run test:logic` passou com 90 testes.
- Risco: baixo; altera apenas prioridade de ordenacao visual e teste logico de `gradeLogic`.
