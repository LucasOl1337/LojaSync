# Swarm Ledger - migracao-visual

## 2026-07-09T07:24Z - executor

- Branch: `swarm-gov/lojasync/migracao-visual`
- Mudanca: a ordenacao visual de grades agora reconhece o tamanho adulto `32` antes de `34/36/38`, alinhando a prioridade base ao preset de familias adultas.
- Testes: `cd frontend-ts && npm run test:logic` passou com 90 testes.
- Risco: baixo; altera apenas prioridade de ordenacao visual e teste logico de `gradeLogic`.
