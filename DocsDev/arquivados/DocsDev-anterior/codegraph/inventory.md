# Inventario CodeGraph - LojaSync

Fonte principal: CodeGraph 0.9.4, indice final com 209 arquivos, 4.298 nos e 10.364 arestas. Complementado por leitura direta de rotas, servicos e launcher quando necessario para confirmar endpoints e comportamento real.

## 1. Funcoes de uso do cliente / usuario comum

### Cadastro manual de produtos

- Nome: Cadastro manual de produto.
- Descricao: Cria produto com nome, codigo, quantidade, preco, categoria, marca, preco final, descricao, cores e grades.
- Arquivos relacionados: `frontend-ts/src/App.tsx`, `frontend-ts/src/productEntryPanel.tsx`, `frontend-ts/src/productForm.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`, `app/application/products/service.py`, `app/domain/products/entities.py`.
- Como e acessada/usada: UI principal chama `createProduct`, que envia `POST /products`; backend normaliza produto e persiste em SQLite.
- Dependencias internas: `ProductService`, `SQLiteProductRepository`, `SQLiteBrandRepository`, margem padrao e `publish_state_changed`.
- Status: funcional.
- Observacoes tecnicas: o produto manual recebe `source_type="manual"` e `pending_grade_import=False`.

### Listagem, busca, filtros e revisao de produtos

- Nome: Operacao da lista de produtos.
- Descricao: Exibe produtos, busca por texto, filtros rapidos, indicadores de revisao, ordenacao visual e estados vazios.
- Arquivos relacionados: `frontend-ts/src/App.tsx`, `frontend-ts/src/productTable.tsx`, `frontend-ts/src/productTableRow.tsx`, `frontend-ts/src/productFilters.ts`, `frontend-ts/src/productOrdering.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`.
- Como e acessada/usada: frontend carrega `GET /products`, aplica filtros locais e renderiza tabela.
- Dependencias internas: `fetchProducts`, `ProductListResponse`, `buildDisplayedProducts`, `filterProductsByQuickFilter`, `filterProductsBySearch`.
- Status: funcional.
- Observacoes tecnicas: filtros sao majoritariamente client-side; reordenacao persistente usa `POST /actions/reorder`.

### Edicao inline e acoes em lote

- Nome: Edicao e tratamento em lote.
- Descricao: Edita campos de produto, aplica categoria/marca, formata/restaura codigos, aplica margem, melhora descricoes, junta duplicados e cria conjuntos.
- Arquivos relacionados: `frontend-ts/src/editableProductCell.tsx`, `frontend-ts/src/productEditing.ts`, `frontend-ts/src/productListControls.tsx`, `frontend-ts/src/productListToolPanels.tsx`, `frontend-ts/src/descriptionCleanup.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`, `app/application/products/service.py`.
- Como e acessada/usada: controles da tabela chamam endpoints `/products/{ordering_key}` e `/actions/*`.
- Dependencias internas: `ProductService.update_product`, `apply_category`, `apply_brand`, `join_duplicates`, `format_codes`, `restore_original_codes`, `apply_margin_to_products`, `improve_descriptions`, `create_set_by_keys`.
- Status: funcional.
- Observacoes tecnicas: algumas operacoes exigem confirmacao no frontend; backend publica eventos de atualizacao para `products`, `totals`, `brands`, `margin` ou `history`.

### Historico de desfazer/refazer

- Nome: Undo/redo persistente de produtos.
- Descricao: Registra snapshots, desfaz e refaz alteracoes destrutivas ou em lote.
- Arquivos relacionados: `frontend-ts/src/keyboardShortcuts.ts`, `frontend-ts/src/uiFormatting.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`, `app/application/products/service.py`, `app/infrastructure/persistence/files/undo_history.py`.
- Como e acessada/usada: UI chama `/actions/history`, `/actions/history/snapshot`, `/actions/history/undo` e `/actions/history/redo`; atalhos globais detectam undo/redo.
- Dependencias internas: `JsonUndoRedoHistoryStore`, limite `MAX_UNDO_HISTORY=50`, `ProductService.restore_snapshot`.
- Status: funcional.
- Observacoes tecnicas: o historico e salvo em JSON separado, nao dentro do SQLite operacional.

### Importacao de romaneio por IA ou leitura local

- Nome: Importacao assistida de romaneio.
- Descricao: Recebe PDF/texto e importa produtos pelo modo escolhido pelo usuario: IA/LLM ou leitura local.
- Arquivos relacionados: `frontend-ts/src/importStagePanel.tsx`, `frontend-ts/src/importDiagnostics.tsx`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_imports.py`, `app/interfaces/api/http/jobs/runtime.py`, `app/application/imports/parsing.py`, `app/application/imports/job_validation.py`, `app/application/imports/local_experiment.py`.
- Como e acessada/usada: `Importar com IA` chama `POST /actions/import-romaneio`, cria job em background e pula o parser local; `Importar com leitura local` chama `POST /actions/import-romaneio-local-experiment`.
- Dependencias internas: `run_import_job`, `parse_local_romaneio_experiment`, `build_local_parser_products`, `select_llm_import_result`, `evaluate_import_validation`, `ProductService.create_many`.
- Status: parcial.
- Observacoes tecnicas: IA/LLM depende do runtime externo/legado e de configuracao de porta. A leitura local e uma opcao independente; nenhum modo deve ser apresentado como caminho principal ou fallback do outro.

### Importacao por leitura local

- Nome: Importacao por leitura local.
- Descricao: Executa o modo local escolhido pelo usuario sem job assincrono, usando parser local e salvando texto extraido.
- Arquivos relacionados: `frontend-ts/src/api.ts`, `frontend-ts/src/App.tsx`, `app/interfaces/api/http/route_local_import_experiment.py`, `app/application/imports/local_experiment.py`, `app/application/imports/job_validation.py`.
- Como e acessada/usada: UI chama `POST /actions/import-romaneio-local-experiment`.
- Dependencias internas: `parse_local_romaneio_experiment`, `build_local_import_text`, `save_romaneio_text`, `ProductService.create_many`.
- Status: funcional.
- Observacoes tecnicas: retorna `422` quando o parser local nao encontra itens importaveis; marca metricas com `selected_source=local_parsing_import`.

### Extracao e consolidacao de grades

- Nome: Grades por produto e por lote de importacao.
- Descricao: Permite editar grades por item, detectar divergencias, importar grades pendentes e consolidar produtos em grade.
- Arquivos relacionados: `frontend-ts/src/gradeModal.tsx`, `frontend-ts/src/gradeLogic.ts`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_products.py`, `app/interfaces/api/http/route_imports.py`, `app/domain/grades/parser.py`, `app/domain/products/grade_utils.py`, `app/application/products/service.py`.
- Como e acessada/usada: modal de grades chama patch de produto; parser de grades usa `/actions/parser-grades`; consolidacao usa `/actions/join-grades`.
- Dependencias internas: `normalize_grades_map`, `sort_grade_items`, `ProductService.update_grades_by_identifier`, `ProductService.join_with_grades`, `parse_grade_extraction`.
- Status: funcional.
- Observacoes tecnicas: consolidacao preserva lotes pendentes e evita misturar produtos manuais quando processa `pending_grade_import`.

### Automacao do Byte Empresa e GradeBot

- Nome: Centro de execucao de automacao.
- Descricao: Executa cadastro em massa, cadastro completo, gradebot individual/lote/produtos, captura coordenadas, consulta contexto nativo e cancela execucao.
- Arquivos relacionados: `frontend-ts/src/executionCenterPanel.tsx`, `frontend-ts/src/settingsModal.tsx`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_automation.py`, `app/application/automation/service.py`, `app/application/automation/byteempresa/*`, `Legacy/automation/gradebot/gradebot.py`, `Legacy/engine/modules/automation/byte_empresa.py`.
- Como e acessada/usada: UI chama `/automation/*` e `/automation/grades/*`; backend inicia workers em thread.
- Dependencias internas: `AutomationService`, `ProductService`, `pyautogui`, opcional `pywinauto`, configuracoes `targets.json`, `desktop_automation.json` e config legado do GradeBot.
- Status: parcial.
- Observacoes tecnicas: funcionalidade depende de Windows, ambiente desktop interativo, coordenadas calibradas e pacotes nativos disponiveis. O codigo tem protecoes por `RuntimeError` quando `pyautogui` ou configuracao faltam.

### Autenticacao administrativa

- Nome: Login, bootstrap, logout e troca de senha.
- Descricao: Protege a UI principal com senha local, cookie HTTP-only e runtime de autenticacao separado.
- Arquivos relacionados: `frontend-ts/src/AuthShell.tsx`, `frontend-ts/src/api.ts`, `app/interfaces/api/http/route_auth.py`, `app/interfaces/auth_api/http/routes.py`, `app/application/auth/service.py`, `app/infrastructure/auth/http_connector.py`, `app/infrastructure/persistence/sqlite/stores.py`.
- Como e acessada/usada: `AuthShell` chama `/auth/session`, `/auth/bootstrap`, `/auth/login`, `/auth/logout`, `/auth/change-password`; backend principal delega ao auth runtime em `:8810`.
- Dependencias internas: `HttpAuthConnector`, `AuthService`, `SQLiteAuthStore`, cookie `auth_cookie_name`.
- Status: funcional.
- Observacoes tecnicas: launcher inicia o auth runtime apenas quando `--enable-auth` e usado; sem auth habilitado, o conector retorna sessao aberta conforme configuracao.

### Painel operacional e notificacoes

- Nome: Saude operacional, diario e notificacoes.
- Descricao: Mostra status de API, socket de eventos, importacoes recentes, diario de operacoes, prontidao de execucao e toasts/dialogos.
- Arquivos relacionados: `frontend-ts/src/operationalHealthPanel.tsx`, `frontend-ts/src/operationalSummaryPanel.tsx`, `frontend-ts/src/appNotifications.ts`, `frontend-ts/src/noticeDialog.tsx`, `frontend-ts/src/noticeToastStack.tsx`, `frontend-ts/src/uiFormatting.ts`, `app/shared/ui_events.py`, `app/interfaces/api/http/app.py`.
- Como e acessada/usada: `App.tsx` abre WebSocket de eventos e tambem usa polling fallback.
- Dependencias internas: eventos `state_changed`, `job_updated`, `connected`; `buildOperationalHealthChips`, `buildExecutionReadiness`.
- Status: funcional.
- Observacoes tecnicas: se WebSocket falhar, a UI continua atualizando por polling.

## 2. Funcoes de estrutura e backend

### Inicializacao dos runtimes

- Nome: Launcher principal.
- Descricao: Prepara frontend TypeScript, inicia backend FastAPI, servidor frontend estatico, auth runtime, LLM legado e monitor LLM quando disponiveis.
- Arquivos relacionados: `launcher.py`, `app/bootstrap/launcher/env.py`, `app/bootstrap/launcher/frontend.py`, `app/bootstrap/launcher/net.py`, `app/interfaces/api/http/app.py`, `app/interfaces/auth_api/http/app.py`.
- Como e acessada/usada: `python launcher.py` ou `Iniciar LojaSync.bat`.
- Dependencias internas: `uvicorn`, `create_app`, `create_auth_app`, `ensure_typescript_frontend_ready`, modulos legados `LLM3.launcher` e `webapp.llm_monitor`.
- Status: funcional.
- Observacoes tecnicas: preserva wrappers retrocompativeis no fim de `launcher.py` para testes e chamadas antigas.

### Aplicacao FastAPI principal

- Nome: Backend HTTP principal.
- Descricao: Monta CORS, middleware de request/auth/cache, rotas API, frontend TS e frontend legado.
- Arquivos relacionados: `app/interfaces/api/http/app.py`, `app/interfaces/api/http/routes.py`, `app/interfaces/api/http/route_*.py`.
- Como e acessada/usada: `create_app()` pelo launcher/uvicorn.
- Dependencias internas: `build_container`, `CORSMiddleware`, `StaticFiles`, `publish_state_changed`.
- Status: funcional.
- Observacoes tecnicas: monta `/legacy` quando existe frontend legado e redireciona `/ts` para raiz.

### Container de dependencias

- Nome: Wiring de aplicacao.
- Descricao: Instancia settings, paths, conector de auth, repositorios SQLite, historico undo/redo, ProductService e AutomationService.
- Arquivos relacionados: `app/bootstrap/wiring/container.py`, `app/bootstrap/wiring/auth_container.py`, `app/shared/config/settings.py`, `app/shared/paths/runtime_paths.py`.
- Como e acessada/usada: `create_app()` coloca container em `app.state.container`; auth runtime usa `build_auth_container`.
- Dependencias internas: `SQLiteProductRepository`, `SQLiteBrandRepository`, `SQLiteMarginSettingsStore`, `SQLiteMetricsStore`, `SQLiteAuthStore`, `JsonUndoRedoHistoryStore`.
- Status: funcional.
- Observacoes tecnicas: SQLite e a fonte principal; arquivos JSON/JSONL sao migrados quando a base esta vazia.

### Persistencia SQLite e migracao de legado

- Nome: Repositorios locais.
- Descricao: Mantem produtos ativos, historico, marcas, margem, metricas e auth em `data/lojasync.db`.
- Arquivos relacionados: `app/infrastructure/persistence/sqlite/stores.py`, `app/infrastructure/persistence/jsonl/stores.py`, `app/infrastructure/persistence/files/settings_files.py`, `app/infrastructure/persistence/files/auth_store.py`.
- Como e acessada/usada: services chamam repositorios por interfaces de dominio.
- Dependencias internas: `Product`, `Metrics`, `AuthConfig`, paths de arquivos legados.
- Status: funcional.
- Observacoes tecnicas: `jsonl/stores.py` e stores de arquivo existem como compatibilidade/legado; o container atual usa SQLite.

### Servico de produtos

- Nome: Regra de negocio de produtos.
- Descricao: Normaliza cadastro, garante ordering key unico, calcula margem, soma totais, mescla duplicados, consolida grades, registra metricas e historico.
- Arquivos relacionados: `app/application/products/service.py`, `app/domain/products/entities.py`, `app/domain/products/grade_utils.py`, `app/domain/products/money.py`, `app/domain/products/repository.py`.
- Como e acessada/usada: handlers de produto, importacao e automacao usam `ProductService`.
- Dependencias internas: repositorios de produtos/marcas/margem/metricas, `JsonUndoRedoHistoryStore`.
- Status: funcional.
- Observacoes tecnicas: arquivo grande e concentrado; e ponto critico para regressao em importacao, grades e automacao.

### Runtime de jobs de importacao

- Nome: Jobs em memoria para imports e parser de grades.
- Descricao: Cria jobs, atualiza estagios, guarda resultado em memoria e publica eventos.
- Arquivos relacionados: `app/interfaces/api/http/jobs/store.py`, `app/interfaces/api/http/jobs/runtime.py`, `app/interfaces/api/http/jobs/llm.py`, `app/interfaces/api/http/route_imports.py`.
- Como e acessada/usada: `BackgroundTasks` do FastAPI executam `run_import_job` e `run_grade_extraction_job`.
- Dependencias internas: parser local, LLM client, stores globais de job, `ProductService`.
- Status: funcional com risco operacional.
- Observacoes tecnicas: store em memoria perde jobs no restart; adequado para app desktop local, mas nao para ambiente multi-processo.

### Parser local de romaneio/NF-e

- Nome: Pipeline local de extracao.
- Descricao: Extrai texto de PDF/imagem, tenta tabelas PDF, OCR Windows, parsers por layouts e validacao de totais.
- Arquivos relacionados: `app/application/imports/local_experiment.py`, `app/application/imports/parsing.py`, `app/application/imports/pdf_text.py`, `app/application/imports/job_validation.py`.
- Como e acessada/usada: jobs de importacao e endpoint local experimental.
- Dependencias internas: OCR Windows quando necessario, normalizadores de preco/quantidade, heuristicas por fornecedor/layout.
- Status: funcional parcial.
- Observacoes tecnicas: muitas heuristicas especificas; cobertura de fornecedores novos e area de maior incerteza.

### Automacao desktop

- Nome: Orquestracao de automacao nativa/legada.
- Descricao: Controla execucao em background, estado ativo, cancelamento, failsafe de mouse, drivers nativos e GradeBot.
- Arquivos relacionados: `app/application/automation/service.py`, `app/application/automation/byteempresa/session.py`, `app/application/automation/byteempresa/catalog.py`, `app/application/automation/profiles.py`, `app/application/automation/product_payload.py`.
- Como e acessada/usada: rotas `/automation/*`.
- Dependencias internas: `ProductService`, `pyautogui`, `pywinauto` opcional, modulos em `Legacy/`.
- Status: parcial.
- Observacoes tecnicas: alto acoplamento com estado de desktop; testes cobrem gates nativos, mas execucao real depende de maquina configurada.

### Eventos de UI

- Nome: Canal de eventos em memoria.
- Descricao: Publica alteracoes de estado e jobs para o frontend por WebSocket.
- Arquivos relacionados: `app/shared/ui_events.py`, `app/interfaces/api/http/app.py`, rotas que chamam `publish_state_changed`.
- Como e acessada/usada: frontend conecta via `buildWsUrl` e escuta eventos; polling e fallback.
- Dependencias internas: subscribers in-memory e rotas de backend.
- Status: funcional.
- Observacoes tecnicas: eventos nao persistem e nao atravessam multiplos processos.

### Codigo legado e compatibilidade

- Nome: Frontend/engine legado.
- Descricao: Mantem webapp JS legado, desktop GUI Tkinter, LLM3 e modulos de automacao antigos.
- Arquivos relacionados: `Legacy/`, `app/interfaces/webapp/static/script.js`, `Legacy/engine/webapp/*`, `Legacy/engine/legacy/desktop_gui/*`.
- Como e acessada/usada: `/legacy/` serve frontend legado; automacao atual ainda carrega `Legacy/automation/gradebot/gradebot.py` e `Legacy/engine/modules/automation/byte_empresa.py`.
- Dependencias internas: imports dinamicos em `AutomationService`, launcher para `LLM3` e `webapp.llm_monitor`.
- Status: parcial / duplicado.
- Observacoes tecnicas: ha duplicidade entre `Legacy/engine/webapp/script.js` e `app/interfaces/webapp/static/script.js`. Parte do legado e runtime real, parte parece preservacao historica.

## 3. Funcoes de estrutura frontend

### Shell React principal

- Nome: `App.tsx`.
- Descricao: Componente central com estado de produtos, automacao, imports, grades, settings, dialogs, notificacoes e sincronizacao.
- Arquivos relacionados: `frontend-ts/src/App.tsx`, `frontend-ts/src/appConfig.ts`, `frontend-ts/src/appLocalState.ts`, `frontend-ts/src/uiFormatting.ts`.
- Como e acessada/usada: `frontend-ts/src/main.tsx` renderiza `AuthShell`, que renderiza `App`.
- Dependencias internas: `api.ts`, componentes de tabela/formulario/importacao/automacao/modais.
- Status: funcional com risco de manutencao.
- Observacoes tecnicas: arquivo tem quase 100 KB e concentra muitos fluxos de UI; candidatos a futuras extracoes.

### Cliente API

- Nome: `frontend-ts/src/api.ts`.
- Descricao: Centraliza base URL, parsing JSON, tratamento de erro, WebSocket URL e todas as chamadas HTTP.
- Arquivos relacionados: `frontend-ts/src/api.ts`, `frontend-ts/src/types.ts`.
- Como e acessada/usada: todos os componentes chamam funcoes exportadas como `fetchProducts`, `importRomaneio`, `startAutomationComplete`, `undoHistorySnapshot`.
- Dependencias internas: tipos de dominio TS e endpoints FastAPI.
- Status: funcional.
- Observacoes tecnicas: detecta resposta HTML inesperada para evitar mensagens confusas quando backend devolve pagina.

### Shell de autenticacao

- Nome: `AuthShell`.
- Descricao: Decide entre loading, setup, login e app; gerencia logout e troca de senha.
- Arquivos relacionados: `frontend-ts/src/AuthShell.tsx`, `frontend-ts/src/api.ts`, `frontend-ts/src/types.ts`.
- Como e acessada/usada: entrada raiz em `main.tsx`.
- Dependencias internas: endpoints `/auth/*`.
- Status: funcional.
- Observacoes tecnicas: se auth estiver desabilitado, entra direto no app.

### Tabela e controles de produtos

- Nome: Lista operacional.
- Descricao: Renderiza tabela, linha de produto, celula editavel, controles de filtros, busca, modos de edicao, ordenacao e conjuntos.
- Arquivos relacionados: `frontend-ts/src/productTable.tsx`, `frontend-ts/src/productTableRow.tsx`, `frontend-ts/src/editableProductCell.tsx`, `frontend-ts/src/productListControls.tsx`, `frontend-ts/src/productListToolPanels.tsx`.
- Como e acessada/usada: `App.tsx` passa produtos filtrados, callbacks e estado de automacao.
- Dependencias internas: `productFilters`, `productEditing`, `productOrdering`, `descriptionCleanup`.
- Status: funcional.
- Observacoes tecnicas: ha bloqueios de acoes por modo de edicao/ordenacao/conjunto para evitar operacoes conflitantes.

### Formulario de produto e precificacao

- Nome: Entrada e calculos locais.
- Descricao: Normaliza quantidade/preco, calcula preview de preco final, valida campos obrigatorios e totais da lista.
- Arquivos relacionados: `frontend-ts/src/productEntryPanel.tsx`, `frontend-ts/src/productForm.ts`, `frontend-ts/src/productPricing.ts`, `frontend-ts/src/marginDialog.tsx`.
- Como e acessada/usada: formulario principal e dialogo de margem.
- Dependencias internas: `ProductPayload`, `parsePriceInput`, `calculateSalePricePreview`.
- Status: funcional.
- Observacoes tecnicas: validacao client-side complementa validacao/normalizacao do backend.

### Importacao no frontend

- Nome: UI de importacao e diagnosticos.
- Descricao: Seleciona arquivo, inicia importacao, acompanha job, exibe metricas, avisos, origem do parse e historico recente.
- Arquivos relacionados: `frontend-ts/src/importStagePanel.tsx`, `frontend-ts/src/importDiagnostics.tsx`, `frontend-ts/src/uiFormatting.ts`, `frontend-ts/src/appLocalState.ts`.
- Como e acessada/usada: painel principal do app.
- Dependencias internas: `importRomaneio`, `fetchImportStatus`, `fetchImportResult`, `importRomaneioLocalExperiment`.
- Status: funcional.
- Observacoes tecnicas: guarda historico recente no browser storage.

### Grade modal e logica de grades

- Nome: UI de grades.
- Descricao: Edita tamanhos/quantidades, organiza familias visuais, detecta divergencias e navega pendencias.
- Arquivos relacionados: `frontend-ts/src/gradeModal.tsx`, `frontend-ts/src/gradeLogic.ts`.
- Como e acessada/usada: aberto por `App.tsx` para produto selecionado.
- Dependencias internas: catalogo `/catalog/sizes`, config `/automation/grades/config`, `patchProduct`.
- Status: funcional.
- Observacoes tecnicas: salva ultima familia ativa no storage local.

### Settings e automacao

- Nome: Configuracao de automacao.
- Descricao: Captura coordenadas, edita targets, configura GradeBot, consulta diagnosticos Byte Empresa e aciona prepare/context.
- Arquivos relacionados: `frontend-ts/src/settingsModal.tsx`, `frontend-ts/src/executionCenterPanel.tsx`, `frontend-ts/src/api.ts`, `frontend-ts/src/appConfig.ts`.
- Como e acessada/usada: modal de configuracoes e centro de execucao.
- Dependencias internas: endpoints `/automation/targets`, `/automation/byteempresa/*`, `/automation/grades/config`.
- Status: parcial.
- Observacoes tecnicas: controles existem, mas sucesso depende de ambiente Windows e Byte Empresa aberto/configurado.

### Dialogos, notificacoes e estado local

- Nome: Infra UI de suporte.
- Descricao: Dialogos de confirmacao, aviso, input textual, toasts, persistencia de preferencias e diario operacional.
- Arquivos relacionados: `frontend-ts/src/confirmationDialog.tsx`, `frontend-ts/src/noticeDialog.tsx`, `frontend-ts/src/noticeToastStack.tsx`, `frontend-ts/src/textInputDialog.tsx`, `frontend-ts/src/appNotifications.ts`, `frontend-ts/src/appLocalState.ts`.
- Como e acessada/usada: `App.tsx` usa esses componentes para operacoes destrutivas e feedback.
- Dependencias internas: storage do navegador, tipos de `uiFormatting`.
- Status: funcional.
- Observacoes tecnicas: estado local e limitado e defensivo contra JSON invalido.

## Mapa dos principais fluxos do sistema

1. Inicializacao: `launcher.py` prepara `frontend-ts/dist`, sobe auth runtime opcional, LLM/monitor opcional, backend FastAPI e frontend estatico.
2. Boot da UI: `AuthShell` consulta `/auth/session`; se autenticado/desabilitado, renderiza `App`.
3. Carga inicial: `App` chama `GET /products`, `/totals`, `/brands`, `/settings/margin`, `/automation/status`, `/actions/history`.
4. Produto manual: `ProductEntryPanel` -> `createProduct` -> `POST /products` -> `ProductService.create_product` -> SQLite -> `publish_state_changed`.
5. Importacao: `ImportStagePanel` -> `POST /actions/import-romaneio` -> job -> parser local -> LLM fallback se necessario -> `ProductService.create_many`.
6. Grades: `GradeModal` -> `PATCH /products/{key}` ou `POST /actions/join-grades` -> `ProductService.update_grades_by_identifier` / `join_with_grades`.
7. Automacao: `ExecutionCenterPanel` -> `/automation/execute*` ou `/automation/grades/*` -> `AutomationService` -> `pyautogui`/`pywinauto`/Legacy -> `ProductService.record_automation_success`.
8. Undo/redo: UI registra snapshot -> store JSON -> undo/redo restaura lista ativa pelo `ProductService`.
9. Atualizacao de UI: rotas publicam eventos -> WebSocket em `App`; polling cobre falhas de socket.

## Dependencias principais

- Backend: FastAPI, Uvicorn, Pydantic, SQLite, PyAutoGUI, pywinauto opcional, OCR/PDF libs via requirements.
- Frontend: React 18, TypeScript, Vite, browser storage e WebSocket.
- Dados locais: `data/lojasync.db`, arquivos legados JSON/JSONL migrados, `data/undo_redo_history.json`, configs de automacao.
- Legado operacional: `Legacy/automation/gradebot/gradebot.py`, `Legacy/engine/modules/automation/byte_empresa.py`, `Legacy/engine/LLM3`, `Legacy/engine/webapp/llm_monitor.py`.

## Pontos criticos, riscos e inconsistencias

- CodeGraph estava inicialmente inconsistente: 188 arquivos indexados contra 209 apos `codegraph index . --force`.
- `ProductService` e `App.tsx` concentram muita logica e sao pontos de alto risco para mudancas.
- Jobs de importacao/grades ficam em memoria; restart perde status/resultados.
- Automacao depende fortemente de Windows, desktop interativo, coordenadas, janela correta e bibliotecas nativas.
- Fluxo LLM e monitor dependem de modulos legados e disponibilidade de portas; quando ausentes, importacao fica limitada ao parser local.
- `Legacy/` contem codigo duplicado e parcialmente conectado. Nao apagar sem mapear imports dinamicos.
- `frontend-ts/dist` esta versionado de proposito; CodeGraph indexa bundle gerado grande, mas o codigo fonte real fica em `frontend-ts/src`.
- Stores JSON/JSONL ainda existem para compatibilidade, mas a fonte operacional atual e SQLite.
- Repositorios abstratos em `app/domain/*/repository.py` levantam `NotImplementedError` por design; nao sao bug se usados via implementacoes concretas.

## Proximos passos recomendados

1. Manter `DocsDev/codegraph/codegraph-files.json` e `codegraph-status.txt` atualizados quando o repo mudar significativamente.
2. Extrair gradualmente partes de `frontend-ts/src/App.tsx` para hooks/componentes por fluxo: imports, grades, automacao e produto.
3. Dividir `ProductService` em servicos menores ou comandos internos para grades, undo/redo, bulk actions e metricas.
4. Persistir jobs de importacao se houver necessidade de recuperar status apos restart.
5. Documentar quais arquivos de `Legacy/` ainda sao runtime obrigatorio e quais sao apenas historicos.
6. Adicionar smoke tests de contrato frontend API para endpoints mais usados.
7. Rodar validacoes antes de release: `python -m pytest`, `cd frontend-ts && npm run build && npm run test:logic`.
