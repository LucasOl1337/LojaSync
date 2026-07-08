# DailyBugSwarm - LojaSync

Memoria oficial do enxame continuo focado em bugs de uso diario do LojaSync.

## Objetivo

Aumentar progressivamente a confiabilidade dos fluxos usados por uma loja no dia a dia: iniciar o app, cadastrar produtos, importar romaneios, revisar listagens, editar dados, desfazer/refazer, lidar com grades e executar automacao local com feedback claro.

## Estado

- Rodada atual: 2/20
- Ultima atualizacao: 2026-07-08 15:27 -03:00
- Modo: sequencial, uma rodada por chat
- Branch observada: `main`
- Worktree efetiva desta sessao: `C:\projetos\LojaSync`
- Observacao operacional: o caminho informado `C:\Users\user\.codex\worktrees\98b0\LojaSync` nao foi aplicado pelo shell; comandos foram executados com `Set-Location -LiteralPath 'C:\projetos\LojaSync'`.

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
| Git | `git status --short` | arvore ja suja antes desta sessao |

## Bugs encontrados

| ID | Titulo | Severidade | Probabilidade | Impacto | Decisao | Evidencia |
|---|---|---|---|---|---|---|
| DBS-001 | Ausencia de ledger do enxame diario podia fazer agentes repetirem escopos ou priorizarem auth legado | P4 | alta | medio | corrigido | `DailyBugSwarm.md` criado com mapa, claims, comandos, riscos e historico |

## Bugs corrigidos

| ID | Titulo | Arquivos | Commit | Validacao |
|---|---|---|---|---|
| DBS-001 | Ledger inicial do enxame diario | `DailyBugSwarm.md` | `389dad1` | `codegraph status .`; `python -m pytest`; `npm run test:logic`; `npm run build` |

## Bugs pendentes

| ID | Titulo | Motivo para pendencia | Proxima acao |
|---|---|---|---|
| - | - | - | - |

## Escopos reivindicados

| Rodada | Area | Fluxo/tela | Arquivos pretendidos | Hipotese de bug/risco | Risco de conflito | Risco funcional | Como reproduzir | Como validar | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1/20 | Diagnostico inicial | Inicializacao, rotas principais e comandos | `DailyBugSwarm.md` | Sem mapa operacional, proximos agentes poderiam testar auth legado ou rotas erradas; risco de perder bug diario por escopo incorreto | Baixo; `DailyBugSwarm.md` novo, mas ha mudancas pre-existentes em docs que nao foram tocadas | Baixo; foco documental e validacao | Consultar CodeGraph, README/AGENTS, executar comandos de teste/build, revisar falhas objetivas | `codegraph status .`, `python -m pytest`, `npm run test:logic`, `npm run build` | concluido |

## Evidencias

- 2026-07-08: `codegraph status .` retornou indice atualizado em `C:\projetos\LojaSync` com 210 arquivos, 4.572 nos e 11.462 arestas.
- 2026-07-08: `AGENTS.md` e `README.md` confirmam produto principal sem login/senha obrigatorio, auth runtime apenas opcional via `--enable-auth`.
- 2026-07-08: `DocsDev/codegraph/inventory.md` mapeia fluxos principais: cadastro manual, listagem, edicao, imports, grades, automacao, undo/redo e painel operacional.
- 2026-07-08: `python -m pytest` passou com 135 testes selecionados aprovados e 5 desmarcados.
- 2026-07-08: `cd frontend-ts; npm run test:logic` passou com 89 testes de logica frontend aprovados.
- 2026-07-08: `cd frontend-ts; npm run build` passou e nao deixou diff em `frontend-ts/dist`.

## Riscos

- Arvore de trabalho ja estava suja antes desta sessao; nao reverter nem misturar alteracoes alheias.
- Auth existe no codigo, mas nao e fluxo esperado de produto; rodadas futuras devem evitar tratar login/senha como prioridade diaria sem pedido explicito.
- Automacao depende de Windows, desktop interativo e Byte Empresa configurado; testes automatizados cobrem gates, nao sucesso real de cadastro.
- Importacao com LLM depende de runtime legado/configuracao externa; parser local e fallback devem ser validados separadamente.

## Historico de rodadas

| Rodada | Status | Agente/Data | Area | Entrega | Evidencia | Proxima recomendacao |
|---|---|---|---|---|---|---|
| 1/20 | concluida | Codex / 2026-07-08 | Diagnostico inicial | Criado ledger operacional do enxame diario, mapa de fluxos criticos, comandos de validacao e riscos para proximas rodadas | `codegraph status .`; `python -m pytest` 135 passed; `npm run test:logic` 89 passed; `npm run build` OK; leitura de `AGENTS.md`, `README.md`, `DocsDev/codegraph/inventory.md` | Rodada 2: subir app e fazer smoke test geral do painel principal, navegacao basica, console e rotas quebradas |
| 2/20 | pendente | - | Smoke test geral | - | - | Subir app e navegar painel principal |
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
