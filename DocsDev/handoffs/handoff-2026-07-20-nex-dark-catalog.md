# Handoff 2026-07-20 - Nex Dark E Direcao Do Catalogo

Status: TRABALHO EM ANDAMENTO / SEM COMMIT / RETOMAR EM 20/07/2026.

Este documento registra o estado ao encerrar a sessao de 19/07/2026. A rodada
transformou o brand kit Nex Dark em uma interface funcional conectada ao LojaSync
real. O resultado ainda precisa de avaliacao e polimento, mas a direcao de produto e
de composicao do Catalogo esta definida.

## 1. Resumo executivo

- O brand kit de referencia continua em
  `Transformar-Parte-Visual-E-De-Design.zip`.
- O frontend real foi migrado para uma estrutura Nex Dark com sidebar, workspaces,
  wallpaper oficial, vidro escuro, tipografia Inter/system e azul reservado a acao e
  selecao.
- Catalogo virou a pagina principal e primeira opcao da navegacao.
- Ordem atual:
  1. Catalogo.
  2. Importacao.
  3. Execucao.
  4. Visao geral.
  5. Historico, sob Controle.
- O topbar `Produtos locais / Catalogo` foi removido somente do Catalogo para liberar
  altura para a lista.
- Os indicadores financeiros ficaram em uma faixa horizontal compacta no topo do
  Catalogo.
- Todas as funcoes da lista voltaram ao acesso direto, sem menu `Mais acoes`.
- O Catalogo recebeu um dock de acoes inspirado no kit.
- Cadastro manual virou um overlay de vidro funcional, arrastavel e nao bloqueante,
  aberto pelo dock.
- Importacao por IA e leitura local sao modos independentes escolhidos pelo usuario.
  Nenhum deve ser descrito como caminho principal ou fallback do outro.
- Auth continua opcional/legado e fora do trabalho ativo.

## 2. Direcao visual aprovada ate aqui

### Shell

- Sidebar desktop com 228 px e navegacao agrupada.
- Topbar contextual apenas nos workspaces que precisam dele.
- O Catalogo nao usa topbar proprio: inicia diretamente pelos dados e controles.
- Wallpaper oficial visivel nos gutters.
- Vidro forte em shell, dock e utilitarios flutuantes.
- Superficies mais opacas em tabela, grade, diagnosticos e formularios densos.
- Um unico H1 por workspace quando o topbar existe.
- Corpo em 13 px com fonte Inter/system e mono para codigos/valores tecnicos.
- Azul `#0a84ff` para primaria, foco e selecao.
- Verde, amber e vermelho apenas para semantica operacional.

### Catalogo

- Lista e a superficie dominante.
- A tabela deve ocupar a maior parte da altura util.
- Primeira faixa: readiness, financeiro, pendencias e configuracoes.
- Segunda faixa: contagem, historico, undo/redo, busca e funcoes da lista.
- Em seguida, tabela imediatamente, sem dashboard ou header intermediario.
- Indicadores financeiros permanecem horizontais:
  - Capital no lote.
  - Venda projetada.
  - Ganho bruto potencial.
- Filtros de pendencia permanecem na mesma faixa horizontal:
  - Pedem revisao.
  - Sem marca.
  - Sem categoria.
  - Grades pendentes quando existirem.
- Configuracoes ficam em um icone compacto no final da faixa.

### Funcoes da lista

Todas devem permanecer diretamente acessiveis:

- Permitir/finalizar edicoes.
- Formatar codigos.
- Melhorar descricao.
- Ordenar/salvar ordem.
- Criar/cancelar conjuntos.
- Juntar repetidos.
- Baixar CSV.
- Limpar lista.

Regras:

- Nao esconder essas funcoes em `Mais acoes` na direcao atual.
- Em 1920 e 1440, buscar uma linha unica.
- Em 1366, aceitar no maximo uma quebra controlada.
- Paineis de formatacao e descricao so ocupam altura quando abertos.
- Busca, escopo filtrado, modos e undo/redo continuam visiveis e verdadeiros.

## 3. Dock do Catalogo

O dock desktop foi adotado como superficie de acoes de fluxo, reaproveitando o padrao
iOS/macOS do kit.

Acoes atuais:

1. Novo produto.
2. Importar.
3. Inserir grade.
4. Executar.
5. Historico.

Comportamento:

- Aparece apenas no Catalogo desktop acima de 900 px.
- Fica centralizado no rodape.
- Usa vidro fosco forte.
- Tem 64 px de altura e controles de aproximadamente 48 px.
- Novo produto e a acao primaria azul.
- O workspace reserva padding inferior para o dock nao cobrir as ultimas linhas.
- Abaixo de 900 px, o dock global de navegacao mobile continua sendo o unico dock.

## 4. Cadastro manual flutuante

O cadastro manual e core do produto e deve permanecer disponivel dentro do Catalogo.

Implementacao atual:

- Componente: `frontend-ts/src/catalogQuickEntryPanel.tsx`.
- Usa `createPortal(..., document.body)`.
- Nao depende do stacking context do workspace ou da tabela.
- `role="dialog"` e `aria-modal="false"`.
- Nao usa backdrop, permitindo consultar a lista durante a entrada.
- Abre pelo primeiro botao do dock.
- Compartilha o mesmo estado `form` do cadastro existente.
- Usa a mesma validacao, snapshot, API, refresh de produtos/totais e diario.
- Campos:
  - Nome.
  - Codigo no modo completo.
  - Quantidade.
  - Custo.
- Suporta modo simples/completo.
- Foca `nome` ao abrir.
- `Escape` fecha.
- Tenta restaurar foco ao controle que abriu.
- Pode ser arrastado pelo header com Pointer Events.
- Usa pointer capture durante o arraste.
- Posicao e limitada a viewport.
- Posicao e persistida em
  `lojasync-catalog-quick-entry-position` no `localStorage`.
- Possui `Redefinir posicao`.
- Em ate 720 px, vira bottom sheet e o arraste e desabilitado.

Hierarquia de camadas atual:

- Dock do Catalogo: `z-index: 120`.
- Cadastro manual: `z-index: 220`.
- Modais bloqueantes: `z-index: 320`.
- Notice dialog: `z-index: 340`.
- Toasts: `z-index: 400`.

Evidencia interativa registrada em 1440x900:

- Tabela em `y=216` antes e depois de abrir/mover o overlay.
- Dock em `y=711`, camada `120`.
- Overlay abriu em `(680, 339)`, tamanho aproximado `720x127`, camada `220`.
- Portal confirmado como filho direto do `body`.
- Foco ativo confirmado em `nome`.
- Overlay arrastado para `(440, 415)`.
- Posicao persistida no `localStorage`.
- Deslocamento da tabela: `0 px`.

Captura temporaria da prova:

- `C:\Users\user\AppData\Local\Temp\opencode\catalog-dock-overlay-open.png`.

## 5. Workspaces funcionais

### Catalogo

- Resumo horizontal compacto.
- Ferramentas completas.
- Busca, filtros, modos e escopo em lote.
- Tabela real com edicao inline e row actions.
- Dock de fluxo.
- Cadastro manual flutuante.

### Importacao

- Importar com IA.
- Importar com leitura local.
- As duas opcoes sao escolhas independentes do usuario.
- Diagnosticos, warnings e importacoes recentes continuam conectados.
- Entrada manual completa tambem permanece disponivel nesse workspace.

### Execucao

- Centro de execucao real.
- Readiness, progresso e parada.
- Cadastro completo, cadastro, grades e consolidacao continuam conectados.

### Visao geral

- Agora e a quarta opcao.
- Mantem resumo, saude operacional e proximas acoes.
- Nao deve competir com o Catalogo como pagina inicial.

### Historico

- Usa eventos reais de `operationDiary`.
- Undo/redo continuam controles separados, com contagens e rotulos reais.
- Nao inventar timeline detalhada de snapshots.

## 6. Arquivos principais alterados nesta linha

Fontes frontend:

- `frontend-ts/src/App.tsx`
- `frontend-ts/src/styles.css`
- `frontend-ts/src/catalogOverviewPanel.tsx`
- `frontend-ts/src/productListControls.tsx`
- `frontend-ts/src/importStagePanel.tsx`
- `frontend-ts/src/catalogActionDock.tsx` - novo
- `frontend-ts/src/catalogQuickEntryPanel.tsx` - novo
- `frontend-ts/src/historyPanel.tsx` - novo
- `frontend-ts/index.html`

Ativos:

- `frontend-ts/public/wallpapers/`
- `frontend-ts/dist/wallpapers/`

Documentacao corrigida:

- `README.md`
- `DocsDev/codegraph/inventory.md`
- `DocsDev/architecture/brand-kit-adaptation-plan.md` - novo, plano inicial que foi
  parcialmente superado pela implementacao; usar este handoff como estado mais atual.

Bundle de distribuicao:

- `frontend-ts/dist/index.html`
- Novos bundles hash em `frontend-ts/dist/assets/`.
- Bundles hash anteriores aparecem removidos, comportamento normal apos `npm run build`.

## 7. Validacao executada

Frontend:

- `npm run test:logic`: 112 testes aprovados, 0 falhas.
- `npx tsc -b --pretty false`: aprovado durante as rodadas.
- `npm run build`: aprovado na ultima rodada.
- Vite transformou 59 modulos.
- Ultimo build observado:
  - `dist/assets/index-BXLpizPp.css`
  - `dist/assets/index-2AtBm_ml.js`
  - `dist/assets/App-D3PRmrJF.js`
- `git diff --check`: aprovado; apenas warnings LF/CRLF.

Validacao visual:

- Capturas reais com Chrome em:
  - 1920x1080.
  - 1440x900.
  - 1366x768.
- O topbar do Catalogo foi removido nas tres larguras.
- Financeiro permaneceu horizontal.
- Funcoes diretas permaneceram visiveis.
- A lista subiu aproximadamente a altura inteira do topbar removido.
- Dock permaneceu centralizado e sem cobrir o fim da tabela.

Backend:

- Nenhum contrato de API foi alterado nesta linha visual.
- O full pytest backend nao foi necessario para cada fatia visual.

## 8. Estado do runtime ao encerrar

- Em 19/07/2026, no fechamento deste handoff, a porta `8800` nao estava mais
  ouvindo.
- `/health` estava indisponivel porque o launcher ja havia encerrado.
- Para retomar sem rebuild automatico, depois de confirmar que o build atual existe:

```powershell
python launcher.py --skip-ts-build --disable-llm-monitor --no-browser
```

- Aplicacao esperada: `http://127.0.0.1:8800/`.
- Se precisar iniciar o LLM monitor, remover `--disable-llm-monitor`.
- Nao habilitar auth salvo pedido explicito.

## 9. Estado Git e cuidados

- Nenhum commit foi criado.
- A arvore esta suja de proposito.
- Nao usar reset/checkout destrutivo.
- `Transformar-Parte-Visual-E-De-Design.zip` esta nao rastreado e deve ser preservado.
- `showcase-site/` esta nao rastreado e nao foi parte desta implementacao; preservar e
  nao misturar automaticamente em eventual commit.
- O novo handoff tambem esta nao rastreado ate ser adicionado explicitamente.
- Antes de commit, revisar `git status`, `git diff`, bundles de `dist` e separar apenas
  os arquivos intencionais.

Resumo do `git status` no fechamento:

- Modificados: README, inventario CodeGraph, frontend source/index e dist.
- Removidos: bundles antigos hash de `frontend-ts/dist/assets/`.
- Novos: bundles hash atuais, wallpapers, componentes do Catalogo/Historico, plano e
  este handoff.
- Nao relacionados preservados: ZIP do kit e `showcase-site/`.

## 10. Riscos e divida tecnica

### CSS

- `frontend-ts/src/styles.css` recebeu varias rodadas de override e cresceu muito.
- A direcao visual esta mais clara, mas seletores antigos e novos ainda coexistem.
- Nao iniciar uma limpeza ampla antes de congelar a composicao aprovada pelo usuario.
- Depois da aprovacao visual, consolidar tokens e remover regras realmente
  superseded em uma fatia separada, com screenshots de regressao.

### App

- `App.tsx` continua grande e concentra estado/handlers.
- Isso preservou o comportamento durante a migracao, mas aumenta risco de manutencao.
- Nao misturar extracao de estado/hooks com a proxima rodada puramente visual.

### Overlay

- Validado em Chrome desktop.
- Retestar manualmente arraste, reset de posicao, Escape e foco no navegador do
  operador.
- Retestar bottom sheet em 720 px ou menos.
- Verificar que abrir modal bloqueante enquanto o overlay esta aberto preserva a
  hierarquia de camadas esperada.

### Outros workspaces

- Catalogo recebeu a maior parte do polimento.
- Importacao, Execucao, Visao geral, Historico, Grade e Settings ainda precisam de uma
  revisao visual equivalente contra o kit.
- Nao sacrificar comportamento real por fidelidade ao prototipo estatico.

## 11. Prioridade recomendada para 20/07/2026

1. Iniciar o launcher e fazer smoke manual do Catalogo.
2. Testar cadastro manual pelo dock:
   - abrir/fechar;
   - arrastar;
   - resetar posicao;
   - modo simples/completo;
   - validacao de campos;
   - criar produto real;
   - confirmar refresh da tabela/totais e undo.
3. Revisar a faixa horizontal do Catalogo em 1366, 1440 e 1920 com dados reais.
4. Confirmar se todas as oito funcoes diretas devem permanecer na primeira linha ou
   se alguma pode virar icone sem perder clareza.
5. Revisar estados expandidos:
   - formatar codigos;
   - melhorar descricao;
   - ordenar;
   - conjuntos;
   - escopo filtrado;
   - bulk marca/categoria.
6. Fazer a mesma rodada de fidelidade Nex Dark em Importacao e Execucao.
7. Somente apos aceite visual do Catalogo, planejar consolidacao do CSS.
8. Ao preparar release, revisar arquivos intencionais, regenerar dist uma ultima vez e
   rodar os gates completos.

## 12. Decisoes que nao devem regredir

- Catalogo e a pagina principal.
- Visao geral e a quarta opcao.
- Cadastro manual precisa estar disponivel diretamente no Catalogo.
- Lista tem prioridade maxima de area util.
- Financeiro fica horizontal.
- Funcoes da lista ficam em acesso direto na direcao atual.
- Dock do Catalogo e uma superficie real de acoes, nao decoracao.
- Cadastro manual usa portal/overlay e nao desloca a lista.
- IA e leitura local sao modos escolhidos pelo usuario, sem hierarquia.
- Stop da automacao deve permanecer sempre acessivel durante execucao.
- Escopo visivel das operacoes em lote deve continuar explicito.
- Undo/redo, grade dirty/save-next, WebSocket/polling e todos os contratos atuais devem
  ser preservados.
- Auth continua fora do backlog ativo.

## 13. Referencias

- Kit entregue: `Transformar-Parte-Visual-E-De-Design.zip`.
- Especificacao extraida durante a sessao:
  `C:\Users\user\AppData\Local\Temp\opencode\lojasync-brandkit\brand-spec.md`.
- Prototipo de referencia extraido:
  `C:\Users\user\AppData\Local\Temp\opencode\lojasync-brandkit\lojasync-nex-dark.html`.
- Preview extraido:
  `C:\Users\user\AppData\Local\Temp\opencode\lojasync-brandkit\lojasync-nex-dark-preview.png`.
- Plano inicial: `DocsDev/architecture/brand-kit-adaptation-plan.md`.
- Inventario vivo: `DocsDev/codegraph/inventory.md`.
