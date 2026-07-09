# DocsDev index

Este indice aponta para a documentacao viva mais util para manutencao, releases e operacao Agent-First do LojaSync.

## Operacao Agent-First

- `agent/PLAYBOOK.md`: sequencia segura para agentes, dry-run, snapshots e verificacao.
- `agent/actions-index.json`: catalogo versionado das acoes HTTP disponiveis.
- `agent/openapi.json`: contrato OpenAPI exportado por `python tools/export_openapi.py`.

## Arquitetura e inventario

- `codegraph/inventory.md`: mapa funcional principal do produto e status dos fluxos.
- `codegraph/codegraph-context.md`: contexto gerado a partir do indice CodeGraph.
- `architecture/blueprint.md`: desenho tecnico de alto nivel.
- `architecture/qol-feature-rounds.md`: historico de rodadas de melhorias de uso.
- `architecture/codegraphy-audit.md`: auditoria estrutural apoiada por CodeGraph.

## Migracao visual

- `migration/component-inventory.md`: inventario de componentes da UI.
- `migration/equivalence-matrix.md`: matriz de equivalencia para migracao visual.

## Releases e distribuicao

- `releases/`: notas e metadados versionados por release.
- `distribution/productization-plan.md`: plano de empacotamento e produto.
- `validation/`: evidencias de validacao, benchmarks e execucoes de importacao.

## Handoffs

- `handoffs/`: transferencias de contexto entre sessoes de desenvolvimento.

## Regras de leitura

1. Comece por este indice, `README.md`, `AGENTS.md` e `codegraph/inventory.md`.
2. Para perguntas estruturais, consulte CodeGraph antes de busca textual ampla.
3. Abra profundamente apenas os documentos ligados ao assunto em execucao.
