# LojaSync

Release atual: v1.2.7, 2026-07-14

LojaSync e uma plataforma desktop-web para cadastro assistido de produtos no Byte Empresa. O sistema combina painel web em React, API FastAPI, leitura de romaneios/NF-e, consolidacao de grades, persistencia local e automacao desktop para reduzir trabalho manual em cadastros de estoque.

## O que o sistema faz

- Importa romaneios e notas fiscais a partir de PDF/texto.
- Permite ao usuario escolher importacao por IA/LLM ou por leitura local.
- Detecta e consolida grades por lote de importacao.
- Mantem produtos ativos, historico, marcas, margem, metricas e autenticacao em SQLite local.
- Permite desfazer/refazer edicoes de produtos com historico persistente.
- Executa automacao desktop para cadastro completo, cadastro em massa e preenchimento de grades no ERP.
- Exibe painel operacional com progresso, prontidao de execucao, avisos de importacao e metricas.

## Stack

- Python 3.11+ com FastAPI, Uvicorn e Pydantic.
- SQLite local em `data/lojasync.db`.
- React 18 + TypeScript + Vite em `frontend-ts/`.
- PyAutoGUI/pywinauto para automacao Windows.
- Pipeline LLM opcional para leitura assistida quando o parser local nao aprova a nota.

## Estrutura principal

```text
LojaSync/
|- launcher.py
|- Iniciar LojaSync.bat
|- patchatt.bat
|- pyproject.toml
|- requirements.txt
|- README.md
|- PATCH_NOTES.md
|- app/
|  |- application/
|  |- bootstrap/
|  |- domain/
|  |- infrastructure/
|  `- interfaces/
|- frontend-ts/
|- data/
|- DocsDev/
`- Legacy/
```

## Inicializacao rapida

No Windows, use:

```bat
Iniciar LojaSync.bat
```

O iniciador procura Python 3.11/3.12, cria uma `.venv` local quando necessario, instala dependencias ausentes e sobe os runtimes principais.

Execucao manual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python launcher.py
```

## Frontend TypeScript

O launcher prepara o frontend automaticamente quando encontra `frontend-ts/`. Para trabalhar no frontend isolado:

```powershell
cd frontend-ts
npm ci
npm run dev
```

Build de producao:

```powershell
cd frontend-ts
npm run build
```

O diretorio `frontend-ts/dist/` e versionado nesta aplicacao para que a release tenha um frontend pronto mesmo em maquinas sem Node.js. Antes de publicar uma nova release, rode `npm run build` e inclua o `dist/` atualizado.

## URLs padrao

- Aplicacao principal: `http://127.0.0.1:8800`
- Backend/API: `http://127.0.0.1:8800`
- Swagger: `http://127.0.0.1:8800/docs`
- Auth runtime opcional: `http://127.0.0.1:8810` somente quando o launcher e iniciado com `--enable-auth`.
- Frontend legado: `http://127.0.0.1:8800/legacy/`
- LLM Monitor: `http://127.0.0.1:5174`

## Dados locais e migracao

A linha v1.2.x usa SQLite como base operacional principal. Na primeira execucao, os repositorios SQLite carregam dados legados de JSON/JSONL quando a base ainda esta vazia.

Arquivos locais importantes:

- `data/lojasync.db`: banco SQLite local, nao versionado.
- `data/products_active.jsonl` e `data/products_history.jsonl`: fontes legadas migradas para SQLite.
- `data/brands.json`, `data/margem.json`, `data/metrics.json` e `data/auth.json`: fontes legadas/configuracoes locais.
- `data/undo_redo_history.json`: historico local de desfazer/refazer, recriado em runtime e nao versionado.

## Principais fluxos

### Importacao de romaneio

1. O usuario escolhe `Importar com IA` ou `Importar com leitura local`.
2. No modo IA, o backend pula o parser local e processa o documento pelo runtime LLM.
3. No modo local, o parser local extrai os itens e valida quantidade, totais do documento e sinais de consistencia.
4. Os dois modos persistem os produtos aprovados usando os mesmos contratos de produto.
5. Produtos recebem metadados de lote (`import_batch_id`, origem e flag de grade pendente).

### Grades

- Produtos importados com grade detectavel ficam marcados como pendentes.
- A acao de importar grades processa todos os lotes pendentes sem misturar produtos manuais.
- A consolidacao preserva faixas de preco diferentes e nomes diferentes, evitando merges incorretos.

### Edicao reversivel

- O frontend registra snapshots antes de operacoes destrutivas ou em lote.
- O backend expoe `/actions/history`, `/actions/history/snapshot`, `/actions/history/undo` e `/actions/history/redo`.
- O historico e limitado a 50 snapshots e persiste entre reinicios locais.

### Automacao

- O centro de execucao centraliza cadastro completo, cadastro em massa, execucao de grades, importacao de grades e parada de emergencia.
- A automacao depende de Windows, permissao de interacao com a area de trabalho e posicoes configuradas do Byte Empresa.

## Comandos de validacao

Backend:

```powershell
python -m pytest
```

Frontend:

```powershell
cd frontend-ts
npm run build
npm run test:logic
```

## Atualizacao em outro PC

Para atualizar uma maquina ja clonada:

```bat
patchatt.bat
```

O script valida Git, exige arvore limpa e executa `git pull --ff-only origin main`.

## Patch notes

As notas completas da release estao em `PATCH_NOTES.md`.

## Observacoes operacionais

- Nao versionar bancos, credenciais, historicos de runtime, `.venv`, `node_modules` ou caches.
- `frontend-ts/dist/` e a excecao intencional de build estatico versionado para distribuicao local.
- O frontend React e a interface principal. O frontend legado fica disponivel em `/legacy/` para compatibilidade.
- O LLM e opcional para importacao; quando indisponivel, o parser local ainda pode aprovar notas consistentes.
- Para publicar nova release, atualize versoes, README, `PATCH_NOTES.md`, rode validacoes, commite, crie tag e publique no GitHub.
