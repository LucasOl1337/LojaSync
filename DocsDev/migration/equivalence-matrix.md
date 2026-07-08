# Matriz de Equivalencia Funcional

> HISTORICO / SUPERSEDED: esta matriz descreve o alvo de uma fase antiga de
> migracao. Ela nao e a fonte atual para backend, API ou banco. Para o estado
> vivo do runtime v1.2.x, use `README.md` e `DocsDev/codegraph/inventory.md`.
>
> Evidencia atual: `app/bootstrap/wiring/container.py` injeta repositorios
> SQLite no container principal; `app/infrastructure/persistence/sqlite/stores.py`
> define as tabelas `active_products` e `history_products` e so carrega JSONL
> legado quando o banco ainda esta vazio.

Esta matriz define o que a nova base precisa reproduzir para ser considerada equivalente ao runtime atual.

## Runtime

- entrypoint principal via `launcher.py`
- API backend em porta local
- persistencia ativa em JSONL (historico: no runtime atual a persistencia principal e SQLite)
- leitura de configuracoes de margem e targets

## Produtos

- listar produtos ativos
- inserir produto
- atualizar produto
- remover produto
- limpar lista atual
- calcular preco final por margem padrao
- manter codigo original quando necessario

## Marcas e Totais

- listar marcas
- adicionar marca
- totais atuais
- totais historicos
- metricas agregadas

## Etapas Futuras Obrigatorias

- importacao de romaneio via LLM
- extracao de grades
- automacao local ByteEmpresa
- agentes remotos
- websocket de eventos de UI
- frontend completo

## Regra

Nenhum componente sera marcado como concluido sem teste ou validacao comparativa contra o projeto atual.
