# Swarm Ledger - performance

## 2026-07-09T09:23Z - governor

- Branch: `swarm-gov/lojasync/performance`
- Mudanca: `buildDisplayedProducts` agora monta a ordenacao visual em passagens diretas sobre rascunho/produtos, sem criar a lista intermediaria de chaves originais nem fazer `map/filter` final para recuperar produtos.
- Testes: `cd frontend-ts && npm run test:logic` => 89 passed.
- Risco: baixo; contrato existente de ordenacao foi preservado pela suite logica do frontend.

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

## 2026-07-09T09:15:07-03:00 - governor

- Assunto: performance.
- Branch: `swarm-gov/lojasync/performance`.
- Mudanca: contagens dos filtros rapidos de produtos agora usam uma passagem unica com resumo de revisao por item, evitando multiplos `filter` e alocacoes de badges.
- Validacao: `cd frontend-ts && npm run test:logic` => 89 passed.
- Risco: baixo; sem alteracao esperada nos criterios dos filtros e coberto pela suite logica existente.
