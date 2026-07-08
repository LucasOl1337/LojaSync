# Inventario Inicial de Componentes

> HISTORICO / SUPERSEDED: este inventario registra uma fase antiga da migracao.
> Ele nao descreve o runtime atual do LojaSync v1.2.x. Para estado vivo, use
> `README.md` e `DocsDev/codegraph/inventory.md`.
>
> Evidencia atual: `app/bootstrap/wiring/container.py` instancia
> `SQLiteProductRepository`, `SQLiteBrandRepository`, `SQLiteMarginSettingsStore`
> e `SQLiteMetricsStore`; `app/infrastructure/persistence/sqlite/stores.py`
> migra JSON/JSONL legado apenas quando as tabelas SQLite estao vazias.

## Essenciais no runtime atual

- launcher do webapp
- backend FastAPI
- frontend estatico real
- persistencia JSONL de produtos (historico: hoje e entrada legada para migracao ao SQLite)
- persistencia de marcas, margem e metricas
- importacao de romaneio
- parser de grades
- automacao local PyAutoGUI
- automacao remota por websocket
- LLM3
- monitor do LLM

## Legado fora da nova base

- desktop GUI antigo
- parser managers antigos
- artefatos historicos de build
- sistema de temas nao conectado ao frontend real
- utilitarios manuais fora do runtime principal

## Nucleo iniciado nesta fase

- dominio de produtos
- repositorio de produtos
- persistencia JSONL (historico: substituida como runtime principal por SQLite)
- settings de margem
- API HTTP inicial
