# Planejamento De Features E QoL - 2026-06-14

Status documental: VIVO SECUNDARIO / PLANEJAMENTO. Este documento registra intencoes e fatias de QoL. Use `DocsDev/codegraph/inventory.md` e o codigo atual para confirmar quais itens ja viraram comportamento real.

## Objetivo

Criar uma nova rodada de evolucao do LojaSync focada em recursos novos e
qualidade de vida do usuario final, preservando os fluxos que ja funcionaram
por seis meses de uso real.

## Regra Base

- Nenhuma melhoria pode quebrar importacao, cadastro, grades, ordenacao,
  automacao ou autenticacao existentes.
- Cada rodada precisa de um auditor de review antes de virar implementacao.
- O auditor deve revisar comportamento atual, testes, build e verificacao em
  Chrome quando houver UI.
- Mudancas criativas entram primeiro como fatias reversiveis, pequenas e
  observaveis.
- Bugs teoricos sem incidencia real nao devem sequestrar a prioridade de
  features/QoL, salvo quando o risco for alto e a correcao for local.

## Rodada 1 - Confianca Operacional E Feedback

**Intencao:** melhorar a clareza do que esta acontecendo durante importacao,
auth, runtime e automacao, usando metricas e estados ja existentes.

**Features candidatas:**

- Painel de saude local: backend, auth runtime, WebSocket e estado da
  automacao em um resumo pequeno.
- Historico curto de importacoes recentes: origem usada, total importado,
  warnings, status final e tempo.
- Mensagens acionaveis para falhas de runtime, auth e importacao, sem stack
  ou erro bruto de parser.
- Indicadores de progresso mais ricos para importacao longa e fallback por
  imagem/LLM.

**Aceite:**

- O usuario entende se o problema esta no backend, auth, arquivo importado,
  parser local, LLM ou automacao.
- Nenhum endpoint de importacao ou persistencia muda de contrato.
- O fluxo atual continua funcionando quando as novas informacoes nao existem.

**Auditor de review:**

- Revisar que UI nova consome somente dados ja disponiveis ou endpoints
  pequenos de leitura.
- Confirmar que mensagens novas nao escondem warnings tecnicos importantes.
- Rodar `npm run test:logic --prefix frontend-ts`, `npm run build --prefix
  frontend-ts` e verificacao em Chrome.

## Rodada 2 - Velocidade No Trabalho Diario

**Intencao:** reduzir cliques, alternancia mental e retrabalho nas operacoes
mais repetidas: editar produtos, fechar grades, ordenar e preparar cadastro.

**Features candidatas:**

- Filtros salvos ou atalhos de visualizacao: pendentes de grade, importados
  recentemente, sem marca, sem codigo, com divergencia de quantidade.
- Barra de acoes por contexto para item selecionado: editar, duplicar, abrir
  grade, marcar categoria, mover na ordenacao.
- Melhorias no modal de grades: proximo item pendente, foco previsivel,
  resumo de divergencia e atalhos visuais.
- Revisao de undo/redo com indicacao simples de que existe historico
  reversivel.

**Aceite:**

- O operador faz as tarefas repetidas com menos passos sem perder o controle
  manual atual.
- Filtros e atalhos nao alteram a ordem real dos produtos sem acao explicita.
- Qualquer alteracao de produto continua passando pelos mesmos payloads e
  validacoes existentes.

**Auditor de review:**

- Revisar se a selecao/ordenacao visual nao altera `ordering_key` nem
  automacao por acidente.
- Conferir que a grade salva continua fechando com a quantidade esperada.
- Rodar testes puros de `productOrdering`, `productEditing`, `productForm`,
  `gradeLogic` e o gate frontend completo.

## Rodada 3 - Recursos Criativos Controlados

**Intencao:** abrir espaco para recursos novos, mas com contrato de seguranca:
primeiro prototipo reversivel, depois promocao para fluxo principal.

**Features candidatas:**

- Assistente de preparacao de cadastro: checklist operacional antes de iniciar
  cadastro completo, com pendencias de grades, automacao e targets.
- Modo "revisao do romaneio": tela de conferencia antes de consolidar
  importacoes com warnings, totais e itens suspeitos.
- Perfis operacionais: presets de grade/targets por maquina, operador ou tipo
  de fornecedor, sem alterar o padrao global ate confirmacao.
- Diario de operacao: linha do tempo local de importacao, edicoes relevantes,
  automacao iniciada/parada e erros recuperaveis.

**Aceite:**

- Prototipos ficam atras de UI secundaria ou fluxo opt-in.
- O usuario consegue abandonar o recurso e continuar usando o caminho atual.
- Dados novos devem ser derivados ou armazenados sem bloquear os dados
  principais de produto/importacao.

**Auditor de review:**

- Revisar se o recurso criativo nao cria novo ponto unico de falha.
- Conferir se ha caminho de rollback: feature removivel sem migracao destrutiva.
- Exigir teste de contrato para dados novos e verificacao visual em Chrome.

**Fatia executada:**

- Checklist inicial de prontidao para Cadastro Completo derivado de produtos,
  grades pendentes, automacao e targets ja expostos por `/automation/targets`,
  sem novo endpoint e sem mudar o handler atual de bloqueio por grade pendente.
  Prova registrada em `DocsDev/architecture/codegraphy-audit.md`.
- Diario local de operacao derivado de eventos ja confirmados pela UI:
  importacao/parser local, revisao com IA, automacao e bloqueio por grades
  pendentes. O recurso usa `localStorage`, limite curto e renderizacao
  recolhivel, sem novo endpoint, sem migracao e sem alterar payloads atuais.
  Prova registrada em `DocsDev/architecture/codegraphy-audit.md`.
- Complemento do diario para edicoes relevantes: criacao/edicao/remocao de
  produtos, acoes em massa de marca/categoria, margem, ordenacao, conjuntos,
  codigos e descricoes. O registro acontece somente apos sucesso da API e
  continua usando o cache local existente.
- Visao rapida `Revisar` para trabalho diario: agrupa itens com grade
  pendente, marca ausente, codigo ausente ou divergencia de grade, mantendo a
  ordem relativa da lista. O ultimo filtro visual escolhido fica salvo em
  `localStorage` e e validado contra presets conhecidos antes de ser aplicado.
- Indicadores de revisao por linha: os mesmos criterios da visao `Revisar`
  agora aparecem abaixo do nome do produto como chips compactos, explicando se
  o item esta sem marca, sem codigo, com grade pendente ou com total de grade
  divergente.
- Atalhos acionaveis nos chips de revisao: clicar em `Sem marca`,
  `Sem codigo`, `Grade pendente` ou `Grade X/Y` aplica o filtro especifico
  correspondente e preserva a preferencia visual local, sem selecionar linha,
  criar conjunto ou alterar ordenacao.
- Faixa de contexto para filtro ativo: quando a lista esta filtrada, a toolbar
  mostra o filtro atual, a contagem visivel e acoes reversiveis para `Mostrar
  todos` ou `Voltar para Revisar`, usando o mesmo estado visual e sem novo
  endpoint, nova persistencia ou alteracao de produtos.
- Estado vazio filtrado com recuperacao: quando um filtro nao retorna itens, a
  tabela explica o recorte atual e oferece as mesmas acoes reversiveis para
  sair do filtro ou voltar para `Revisar`, sem criar persistencia adicional nem
  acionar API.
- Filtro/chip `Sem categoria`: produtos sem categoria agora entram em
  `Revisar`, aparecem no filtro `Sem categoria` e recebem chip de revisao,
  para evitar que a automacao ByteEmpresa caia no grupo padrao por categoria
  vazia sem o operador perceber; sem mudar payloads, API, ordenacao ou
  automacao.

## Checkpoints Obrigatorios

1. Antes de implementar: escolher uma feature pequena da rodada e mapear
   arquivos provaveis.
2. Durante a implementacao: adicionar ou atualizar teste antes do comportamento
   virar definitivo.
3. Antes de fechar a fatia: rodar teste, build, `git diff --check` e, para UI,
   Chrome.
4. Depois de fechar a fatia: atualizar `DocsDev/architecture/codegraphy-audit.md`
   com regra seguida, motivacao, prova e impacto no CodeGraphy quando houver.

## Primeira Fatia Recomendada

Comecar pela Rodada 1 com "painel de saude local" ou "historico curto de
importacoes recentes". Essas fatias reaproveitam estados e metricas ja
existentes, tem alto valor de QoL e baixo risco de quebrar cadastro/automacao.
