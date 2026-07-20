# DailyBugSwarm - LojaSync

Memoria oficial do enxame continuo focado em bugs de uso diario do LojaSync.

## Objetivo

Aumentar progressivamente a confiabilidade dos fluxos usados por uma loja no dia a dia: iniciar o app, cadastrar produtos, importar romaneios, revisar listagens, editar dados, desfazer/refazer, lidar com grades e executar automacao local com feedback claro.

## Estado

- Rodada atual: 3/20
- Ultima atualizacao: 2026-07-08 17:55 -03:00
- Modo: sequencial, uma rodada por chat
- Branch observada: `HEAD` destacado em `72dd8bf`
- Worktree efetiva desta sessao: `C:\Users\user\.codex\worktrees\e6dd\LojaSync`
- Observacao operacional: comandos executados com `git -C C:\Users\user\.codex\worktrees\e6dd\LojaSync` e caminhos absolutos porque o shell inicial caiu em `C:\projetos`.

## Mapa inicial de fluxos criticos

| Fluxo | Uso diario provavel | Arquivos principais | Validacao inicial |
|---|---|---|---|
| Inicializacao do app | Abrir LojaSync pelo `.bat` ou `launcher.py` e acessar painel principal | `launcher.py`, `app/interfaces/api/http/app.py`, `frontend-ts/src/main.tsx`, `frontend-ts/src/AuthShell.tsx` | `python -m pytest`, `npm run build`, smoke manual futuro em `http://127.0.0.1:8800` |
| Cadastro manual de produto | Cadastrar item avulso com quantidade, preco, marca/categoria | `frontend-ts/src/productEntryPanel.tsx`, `frontend-ts/src/productForm.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`, `app/application/products/service.py` | testes de `productForm`, API `POST /products`, smoke da tela |
| Listagem, busca e filtros | Revisar produtos ja cadastrados/importados | `frontend-ts/src/productTable.tsx`, `frontend-ts/src/productFilters.ts`, `frontend-ts/src/productOrdering.ts`, `app/interfaces/api/http/route_products.py` | `npm run test:logic`, smoke visual |
| Edicao inline e lote | Corrigir campos, marca, categoria, codigo, margem e descricoes | `frontend-ts/src/editableProductCell.tsx`, `frontend-ts/src/productEditing.ts`, `frontend-ts/src/productListControls.tsx`, `app/application/products/service.py` | testes de logica e API patch |
| Importacao de romaneio | Enviar PDF/texto de fornecedor e importar itens | `frontend-ts/src/importStagePanel.tsx`, `app/interfaces/api/http/route_imports.py`, `app/application/imports/local_experiment.py`, `app/application/imports/job_validation.py` | testes backend de parser/import e smoke de job |
| Grades | Editar e consolidar tamanhos/quantidades | `frontend-ts/src/gradeModal.tsx`, `frontend-ts/src/gradeLogic.ts`, `app/domain/products/grade_utils.py`, `app/domain/grades/parser.py` | testes de `gradeLogic` e backend |
| Automacao Byte Empresa | Executar cadastro no ERP local | `frontend-ts/src/executionCenterPanel.tsx`, `frontend-ts/src/settingsModal.tsx`, `app/interfaces/api/http/route_automation.py`, `app/application/automation/service.py` | testes backend; execucao real depende de desktop configurado |
| Undo/redo | Recuperar alteracoes acidentais | `frontend-ts/src/keyboardShortcuts.ts`, `app/infrastructure/persistence/files/undo_history.py`, `app/application/products/service.py` | testes de historico e fluxo manual |

## Telas mais provaveis de uso diario

- Painel principal React em `/`.
- Formulario de cadastro manual.
- Lista/tabela de produtos.
- Painel de importacao de romaneio.
- Modal de grades.
- Centro de execucao/automacao.
- Modal de configuracoes de automacao.
- Dialogos de confirmacao, aviso e toasts.

## Comandos de validacao

| Area | Comando | Status nesta sessao |
|---|---|---|
| CodeGraph | `codegraph status .` | OK, indice atualizado |
| Backend | `python -m pytest` | OK, 135 passed, 5 deselected |
| Frontend build | `cd frontend-ts; npm run build` | OK |
| Frontend logica | `cd frontend-ts; npm run test:logic` | OK, 89 tests passed |
| Smoke HTTP/UI | `uvicorn`, Browser integrado e `Invoke-WebRequest` | OK, raiz renderizou, `/health` e `/products` 200, `/ts/` 307 |
| Smoke regressao frontend | `python -m pytest tests/test_http_frontend.py` | OK, 5 passed |
| Git | `git status --short` | arvore ja suja antes desta sessao |

## Bugs encontrados

| ID | Titulo | Severidade | Probabilidade | Impacto | Decisao | Evidencia |
|---|---|---|---|---|---|---|
| DBS-001 | Ausencia de ledger do enxame diario podia fazer agentes repetirem escopos ou priorizarem auth legado | P4 | alta | medio | corrigido | `DailyBugSwarm.md` criado com mapa, claims, comandos, riscos e historico |
| DBS-002 | Risco de regressao nao coberta em `frontend-ts/dist/index.html` apontar para assets inexistentes e abrir tela em branco | P4 | media | medio | corrigido | Smoke real renderizou a raiz; teste novo valida scripts/styles locais referenciados pelo HTML versionado |

## Bugs corrigidos

| ID | Titulo | Arquivos | Commit | Validacao |
|---|---|---|---|---|
| DBS-001 | Ledger inicial do enxame diario | `DailyBugSwarm.md` | `acae87d` | `codegraph status .`; `python -m pytest`; `npm run test:logic`; `npm run build` |
| DBS-002 | Protecao de smoke para assets do frontend versionado | `tests/test_http_frontend.py`, `DailyBugSwarm.md` | pendente nesta etapa | Browser integrado; `python -m pytest tests/test_http_frontend.py`; `npm run build`; `npm run test:logic` |

## Bugs pendentes

| ID | Titulo | Motivo para pendencia | Proxima acao |
|---|---|---|---|
| - | - | - | - |

## Escopos reivindicados

| Rodada | Area | Fluxo/tela | Arquivos pretendidos | Hipotese de bug/risco | Risco de conflito | Risco funcional | Como reproduzir | Como validar | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1/20 | Diagnostico inicial | Inicializacao, rotas principais e comandos | `DailyBugSwarm.md` | Sem mapa operacional, proximos agentes poderiam testar auth legado ou rotas erradas; risco de perder bug diario por escopo incorreto | Baixo; `DailyBugSwarm.md` novo, mas ha mudancas pre-existentes em docs que nao foram tocadas | Baixo; foco documental e validacao | Consultar CodeGraph, README/AGENTS, executar comandos de teste/build, revisar falhas objetivas | `codegraph status .`, `python -m pytest`, `npm run test:logic`, `npm run build` | concluido |
| 2/20 | Smoke test geral | Inicializacao local, painel principal, rotas API/frontend e console | `DailyBugSwarm.md`; `tests/test_http_frontend.py` | App pode falhar ao abrir, servir frontend errado, quebrar rota raiz/API ou emitir erro de console na primeira experiencia | Medio; outros enxames mexeram em frontend publico/dist, entao evitar tocar assets gerados sem necessidade | Medio; smoke mexe no primeiro contato do usuario com o app | Subir backend local, abrir `http://127.0.0.1:8800`, consultar rotas principais e observar console/rede | HTTP status, Browser integrado, `python -m pytest tests/test_http_frontend.py`, `npm run build`, `npm run test:logic` | concluido |

## Evidencias

- 2026-07-08: `codegraph status .` retornou indice atualizado em `C:\projetos\LojaSync` com 210 arquivos, 4.572 nos e 11.462 arestas.
- 2026-07-08: `AGENTS.md` e `README.md` confirmam produto principal sem login/senha obrigatorio, auth runtime apenas opcional via `--enable-auth`.
- 2026-07-08: `DocsDev/codegraph/inventory.md` mapeia fluxos principais: cadastro manual, listagem, edicao, imports, grades, automacao, undo/redo e painel operacional.
- 2026-07-08: `python -m pytest` passou com 135 testes selecionados aprovados e 5 desmarcados.
- 2026-07-08: `cd frontend-ts; npm run test:logic` passou com 89 testes de logica frontend aprovados.
- 2026-07-08: `cd frontend-ts; npm run build` passou e nao deixou diff em `frontend-ts/dist`.
- 2026-07-08 rodada 2: `codegraph status C:\Users\user\.codex\worktrees\e6dd\LojaSync` retornou `Not initialized`; a rodada seguiu com leitura direta e registrou o risco para evitar confiar no indice errado.
- 2026-07-08 rodada 2: primeira tentativa de `uvicorn` sem `Set-Location` falhou com `ModuleNotFoundError: No module named 'app'` por problema do shell da automacao; a reproducao real foi feita com `Set-Location -LiteralPath`.
- 2026-07-08 rodada 2: `http://127.0.0.1:8800/` renderizou painel LojaSync com 3 itens visiveis, sem overlay e sem `console.error`/`console.warn` relevantes no Browser integrado.
- 2026-07-08 rodada 2: busca por `jaqueta` filtrou a lista para 1 item (`JAQUETA SOLIRA`) sem erro de console.
- 2026-07-08 rodada 2: `Invoke-WebRequest` confirmou `/health` 200, `/products` 200 e `/ts/` 307 para `/`.
- 2026-07-08 rodada 2: `python -m pytest tests/test_http_frontend.py` passou com 5 testes apos adicionar verificacao dos assets locais do `frontend-ts/dist/index.html`.
- 2026-07-08 rodada 2: `cd frontend-ts; npm ci` instalou dependencias locais ausentes para validacao; `npm run build` passou; `npm run test:logic` passou com 89 testes.

## Riscos

- Arvore de trabalho ja estava suja antes desta sessao; nao reverter nem misturar alteracoes alheias.
- Auth existe no codigo, mas nao e fluxo esperado de produto; rodadas futuras devem evitar tratar login/senha como prioridade diaria sem pedido explicito.
- Automacao depende de Windows, desktop interativo e Byte Empresa configurado; testes automatizados cobrem gates, nao sucesso real de cadastro.
- Importacao com LLM depende de runtime legado/configuracao externa; parser local e fallback devem ser validados separadamente.
- CodeGraph da worktree isolada `C:\Users\user\.codex\worktrees\e6dd\LojaSync` retornou `Not initialized`; proxima rodada deve inicializar ou confirmar se deve usar o indice da worktree principal antes de perguntas estruturais.
- Browser integrado falhou ao chamar `domSnapshot()` por incompatibilidade `incrementalAriaSnapshot`; smoke foi validado com leitura DOM pontual, screenshot, console e interacao.

## Historico de rodadas

| Rodada | Status | Agente/Data | Area | Entrega | Evidencia | Proxima recomendacao |
|---|---|---|---|---|---|---|
| 1/20 | concluida | Codex / 2026-07-08 | Diagnostico inicial | Criado ledger operacional do enxame diario, mapa de fluxos criticos, comandos de validacao e riscos para proximas rodadas | `codegraph status .`; `python -m pytest` 135 passed; `npm run test:logic` 89 passed; `npm run build` OK; leitura de `AGENTS.md`, `README.md`, `DocsDev/codegraph/inventory.md` | Rodada 2: subir app e fazer smoke test geral do painel principal, navegacao basica, console e rotas quebradas |
| 2/20 | concluida | Codex / 2026-07-08 | Smoke test geral | Painel principal abriu em `http://127.0.0.1:8800/`, rotas basicas responderam, busca filtrou lista e foi criado teste de regressao para assets locais do `dist/index.html` | Browser integrado sem console error/warn; screenshot do painel; busca `jaqueta` -> 1 item; `/health` 200; `/products` 200; `/ts/` 307; `python -m pytest tests/test_http_frontend.py` 5 passed; `npm run build` OK; `npm run test:logic` 89 passed | Rodada 3: validar autenticacao/compatibilidade, com foco em auth desabilitado por padrao, auth habilitado opcional, logout/sessao e redirecionamentos sem tratar login como fluxo principal |
| 3/20 | pendente | - | Autenticacao/compatibilidade | - | - | Adaptar para confirmacao de fluxo sem auth e redirects opcionais |
| 4/20 | pendente | - | Cadastro/onboarding | - | - | Primeiro cadastro manual e campos obrigatorios |
| 5/20 | pendente | - | Jornada principal | - | - | Cadastrar/importar produto e preparar execucao |
| 6/20 | pendente | - | Formularios comuns | - | - | Validacao de inputs de produto/preco/quantidade |
| 7/20 | pendente | - | CRUD principal | - | - | Criar, editar, excluir/restaurar ou desfazer produto |
| 8/20 | pendente | - | Listagens | - | - | Busca, filtros, ordenacao e estados vazios |
| 9/20 | pendente | - | Detalhe/deep link equivalente | - | - | Modal de grades/item inexistente/voltar |
| 10/20 | pendente | - | Permissoes e papeis | - | - | Equivalente: auth opcional e rotas protegidas sem virar produto |
| 11/20 | pendente | - | Reload e persistencia | - | - | Refresh, storage local e historico |
| 12/20 | pendente | - | Estados loading/erro/vazio/sucesso | - | - | Import, API offline e feedback |
| 13/20 | pendente | - | Mobile/responsivo | - | - | Layout da tabela/formulario |
| 14/20 | pendente | - | Rede lenta/falha API | - | - | Timeout/erro de API e mensagens |
| 15/20 | pendente | - | Acoes duplicadas/corrida | - | - | Submit duplo e locks de loading |
| 16/20 | pendente | - | Integracoes criticas | - | - | Import/automacao/upload sem disparar acoes reais |
| 17/20 | pendente | - | Acessibilidade pratica | - | - | Foco, teclado, labels e erros |
| 18/20 | pendente | - | Console/logs/erros silenciosos | - | - | Console, promise rejection e warnings |
| 19/20 | pendente | - | Testes de regressao | - | - | Cobertura dos bugs achados |
| 20/20 | pendente | - | Revisao final | - | - | Consolidar riscos e proximas prioridades |
