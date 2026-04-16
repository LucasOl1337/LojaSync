# Blueprint Arquitetural

## Objetivo

Reconstruir o LojaSync em uma base limpa, modular e testavel, mantendo o comportamento real do fluxo atual.

## Diretrizes

- comportamento antes de forma
- uma responsabilidade por modulo
- dominio sem framework
- infraestrutura isolada
- interfaces finas
- migracao controlada por equivalencia funcional

## Camadas

### Domain

Contem entidades, regras e contratos centrais:

- produtos
- marcas
- grades
- romaneio
- automacao
- metricas

Nao conhece FastAPI, PyAutoGUI, filesystem, httpx ou JSON.

### Application

Executa casos de uso:

- cadastro e manutencao de produtos
- configuracoes
- importacao de romaneio
- extracao de grades
- execucao de automacao
- agentes remotos

Coordena dominio e portas de infraestrutura.

### Infrastructure

Implementa adaptadores:

- persistencia JSONL
- arquivos de configuracao
- clientes LLM
- automacao local
- agentes remotos
- monitoramento
- conectores entre runtimes

### Interfaces

Expone o sistema para fora:

- API HTTP
- WebSocket
- frontend web
- auth API dedicada em runtime separado

## Separacao de Runtime

- o runtime principal nao implementa autenticacao localmente
- autenticacao roda em processo separado
- a comunicacao entre runtimes acontece por conectores HTTP
- cookies e sessao continuam compartilhados no host, mas a validacao pertence ao runtime de auth

## Fronteiras

- `interfaces -> application`
- `application -> domain`
- `application -> infrastructure` via contratos
- `domain` nao depende de nenhuma outra camada

## Estrategia de Portabilidade

Cada componente do runtime atual sera remontado em quatro passos:

1. identificar comportamento real
2. definir contrato novo
3. portar sem carregar ruinas do legado
4. validar equivalencia

## Meta de Arquivos

- arquivos pequenos
- nomes orientados por responsabilidade
- sem modulo unico concentrando tudo
- sem helpers genericos sem dono
