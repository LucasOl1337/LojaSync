![LojaSync v1.2.5](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.5/v1.2.5-card.png)

# v1.2.5 - Operacoes de produto confiaveis e integracao do enxame (10/07/2026)

LojaSync v1.2.5 consolida as entregas pos-v1.2.4 em um patch focado em seguranca operacional, escopo explicito, historico persistente e qualidade de integracao.

## Novidades

1. Operacoes em lote e juncao de duplicados podem ser limitadas a chaves selecionadas.
2. Duplicados preservam detalhes distintos, grades, cores e metadados ao serem consolidados.
3. Criacao de conjuntos valida quantidades e composicao antes de alterar produtos.
4. Undo/redo restaura snapshots e margem padrao apos reinicio.
5. Runner Agent-First reforca validacao de JSON e caminhos.

## Sessoes e agentes

1. Codex / Enxame LojaSync: integracao funcional da linha `enxame/lojasync/continuo`.
2. Codex / ShipSwarm Governor: ready-to-ship, bugs, geral, landing, performance e documentacao, com conflitos resolvidos e testes executados.
3. Claude, ZCode, TraeWork, OpenCode e Wispr Flow: nenhuma mudanca nova atribuivel encontrada no repositorio desde `v1.2.4`.

## Sistemas

1. Versoes sincronizadas em runtime, frontend, FastAPI, health check e OpenAPI.
2. Patch notes, changelog, release metadata e card PNG preparados para a tag `v1.2.5`.

## Validacao

- Backend: 169 passed, 5 deselected, 5 subtests passed.
- Frontend: 112 testes de logica aprovados.
- Frontend: build de producao aprovado.
- Integracao: sem arquivos em conflito e com verificacao de whitespace antes da publicacao.

---

## Notas tecnicas

- Base: `v1.2.4` -> `v1.2.5`.
- Tag: `v1.2.5`.
- Publicacao: GitHub `main` e GitHub Release.
