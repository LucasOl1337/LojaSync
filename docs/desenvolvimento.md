# Desenvolvimento

## Iniciar

No Windows:

```bat
Iniciar LojaSync.bat
```

Execucao manual com ambiente ja preparado:

```powershell
python launcher.py
```

A aplicacao principal e a API usam `http://127.0.0.1:8800`. O launcher usa auth somente com `--enable-auth`. O frontend principal vem de `frontend-ts/dist/`; `/legacy/` mantem a interface antiga quando seus arquivos estaticos existem.

## Validar

```powershell
python -m pytest
cd frontend-ts
npm run test:logic
npm run build
```

Use o teste ligado ao escopo durante o trabalho. Rode os tres comandos antes de preparar release. O build sobrescreve `frontend-ts/dist/`, que e versionado; revise e inclua o bundle quando a fonte da interface mudar.

## Navegar

O indice local do CodeGraph fica em `.codegraph/`:

```powershell
codegraph status .
codegraph context <termo>
codegraph callers <simbolo>
codegraph callees <simbolo>
codegraph impact <simbolo>
```

Use-o SOMENTE para perguntas estruturais ou impacto. Se estiver divergente dos arquivos, execute `codegraph index . --force`.

## Dados

O runtime grava em `data/lojasync.db` e `data/undo_redo_history.json`. Repositorios SQLite podem importar JSON/JSONL legado quando a base esta vazia. Testes que precisam de persistencia devem usar diretorio temporario.
