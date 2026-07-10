# LojaSync v1.2.5 - Patch Notes

Data: 2026-07-10

Patch de consolidacao pos-v1.2.4. Esta release integra as entregas funcionais do enxame, corrige conflitos encontrados durante a integracao e reforca a seguranca das operacoes de produto, historico e importacao.

## Destaques

- Operacoes em lote agora respeitam escopo explicito de produtos selecionados.
- Juncao de duplicados preserva detalhes de produto, grades, cores e metadados relevantes.
- Criacao de conjuntos valida a composicao antes de mutar o estoque.
- Undo/redo persiste snapshots e restaura corretamente margem e estado apos reinicio.
- CLI/Agent-First rejeita entradas JSON invalidas, caminhos relativos e overrides de caminho inseguros.
- Landing page, SEO, acessibilidade, responsividade, importacao e performance foram consolidados.
- Versoes runtime, frontend, FastAPI, health check e OpenAPI sincronizadas em `1.2.5`.

## Sessoes e agentes auditados

- **Codex / Enxame LojaSync:** 14 commits da linha `enxame/lojasync/continuo`, cobrindo operacoes de produto, importacao, frontend, acessibilidade, SEO, testes e integracao funcional.
- **Codex / ShipSwarm Governor:** branches `ready-to-ship`, `bugs`, `geral-integracao`, `landing`, `performance` e `documentacao` integradas apos resolucao de conflitos. Inclui correcoes de escopo, historico, composicao, contratos HTTP, performance e documentacao.
- **Claude:** nenhuma mudanca nova atribuivel por commit, branch ou worktree apos `v1.2.4`.
- **ZCode:** nenhuma mudanca nova atribuivel por commit, branch ou worktree apos `v1.2.4`.
- **TraeWork:** nenhuma mudanca nova atribuivel por commit, branch ou worktree apos `v1.2.4`.
- **OpenCode:** nenhuma mudanca nova atribuivel por commit, branch ou worktree apos `v1.2.4`.
- **Wispr Flow:** nenhuma mudanca nova atribuivel por commit, branch ou worktree apos `v1.2.4`.

## Melhorias por area

### Produtos e estoque

- Escopo opcional por chave adicionado a categoria, marca, margem, formatacao/restauracao de codigos, descricoes e juncao de duplicados.
- Juncao de duplicados limitada ao conjunto selecionado e com preservacao de detalhes distintos, grades, cores, origem e metadados.
- Criacao de conjuntos bloqueia composicoes inconsistentes sem gerar historico fantasma.
- Historico undo/redo passa a atravessar reinicios e restaura a margem padrao associada ao snapshot.

### Agent-First e API

- Payloads HTTP tipados para acoes em lote, restauracao, juncao e escopo por chave.
- Validacao reforcada do runner contra JSON invalido, caminhos relativos e overrides de caminho com placeholders.
- OpenAPI e playbook alinhados ao contrato publicado.

### Frontend, landing e qualidade

- Integracao das melhorias de landing, SEO, acessibilidade, responsividade e importacao.
- Reconciliacao do indice de busca e filtros de produtos com os fluxos de tela.
- Build estatico do frontend regenerado para `v1.2.5`.

## Validacao

- `python -m pytest -q`: 169 passed, 5 deselected, 5 subtests passed.
- `cd frontend-ts && npm run test:logic`: 112 passed.
- `cd frontend-ts && npm run build`: passou.
- `git diff --check` e verificacao de marcadores de conflito executadas antes da publicacao.

## Diferenca nuvem/local

- Nuvem: `origin/main` permanece no release oficial `v1.2.4` (`393d086`) antes da publicacao deste patch.
- Local: o candidato `release/v1.2.5` agrega os branches funcionais auditados e os fixes de integracao.
- Branch `enxame/lojasync/continuo` e local; branches `swarm-gov/*` foram encontrados no remoto.
- Nenhuma alteracao de runtime cloud foi identificada; o produto continua seguindo o padrao desktop-web local. A publicacao oficial desta entrega e feita no GitHub via `main` e tag `v1.2.5`.
