# Matriz de Equivalencia Funcional

Esta matriz define o que a nova base precisa reproduzir para ser considerada equivalente ao runtime atual.

## Runtime

- entrypoint principal via `launcher.py`
- API backend em porta local
- persistencia ativa em JSONL
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
