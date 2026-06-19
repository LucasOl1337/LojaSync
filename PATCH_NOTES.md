# LojaSync v1.2.0 - Patch Notes

Data: 2026-06-19

Esta release consolida o LojaSync como uma aplicacao local mais resiliente: persistencia SQLite, historico real de desfazer/refazer, importacao com validacao mais forte, melhor tratamento de grades e um painel React mais operacional para uso diario no cadastro de produtos.

## Destaques

- Persistencia principal migrada para SQLite local em `data/lojasync.db`.
- Desfazer/refazer persistente para edicoes e acoes em lote de produtos.
- Importacao de romaneios com validacao local antes do fallback por LLM.
- Pipeline LLM com chunks estruturados, retry de trechos incompletos e fallback visual por recortes verticais.
- Consolidacao de grades por lote de importacao, preservando diferencas de preco e nome.
- Centro de execucao no frontend com status de automacao, prontidao e botao de parada sempre acessivel.
- Patch notes, README expandido e documentacao tecnica em `DocsDev/`.

## Backend e persistencia

- Adicionado `SQLiteProductRepository`, `SQLiteBrandRepository`, `SQLiteMarginSettingsStore`, `SQLiteMetricsStore` e `SQLiteAuthStore`.
- Produtos ativos, historico de produtos, marcas, margem, metricas e autenticacao agora compartilham a mesma base SQLite local.
- A primeira inicializacao migra dados legados de `products_active.jsonl`, `products_history.jsonl`, `brands.json`, `margem.json`, `metrics.json` e `auth.json` quando as tabelas ainda estao vazias.
- A tabela de produtos passou a preservar `source_type`, `import_batch_id`, `import_source_name` e `pending_grade_import`.
- A ordenacao de produtos ativos ganhou coluna `position`, reduzindo instabilidade visual apos reordenar a lista.
- O endpoint `/health` e o metadata FastAPI agora reportam a versao `1.2.0`.

## Desfazer/refazer

- Adicionado store de historico em `app/infrastructure/persistence/files/undo_history.py`.
- O backend passou a expor:
  - `GET /actions/history`
  - `POST /actions/history/snapshot`
  - `POST /actions/history/undo`
  - `POST /actions/history/redo`
- O historico e limitado aos 50 snapshots mais recentes.
- Snapshots sao clonados antes de serem armazenados, evitando mutacao acidental por referencia.
- O arquivo `data/undo_redo_history.json` e local de runtime e foi incluido no `.gitignore`.

## Produtos, grades e limpeza

- `ProductService` passou a centralizar snapshots, restauracao, reordenacao, aplicacao de margem, formatacao de codigos, restauracao de codigos originais e melhoria de descricoes.
- A consolidacao de grades agora trabalha por lotes pendentes e nao mistura produtos manuais com produtos importados.
- Produtos com mesmo codigo e nome, mas precos diferentes, ficam em grupos separados.
- Pequenas diferencas numericas de preco vindas de LLM podem ser reunidas quando ficam dentro da tolerancia configurada.
- Adicionada acao para criar conjunto a partir de dois itens selecionados.
- Adicionada limpeza de descricoes por numeros, caracteres especiais e termos informados/sugeridos.
- Removidos os modulos antigos de pos-processamento de produtos e seus testes especificos, substituidos por fluxo integrado ao `ProductService`.

## Importacao de romaneios e NF-e

- O job de importacao agora tenta parser local primeiro e aprova o lote quando a validacao da nota fecha.
- Quando o parser local nao e suficiente, o job registra fallback LLM com eventos e metricas mais claras.
- O texto estruturado da nota e dividido em chunks com faixa esperada de codigos e quantidade esperada de linhas.
- Chunks incompletos podem ser subdivididos e reprocessados automaticamente.
- Em PDFs/imagens, o pipeline pode tentar paginas completas e depois recortes verticais para reduzir perdas de linhas.
- A resposta de importacao passou a retornar:
  - `grades_disponiveis`
  - `total_grades_disponiveis`
  - `imported_keys`
  - `import_batch_id`
  - `metrics`
- Itens importados passam a carregar origem, nome do arquivo e lote para diagnostico e acoes posteriores.

## Frontend React

- Adicionado centro de execucao dedicado para automacao, cadastro completo, cadastro em massa, grades e parada.
- Adicionados controles de desfazer/refazer na lista de produtos, com labels e estado vindos do backend.
- Atalhos globais de undo/redo respeitam foco em campos editaveis.
- O painel de ferramentas de produtos ganhou sugestoes de termos suspeitos para limpeza de descricao.
- A tela passou a destacar produtos importados, pendencias de grades e diagnosticos de importacao.
- O historico recente de importacoes e o diario operacional usam `localStorage` com limites e coercao defensiva.
- A formatacao de valores, labels de status, mensagens de importacao e resumo operacional foi reforcada por testes.
- O CSS do frontend TypeScript foi expandido para uma interface mais densa, legivel e orientada a operacao.

## Auth e runtime

- A autenticacao passa a usar `SQLiteAuthStore`, mantendo compatibilidade com `data/auth.json` para migracao inicial.
- O container principal injeta SQLite, historico de undo/redo e conector HTTP de autenticacao de forma explicita.
- O runtime segue separado entre API principal e auth runtime, com portas padrao `8800` e `8810`.

## Documentacao

- README atualizado com visao geral, stack, estrutura, comandos, URLs, dados locais, fluxos e validacao.
- Adicionado este `PATCH_NOTES.md` como historico detalhado da release.
- Adicionada pasta `DocsDev/` com blueprint, auditorias, plano de produto, handoff tecnico e materiais de divulgacao/dev.
- `frontend-ts/dist/` passa a ser incluido como build estatico versionado da release.

## Arquivos locais e compatibilidade

- `data/lojasync.db`, `data/lojasync.db-*`, `data/auth.json` e `data/undo_redo_history.json` nao devem ser versionados.
- Os JSON/JSONL antigos continuam sendo usados como fonte de migracao quando o banco SQLite esta vazio.
- Maquinas ja clonadas podem atualizar com `patchatt.bat`, desde que a arvore local esteja limpa.

## Validacao da release

- `python -m pytest`: 131 passed, 5 deselected.
- `cd frontend-ts && npm run build`: passou.
- `cd frontend-ts && npm run test:logic`: 88 passed.

## Riscos conhecidos

- A automacao desktop continua dependente de Windows, posicoes de tela e disponibilidade do Byte Empresa.
- O fallback por LLM depende do servico configurado em `LLM_BASE_URL`/`LLM_HOST`/`LLM_PORT`.
- Bases locais existentes em SQLite nao sao sobrescritas pelos arquivos JSONL legados; a migracao so ocorre quando as tabelas estao vazias.
