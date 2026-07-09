# Swarm Ledger - performance

## 2026-07-09T06:56Z - executor

- Branch: `swarm-gov/lojasync/performance`
- Mudanca: otimizada a montagem de produtos exibidos na ordenacao manual para usar `Set` nas chaves ja selecionadas, evitando buscas repetidas com `includes` em listas maiores.
- Testes: `cd frontend-ts && npm run test:logic`
- Risco: baixo; alteracao limitada a duas funcoes puras de ordenacao e validada pela suite logica do frontend.

## 2026-07-09T08:29Z - governor

- Branch: `swarm-gov/lojasync/performance`
- Mudanca: pre-calculados os termos compactados da busca de produtos uma vez por consulta, evitando recomputar o mesmo termo para cada produto filtrado.
- Testes: `cd frontend-ts && npm run test:logic`
- Risco: baixo; sem mudanca esperada no resultado da busca, apenas reducao de trabalho repetido no filtro client-side.
