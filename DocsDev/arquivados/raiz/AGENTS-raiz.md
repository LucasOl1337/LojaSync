## Contexto de produto

- O LojaSync nao usa senha/login no fluxo esperado do produto. Nao proponha, priorize ou implemente trabalhos em auth/senha/sessoes como melhoria de produto, salvo se o usuario pedir explicitamente.
- Codigo de autenticacao existente deve ser tratado como infraestrutura opcional/legada, nao como requisito ativo do app principal.
- Se encontrar `AuthShell`, rotas `/auth/*` ou runtime em `:8810`, leia como compatibilidade tecnica existente. Nao transforme isso em backlog, refactor ou hardening prioritario sem pedido explicito.
- Evidencias vivas atuais: `DocsDev/codegraph/inventory.md` documenta auth como opcional via `--enable-auth`; `PATCH_NOTES.md` e `DocsDev/releases/release-v1.2.3.md` registram que mudancas de auth/senha foram reprovadas como melhoria ativa.

## Agent-First (operacao do sistema)

- Catalogo de acoes HTTP: `DocsDev/agent/actions-index.json`
- Playbook seguro: `DocsDev/agent/PLAYBOOK.md`
- OpenAPI versionado: `DocsDev/agent/openapi.json` (gerar com `python tools/export_openapi.py`)
- CLI: `python tools/agent_run.py list|health|run <action> [--dry-run]`
- Preferir API a UI. Acoes destrutivas suportam `dry_run` e gravam undo snapshot automaticamente quando executadas de verdade.
- Automacao desktop (`/automation/execute*`) exige ambiente Windows e confirmacao humana; checar `/automation/status` antes.

## CodeGraph

Este repositorio tem indice CodeGraph local em `.codegraph/`. Proximos agentes devem consultar CodeGraph antes de usar buscas textuais para perguntas estruturais, fluxos, chamadas, definicoes de simbolos e impacto de mudancas.

- Comece por `codegraph status .` para confirmar saude do indice.
- Use `codegraph files` para navegar a estrutura indexada quando precisar de listagem estrutural.
- Use `codegraph context <termo>` para entender uma area funcional.
- Use `codegraph trace`, `codegraph callers`, `codegraph callees` e `codegraph impact` para fluxos e dependencia entre simbolos.
- Use leitura direta apenas para detalhes que o CodeGraph nao cobrir ou para texto literal.
- Consulte primeiro `DocsDev/codegraph/inventory.md`.
- Abra `DocsDev/codegraph/codegraph-visual.html` no navegador para ver o mapa clicavel dos modulos e fluxos principais.
- Se a listagem do CodeGraph divergir dos arquivos reais, rode `codegraph index . --force` e depois `codegraph status .`.
