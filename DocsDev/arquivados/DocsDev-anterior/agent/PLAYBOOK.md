# Agent playbook - LojaSync

Base: `http://127.0.0.1:8800`
Catalogo: `DocsDev/agent/actions-index.json`
OpenAPI: `DocsDev/agent/openapi.json` (gerar com `python tools/export_openapi.py`)
CLI: `python tools/agent_run.py`

## Sequencia segura

1. `GET /health` -> `status=ok`
2. Acao destrutiva: primeiro com `dry_run=true` (query ou body)
3. Executar mutacao real (`dry_run=false` / omitido) - bulk destrutivo grava snapshot de undo sozinho
4. Verificar: `GET /products` + `GET /totals`
5. Falhou? `POST /actions/history/undo`
6. Automacao desktop: so se `GET /automation/status` estiver idle/ready; senao parar

## Dry-run suportado

| Acao | Como |
|------|------|
| `DELETE /products` | `?dry_run=true` |
| `POST /actions/join-duplicates` | `?dry_run=true` |
| `POST /actions/apply-category` | body `"dry_run": true` |
| `POST /actions/apply-brand` | body `"dry_run": true` |
| `POST /actions/join-grades` | body `"dry_run": true` |
| `POST /actions/format-codes` | body `"dry_run": true` |
| `POST /actions/apply-margin` | body `"dry_run": true` |
| `POST /actions/improve-descriptions` | body `"dry_run": true` |

Resposta inclui `"dry_run": true|false`. Em dry-run **nao** persiste e **nao** grava snapshot.

## Auto-snapshot (quando dry_run=false)

clear, delete item, apply-category/brand, join-duplicates, join-grades, format-codes, restore-original-codes, apply-margin, create-set, improve-descriptions.

## CLI rapida

```powershell
python tools/agent_run.py list
python tools/agent_run.py health
python tools/agent_run.py run products.list
python tools/agent_run.py run actions.join_duplicates --dry-run
python tools/export_openapi.py
```

## Gate para agentes headless

1. Leitura: `health.check`, `products.list`, `totals.get`, `brands.list`, `margin.get`, `automation.status`.
2. Simulacao: toda acao com `dry_run` deve ser executada primeiro com `--dry-run` ou payload equivalente.
3. Mutacao real: execute somente depois de revisar o plano do dry-run e garanta verificacao por `products.list` ou `totals.get`.
4. Recuperacao: se a verificacao falhar apos mutacao com snapshot, rode `history.undo` antes de tentar nova correcao.
5. Desktop: nunca chame `automation.execute*` se `automation.status` nao indicar runtime ocioso/pronto.

## Nao fazer

- Auth/login (opcional; nao e fluxo de produto)
- Clicar UI quando existir endpoint
- `automation.execute*` sem status idle
