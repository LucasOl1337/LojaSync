# Contexto CodeGraph - LojaSync

Gerado em 2026-06-25 a partir do cwd `C:\Projetos\LojaSync`.

## Setup executado

- `codegraph --version`: `0.9.4`.
- Documentacao local lida: `C:\Users\user\Desktop\codegraph\README.md` e `C:\Users\user\Desktop\codegraph\CLAUDE.md`.
- Documentacao do projeto lida: `README.md`.
- `.codegraph/` ja existia. Foi executado `codegraph sync .`.
- A primeira listagem tinha 188 arquivos e ficou inconsistente com arquivos reais do frontend/backend. Foi executado `codegraph index . --force`.
- Status final: 209 arquivos, 4.298 nos, 10.364 arestas, backend `node:sqlite`, indice atualizado.

## Consultas principais

- `codegraph_status`: validou o indice final.
- `codegraph_files`: levantou a estrutura indexada e alimentou `codegraph-files.json`.
- `codegraph_context`: consultado para rotas FastAPI, produtos, imports, automacao e frontend.
- `codegraph_explore`: usado uma vez para os simbolos centrais: `create_app`, `route_products`, `route_imports`, `route_automation`, `ProductService`, `SQLiteProductRepository`, `AutomationService`, `App`, `api.ts`, `AuthShell`, `ExecutionCenterPanel`, `ProductTable`, `GradeModal`.

## Complementos por leitura direta

Leitura direta foi usada para detalhes que exigiam endpoints, handlers e status por funcionalidade:

- `app/interfaces/api/http/route_products.py`
- `app/interfaces/api/http/route_imports.py`
- `app/interfaces/api/http/route_local_import_experiment.py`
- `app/interfaces/api/http/route_automation.py`
- `app/interfaces/api/http/route_auth.py`
- `app/interfaces/auth_api/http/routes.py`
- `app/bootstrap/wiring/container.py`
- `app/bootstrap/wiring/auth_container.py`
- `launcher.py`

## Observacoes de cobertura

- `frontend-ts/dist/assets/index-Cy0vR5Wx.js` esta indexado porque `frontend-ts/dist/` e versionado para distribuicao local.
- `Legacy/` tambem esta indexado. O inventario marca esse codigo como legado/desconectado quando nao e chamado pelo fluxo principal.
- O sistema principal atual esta em `app/`, `frontend-ts/src/` e `launcher.py`.
