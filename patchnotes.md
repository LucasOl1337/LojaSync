# Patch Notes

<!-- safe-commit:generated:start -->
Generated: 2026-05-29T11:23:31.323Z
Repository: LojaSync
Path: C:\projetos\LojaSync
Branch: main
Remote: https://github.com/LucasOl1337/LojaSync.git
GitHub baseline: origin/main
State before safe commit: dirty
Ahead/behind before safe commit: ahead 0, behind 0
Recent local file changes detected: 6
Recent local commit detected: no
Last commit: 2026-04-22T07:25:19-03:00 - Refactor launcher bootstrap and add health endpoint

## Executive Summary

This safe-commit report records the current PC state for LojaSync before committing the local work. Fetch from origin completed successfully before this report.
The comparison target is origin/main. The local branch is main, with ahead 0 and behind 0 relative to GitHub after fetch.
No Git merge conflict entries were detected in the current status.
GitHub did not report remote-only commits for this branch, or the upstream comparison is unavailable.

## PC Versus GitHub

### Working Tree Compared To GitHub
```text
 PATCHNOTES.md          | 93 ++++++++++++++++++++++++++++++++++++++++++++++++++
 frontend-ts/index.html |  4 +++
 2 files changed, 97 insertions(+)
```

### File-Level Delta Against GitHub
```text
M	PATCHNOTES.md
M	frontend-ts/index.html
```

### Local-Only Commits
- None.

### GitHub-Only Commits
- None.

## Local Working Tree

### Current Status
```text
## main...origin/main
 M PATCHNOTES.md
 M frontend-ts/index.html
?? brand/
?? changelog.md
?? frontend-ts/public/apple-touch-icon.png
?? frontend-ts/public/favicon-32.png
?? frontend-ts/public/favicon.svg
?? frontend-ts/public/icon-512.png
 M PATCHNOTES.md
 M frontend-ts/index.html
?? brand/
?? changelog.md
?? frontend-ts/public/apple-touch-icon.png
?? frontend-ts/public/favicon-32.png
?? frontend-ts/public/favicon.svg
?? frontend-ts/public/icon-512.png
```

### Unstaged Diff Stat
```text
 PATCHNOTES.md          | 93 ++++++++++++++++++++++++++++++++++++++++++++++++++
 frontend-ts/index.html |  4 +++
 2 files changed, 97 insertions(+)
```

### Unstaged File Changes
```text
M	PATCHNOTES.md
M	frontend-ts/index.html
```

### Staged Diff Stat
None.

### Staged File Changes
None.

## Recent Files On This PC
- frontend-ts/index.html (2026-05-29T11:02:58.687Z)
- brand (2026-05-29T03:14:54.816Z, dir)
- frontend-ts/public/apple-touch-icon.png (2026-05-29T03:14:53.969Z)
- frontend-ts/public/favicon-32.png (2026-05-29T03:14:54.817Z)
- frontend-ts/public/favicon.svg (2026-05-29T03:13:14.162Z)
- frontend-ts/public/icon-512.png (2026-05-29T03:14:53.229Z)

## Operational Notes

- These notes were generated before the final staging step for this safe commit.
- Existing local notes, when present, are preserved below this generated block instead of being discarded.
- Untracked files are listed through Git status; ignored build/cache folders are not forced into the commit.
- The intended commit message format is date plus state plus "safe commit".
<!-- safe-commit:generated:end -->

## Previous Local Notes Preserved

## Release atual

Esta entrega consolida a nova base do LojaSync com frontend TypeScript opcional em `/ts`, mantendo o frontend legado funcional em `/`.

Status da release:

- frontend legado continua operando como fallback
- frontend TypeScript ja cobre o fluxo principal de operacao e testes
- backend Python continua como nucleo operacional
- automacao nativa do ByteEmpresa foi introduzida de forma opcional, sem remover o caminho legado

## Principais novidades

### 1. Workspace novo em TypeScript

- novo frontend React + TypeScript em [frontend-ts](C:\Users\user\Desktop\LojaSync\frontend-ts)
- acesso pela rota `http://127.0.0.1:8800/ts/`
- root legado em `/` continua funcional para compatibilidade
- layout reformulado para operacao em tela cheia, com foco em lista, cadastro e automacao

Arquivos principais:

- [App.tsx](C:\Users\user\Desktop\LojaSync\frontend-ts\src\App.tsx)
- [api.ts](C:\Users\user\Desktop\LojaSync\frontend-ts\src\api.ts)
- [styles.css](C:\Users\user\Desktop\LojaSync\frontend-ts\src\styles.css)
- [types.ts](C:\Users\user\Desktop\LojaSync\frontend-ts\src\types.ts)

### 2. Atualizacao em tempo real sem depender de F5

- introduzido broker de eventos de UI em [ui_events.py](C:\Users\user\Desktop\LojaSync\app\shared\ui_events.py)
- websocket `/ws/ui` agora distribui eventos reais de mudanca de estado
- rotas principais passaram a publicar `state.changed` e `job.updated`
- a UI nova atualiza lista, resumo, automacao e importacao sem reload completo

Arquivos principais:

- [ui_events.py](C:\Users\user\Desktop\LojaSync\app\shared\ui_events.py)
- [route_core.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\route_core.py)
- [route_products.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\route_products.py)
- [jobs/store.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\jobs\store.py)

### 3. Ferramentas da lista portadas para o frontend novo

- cadastro manual com fluxo de `Enter`
- edicao inline de itens
- recalculo de venda a partir do custo e da margem
- aplicacao global de marca e categoria direto no cabecalho da lista
- criacao de marca nova a partir do seletor de marca
- ordenacao por clique sequencial
- criacao de conjuntos
- juntar repetidos
- juntar grades
- formatacao de codigos com operacoes de manter/remover primeiros ou ultimos caracteres
- melhoria de descricoes com filtros utilitarios
- `Ctrl+Z` e `Ctrl+Shift+Z` com historico de snapshots

### 4. Editor de grades redesenhado

- `Inserir Grade` agora abre um editor dedicado por item
- suporte a familias de tamanhos horizontais
- persistencia da ultima familia usada
- navegacao por `Tab`
- `Enter` salva a grade atual e avanca para o proximo item
- validacao da soma da grade contra a quantidade do produto
- indicador visual de item completo
- bloqueio de avancar quando a grade estiver errada
- limpar grade do item atual
- limpar todas as grades com confirmacao
- personalizacao de familias e tamanhos para o usuario
- ordem visual da UI separada da ordem ERP usada pela automacao

### 5. Configuracoes de automacao portadas para TypeScript

- modal de configuracoes acessivel a partir do frontend TS
- captura e edicao dos `targets` do cadastro
- configuracao do GradeBot e da ordem ERP
- visualizacao de contexto do ByteEmpresa
- acao de preparar o ByteEmpresa
- persistencia imediata das alteracoes para evitar perda em refresh

Arquivos principais:

- [route_automation.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\route_automation.py)
- [service.py](C:\Users\user\Desktop\LojaSync\app\application\automation\service.py)
- [profiles.py](C:\Users\user\Desktop\LojaSync\app\application\automation\profiles.py)

### 6. Refatoracao do pipeline de importacao

- `route_jobs.py` deixou de concentrar toda a logica
- parsing de romaneio isolado em modulo proprio
- store de jobs em memoria separado
- cliente LLM e runtime de jobs modularizados
- reducao de bloqueios agressivos no fluxo de importacao

Arquivos principais:

- [route_jobs.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\route_jobs.py)
- [runtime.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\jobs\runtime.py)
- [parsing.py](C:\Users\user\Desktop\LojaSync\app\application\imports\parsing.py)
- [in_memory.py](C:\Users\user\Desktop\LojaSync\app\shared\jobs\in_memory.py)

### 7. Base nativa para ByteEmpresa com pywinauto

- nova camada de descoberta e sessao do ByteEmpresa
- identificacao da janela interativa atual
- validacao de contexto da automacao
- preparacao de tela de cadastro usando `pywinauto`
- fluxo nativo ainda opcional, mantendo o caminho legado como fallback seguro

Arquivos principais:

- [catalog.py](C:\Users\user\Desktop\LojaSync\app\application\automation\byteempresa\catalog.py)
- [session.py](C:\Users\user\Desktop\LojaSync\app\application\automation\byteempresa\session.py)
- [models.py](C:\Users\user\Desktop\LojaSync\app\application\automation\byteempresa\models.py)

### 8. Melhorias de base e testes

- container principal tipado com dataclass em vez de `dict` solto
- montagem opcional da UI TS em `/ts` no backend
- novos testes para importacao, job store e gate do ByteEmpresa nativo

Arquivos principais:

- [container.py](C:\Users\user\Desktop\LojaSync\app\bootstrap\wiring\container.py)
- [app.py](C:\Users\user\Desktop\LojaSync\app\interfaces\api\http\app.py)
- [test_import_parsing.py](C:\Users\user\Desktop\LojaSync\tests\test_import_parsing.py)
- [test_job_store.py](C:\Users\user\Desktop\LojaSync\tests\test_job_store.py)
- [test_automation_service_native_gate.py](C:\Users\user\Desktop\LojaSync\tests\test_automation_service_native_gate.py)
- [test_byteempresa_catalog.py](C:\Users\user\Desktop\LojaSync\tests\test_byteempresa_catalog.py)

## O que permanece intencionalmente

- frontend legado em `/` continua ativo
- frontend TypeScript fica em `/ts` para transicao controlada
- automacao PyAutoGUI/GradeBot continua disponivel como fallback
- persistencia principal ainda usa JSON/JSONL

## Limites conhecidos desta release

- a UI TS ainda concentra muita logica em um arquivo grande
- a persistencia ainda nao foi migrada para SQLite
- a automacao nativa do ByteEmpresa ainda nao substitui todo o legado
- jobs de importacao continuam em memoria, sem retomada duravel apos reinicio

## Direcao recomendada apos esta release

1. consolidar o frontend TypeScript como interface principal
2. migrar persistencia operacional para SQLite
3. modularizar `App.tsx`, `ProductService` e `AutomationService`
4. ampliar cobertura de testes de integracao
5. fechar a transicao de automacao nativa do ByteEmpresa
