# Productization Plan

## Objetivo

Levar o LojaSync do modo "projeto operado pela equipe" para o modo "produto distribuivel para terceiros", com foco em:

- instalacao simples
- atualizacao controlada
- licenciamento remoto
- visibilidade basica de uso
- suporte assistido por acesso remoto

## Estado Atual

O repositorio ja tem uma boa base para isso:

- `launcher.py` centraliza a subida do backend, frontend e auth runtime
- `Iniciar LojaSync.bat` prepara `.venv` e dependencias automaticamente
- o frontend TypeScript ja pode ser servido pelo backend
- existe autenticacao remota separada (`auth runtime`)
- os dados da instancia ficam centralizados em `data/`

Hoje, porem, o modelo ainda e de "aplicacao Python rodando a partir do repositorio". Isso funciona internamente, mas ainda nao e o formato ideal para entrega comercial.

## Recomendacao de Produto

### 1. Distribuicao local com instalador Windows

Primeira etapa recomendada:

- gerar um pacote Windows oficial do LojaSync
- instalar em `Program Files` ou pasta dedicada
- manter dados do cliente fora da pasta do programa
- criar atalho no desktop/menu iniciar
- abrir o sistema por um launcher oficial

Formato sugerido:

- `LojaSync Setup.exe` para instalacao
- `LojaSync Launcher.exe` para execucao

Observacao:

Empacotar o runtime novo como executavel e melhor do que depender de Python/Node instalados na maquina do cliente.

### 2. Dados separados do binario

Para distribuicao comercial, os dados nao devem ficar dentro da pasta do app.

Padrao recomendado:

- binarios em `%ProgramFiles%\\LojaSync`
- dados em `%ProgramData%\\LojaSync` ou `%LOCALAPPDATA%\\LojaSync`

Isso evita problemas de permissao, facilita backup e permite atualizar o programa sem mexer no banco e nas configuracoes do cliente.

## Launcher Comercial

O launcher ideal deve:

- verificar se a licenca da maquina esta valida
- iniciar backend, frontend e auth local
- gravar logs em pasta previsivel
- mostrar status simples de inicializacao
- permitir reiniciar servicos
- oferecer botao/acao de suporte remoto

O launcher atual ja cumpre parte da orquestracao, mas ainda tem perfil de ambiente tecnico. A evolucao natural e um launcher empacotado, com menos dependencia externa e com fluxo de erro mais amigavel.

## Licenciamento Recomendado

### O que nao fazer

Nao vale depender apenas de:

- senha local
- arquivo local facilmente editavel
- checagem puramente offline

Isso protege uso casual, mas nao resolve controle comercial.

### O que fazer

Implementar um servico simples de licenciamento em nuvem.

Cada cliente deve ter:

- `customer_id`
- `license_key`
- `installation_id`
- status da licenca (`trial`, `active`, `blocked`, `expired`)
- limite de instalacoes
- ultima sincronizacao

Fluxo sugerido:

1. instalador gera ou coleta um identificador da maquina
2. voce ativa a licenca do cliente
3. o launcher envia `license_key + installation_id` para a nuvem
4. a nuvem responde se a instalacao esta autorizada
5. o launcher salva um token assinado com expiracao curta
6. o app continua funcionando e renova a validacao periodicamente

Isso permite:

- bloquear licencas canceladas
- liberar reativacao apos troca de maquina
- limitar numero de PCs por cliente
- acompanhar quais instalacoes ainda existem

## Telemetria Minima

Voce nao precisa entrar em observabilidade pesada agora. Para a fase comercial inicial, basta registrar:

- cliente
- versao instalada
- data/hora da ultima validacao
- se a aplicacao abriu
- se a automacao rodou
- contagem basica de sessoes

Esses eventos podem ser enviados para uma API simples e gravados em banco leve.

## Estrategia Anti-Pirataria Realista

Nenhum desktop app e "impossivel de hackear". O objetivo certo e:

- dificultar copia casual
- impedir uso nao autorizado em escala
- manter o controle comercial centralizado

Combinacao recomendada:

- executavel oficial
- chave de licenca
- validacao periodica em nuvem
- token assinado com expiracao
- limite de instalacoes por cliente
- possibilidade de revogar remotamente

Isso ja atende muito bem um SaaS/desktop vertical pequeno ou medio.

## Fases Recomendadas

### Fase 1 - Productizacao minima

- empacotar o launcher novo
- separar pasta de dados da pasta do app
- definir instalador oficial
- padronizar logs
- exibir versao no app

### Fase 2 - Licenciamento comercial

- criar API de licencas
- ativacao por chave
- registro de instalacao
- revalidacao periodica
- tela de status da licenca

### Fase 3 - Operacao comercial

- painel simples para ver clientes ativos
- versao instalada por cliente
- ultima atividade
- bloqueio/desbloqueio de licenca
- reset de instalacao

## Stack Sugerida Para a Nuvem

Como o projeto ja e Python no desktop, a parte de licenca pode ser bem simples. Exemplos viaveis:

- FastAPI + SQLite/Postgres
- Cloudflare Workers + D1
- Supabase

O importante nao e a stack mais sofisticada; e a confiabilidade da validacao e a simplicidade de manutencao.

## Prioridade Pratica

Se a meta e comecar a vender sem travar o projeto, a ordem ideal e:

1. empacotar o app para instalacao simples
2. mover dados para pasta de runtime do cliente
3. criar licenciamento remoto leve
4. criar painel interno de clientes/licencas

## Conclusao

O LojaSync ja esta perto do ponto de venda, mas ainda precisa sair do formato "repositorio que sobe localmente" para o formato "produto instalado e licenciado".

O caminho recomendado nao e reinventar tudo:

- manter o runtime local
- empacotar com launcher oficial
- adicionar licenciamento remoto
- acompanhar uso por validacao e heartbeat leves

Isso entrega um produto mais profissional sem forcar uma reescrita completa da arquitetura atual.
