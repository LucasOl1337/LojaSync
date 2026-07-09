# Swarm Ledger - migracao-visual

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
