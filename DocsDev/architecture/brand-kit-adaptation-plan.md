# Plano De Adaptacao Do Brand Kit Nex Dark Para O LojaSync

Status documental: PLANEJAMENTO ONLY / NAO IMPLEMENTAR A PARTIR DESTE ARQUIVO SEM APROVACAO.

Este documento descreve como adaptar o brand kit entregue em
`Transformar-Parte-Visual-E-De-Design.zip` para a UI real do LojaSync. Durante a
analise, o ZIP foi extraido apenas em diretorio temporario para leitura. Ele e
deliberadamente um plano: nao altera contratos, endpoints, estado,
persistencia, automacao, auth ou bundle gerado.

## 1. Status, objetivo e nao-objetivos

### Status

- Tipo: planejamento de arquitetura/UX visual.
- Escopo: frontend React principal em `frontend-ts/src`, com impacto planejado em CSS,
  composicao visual e IA de navegacao.
- Fonte visual: export unico `lojasync-nex-dark.html` + handoff + manifest + critica.
- Fonte de produto: codigo atual, README e inventario CodeGraph.
- Restricao: nenhuma mudanca de aplicacao deve ser feita nesta etapa.

### Objetivo

- Adaptar o LojaSync para uma experiencia operacional Nex Dark coerente, compacta e
  desktop-first.
- Preservar os fluxos reais: importacao/manual, revisao/edicao/lote, grades,
  prontidao, automacao desktop, historico/recuperacao e configuracoes.
- Separar o que e contrato visual valido do prototipo do que era demonstracao.
- Definir fases pequenas, reversiveis e verificaveis antes de escrever codigo.
- Evitar refactors de estado ou rotas misturados com reskin visual.

### Nao-objetivos

- Nao implementar codigo agora.
- Nao mudar endpoints, payloads, jobs, SQLite, automacao ou parser.
- Nao criar novo fluxo de auth, senha, sessao ou hardening de auth.
- Nao prometer paridade mobile completa sem decisao de produto.
- Nao copiar dados demonstrativos, simulacoes ou anotacoes de prototipo.
- Nao afirmar gate de revisao pre-persistencia inexistente no produto atual.
- Nao regenerar `frontend-ts/dist` ate uma fase release-ready.

## 2. Evidencias revisadas e resumo da realidade do produto

### Evidencias revisadas

- `DocsDev/codegraph/inventory.md`:
  - App React principal concentra produtos, automacao, imports, grades, settings,
    dialogs, notificacoes e sincronizacao.
  - Importacao oferece dois modos escolhidos pelo usuario: IA/LLM e leitura local.
  - WebSocket publica eventos, com polling como fallback.
  - Automacao depende de Windows, desktop interativo, coordenadas e Byte Empresa.
  - Auth existe, mas e opcional via `--enable-auth`.
- `README.md`:
  - LojaSync e plataforma desktop-web para cadastro assistido no Byte Empresa.
  - SQLite local e fonte operacional.
  - `frontend-ts/dist/` e versionado de proposito apenas para distribuicao/release.
  - LLM e opcional; parser local ainda pode aprovar notas consistentes.
- `DocsDev/architecture/qol-feature-rounds.md`:
  - Mudancas criativas devem ser pequenas, reversiveis e observaveis.
  - Nao quebrar importacao, cadastro, grades, ordenacao, automacao ou auth existente.
  - Diario local, filtros de revisao e indicadores ja foram planejados/executados em
    partes sem alterar endpoints.
- Arquivos frontend atuais:
  - `App.tsx` render 2470+ mostra shell fixo, sidebar esquerda, painel direito,
    modais globais e estado raiz unico.
  - `productListControls.tsx` contem ferramentas, busca, undo/redo, modos,
    paineis de codigos/descricao.
  - `productTable.tsx` contem tabela real, escopo de lote visivel, bloqueios por
    modo, estados vazio/loading e janela de renderizacao.
  - `gradeModal.tsx` contem lista de produtos, familias, grade dirty, save/next,
    execucao/parada de grades.
  - `importStagePanel.tsx` contem importacao com IA, leitura local avancada,
    diagnosticos e importacoes recentes.
  - `executionCenterPanel.tsx` contem acoes de automacao, readiness e parada.
  - `settingsModal.tsx` contem targets, GradeBot, diagnosticos e captura.
  - `styles.css` contem sistema visual atual, stage fixo, painel esquerdo/direito,
    tokens escuros e muitos componentes ja nomeados.
  - `appConfig.ts` contem constantes de targets, dimensoes do stage e estado inicial.
- Brand kit extraido:
  - `brand-spec.md`: Nex Dark, Inter/system, vidro, wallpaper, azul reservado,
    densidade compacta e um H1 por tela.
  - `DESIGN-HANDOFF.md`: preservar tokens, responsividade, estados, acessibilidade e
    separar superficies reais.
  - `DESIGN-MANIFEST.json`: um screen HTML, app modules devem ser especificos,
    viewport matrix moderna.
  - `lojasync-nex-dark.html`: prototipo visual com sidebar, topbar, views,
    dock, wallpaper panel, modal de produto e dados demo.
  - `critique.json`: cinco destinos refletem fluxo real; catalogo domina; saude,
    importacao e execucao sao secundarios claros.

### Resumo da realidade do produto

- O produto real e uma estacao operacional local para preparar produtos e cadastrar no
  Byte Empresa.
- O caminho mais importante nao e um dashboard generico: e uma mesa de trabalho de
  catalogo/lista com importacao, edicao, grades e execucao sempre recuperaveis.
- A operacao depende de estado local longo: produtos carregados, filtros, jobs,
  historico, dialogs, modais, WebSocket/polling, preferencias e automacao.
- IA/LLM e leitura local sao caminhos distintos escolhidos pelo usuario; a UI nao deve
  apresentar um deles como etapa obrigatoria, caminho primario ou fallback do outro.
- Auth/senha/sessao sao infraestrutura opcional/legada e nao devem virar backlog de
  produto nesta adaptacao.

## 3. Jornada de uso diario

### Fluxo principal

1. Importacao ou entrada manual
   - Usuario seleciona PDF/TXT/imagem de romaneio/NF-e.
   - Sistema inicia job de importacao em background.
   - Se o usuario escolher IA, o fluxo usa o endpoint de importacao por IA sem sondar o
     parser local.
   - Se o usuario escolher leitura local, o fluxo usa o endpoint local dedicado.
   - Produtos persistidos entram na lista ativa com metadados de lote e possivel grade
     pendente.
   - Alternativa: usuario cadastra produto manual por `ProductEntryPanel`.

2. Revisao, edicao e operacoes em lote
   - Usuario revisa tabela por busca, filtros rapidos, indicadores de revisao e chips.
   - Campos sao editados inline quando edicao esta liberada.
   - Acoes em lote aplicam marca/categoria, formatam/restauram codigos, melhoram
     descricoes, exportam CSV, juntam duplicados ou limpam lista.
   - Invariante: lote filtrado age no escopo visivel quando assim indicado.

3. Grades
   - Usuario abre modal de grades para produto ou pendencias.
   - Edita quantidades por tamanho/familia.
   - Usa proxima pendencia, salvar, salvar e proxima, limpar selecionada/todas.
   - Pode importar/consolidar grades pendentes por lote sem misturar produtos manuais.

4. Prontidao
   - UI calcula estado de execucao com produtos, grades pendentes, automacao e erro.
   - Usuario precisa entender bloqueios antes de iniciar Byte Empresa.
   - Indicador global deve mostrar job/automacao ativo mesmo fora da workspace atual.

5. Automacao desktop
   - Usuario inicia cadastro completo, cadastro em massa ou grades.
   - Backend usa automacao Windows/Byte Empresa e pode exigir confirmacao humana.
   - UI exibe estado, progresso, item atual e parada.
   - Parada deve ficar sempre acessivel.

6. Recuperacao e historico
   - Snapshots protegem operacoes destrutivas/lote.
   - Undo/redo persiste em JSON local separado e tem limite de 50 snapshots.
   - Diario/toasts/dialogos explicam resultados e falhas recuperaveis.

### Caminhos alternativos e excecoes

- Arquivo invalido ou parser sem itens: mostrar erro acionavel, manter selecao e nao
  bloquear cadastro manual.
- LLM indisponivel: informar fallback/limite, sem tratar como falha fatal se local
  aprovou ou se usuario pode seguir manualmente.
- Job em andamento com troca de view: manter progresso global e nao desmontar estado.
- WebSocket falha: manter polling fallback e estado de conectividade legivel.
- Lista vazia: oferecer importar primeiro romaneio e cadastrar manualmente.
- Filtro sem resultado: oferecer limpar busca/filtro sem alterar dados.
- Edicao/lote bloqueados por modo de ordenacao/conjunto: explicar bloqueio.
- Grade dirty: impedir troca/perda silenciosa; salvar ou confirmar descarte.
- Automacao sem targets ou Byte Empresa: readiness bloqueia/avisa antes da execucao.
- Captura de coordenadas: exigir contexto Windows e contagem regressiva clara.
- Restart do app: localStorage deve preservar preferencias leves, mas jobs em memoria
  podem ser perdidos; UI deve nao prometer recuperacao de job apos restart.

## 4. Contrato do brand kit

### Preservar como contrato visual

- Tokens Nex Dark:
  - `--bg: oklch(0.16342 0.00906 264.28)` / base `#0c0e12`.
  - `--surface: oklch(0.20864 0.00851 264.37 / 0.48)`.
  - `--fg: oklch(1 0 0 / 0.94)`.
  - `--muted: oklch(1 0 0 / 0.65)`.
  - `--accent: oklch(0.62425 0.20558 255.49)` / `#0a84ff`.
- Hierarquia:
  - Catalogo/lista como centro operacional.
  - Importacao e execucao como workspaces focadas.
  - Saude/historico/settings como utilitarios.
- Tipografia:
  - Inter com fallback Apple/SF/Segoe/system.
  - Corpo compacto 13px/1.45; card titles proximos de 15px.
  - Mono apenas para hora, codigos, coordenadas, contadores tecnicos.
- Azul reservado:
  - Primario, selecao ativa, foco, progresso principal e acao recomendada.
  - Nao usar azul como decoracao generica em todo card.
- Glass/wallpaper:
  - Wallpaper participa do chrome e fica visivel entre unidades.
  - Vidro fosco no chrome e em superficies de baixa densidade; tabela, grade e
    diagnosticos recebem fundos mais opacos para manter contraste e desempenho.
  - Sem contorno solido pesado; hairlines discretas sao permitidas onde controles
    densos precisam de separacao.
  - Trilhos/pontos/labels carregam semantica, nao blocos coloridos inteiros.
- Motion:
  - Transicoes curtas 140ms, medias 280ms e crossfade amplo 520ms quando fizer
    sentido.
  - Respeitar `prefers-reduced-motion` com reducao real.
- Fidelidade visual:
  - Preservar densidade compacta, raios, sombras, gutters e affordances do kit.
  - Comparar screenshots antes de declarar fatia visual concluida.

### Nao portar literalmente

- Dados demonstrativos (`demoProducts`, valores `R$ --`, eventos de prototipo).
- Simulacoes de importacao/execucao/toasts do HTML.
- Anotacoes de prototipo, Open Design chrome, labels `data-od-id` e texto "prototipo".
- Cinco silos isolados que desmontem estado real.
- Dock desktop duplicando sidebar/topbar sem necessidade operacional.
- Cards mobile genericos para tabela como promessa automatica de paridade total.
- Proeminencia de auth/login/senha; auth e opcional/legado no produto.
- Texto "Nada e persistido antes da validacao" se sugerir gate pre-persistencia nao
  suportado pelo fluxo atual.

## 5. UX/IA alvo, recomendacao e riscos

### Recomendacao principal

- Default: `Produtos`/`Catalogo` como workspace inicial ou ultima workspace usada.
- Racional:
  - A maior parte do dia ocorre na lista: revisar, editar, ordenar, filtrar,
    preparar grades, aplicar lote e conferir prontidao.
  - Importacao e entrada manual alimentam a lista; execucao consome a lista.
  - Overview e util, mas nao deve esconder a mesa de trabalho.

### IA proposta

- Workbench principal:
  - `Produtos` ou `Catalogo`: CatalogOverview + ProductListControls + ProductTable.
- Workspaces focadas:
  - `Importar`: ImportStagePanel + diagnosticos + recentes + orientacao de parser local.
  - `Grades`: Grade modal ou view/sheet focada, mantendo compatibilidade com modal.
  - `Executar`: ExecutionCenterPanel + readiness + parada + status atual.
- Utilitarios:
  - `Atividade`: diario operacional, undo/redo, importacoes recentes, recuperacao.
  - `Configuracoes`: settings modal ou view utilitaria para targets/GradeBot/diagnosticos.
- `Overview`:
  - Opcional; se mantida, deve resumir estado e proxima acao sem substituir catalogo.
- Indicador global:
  - Sempre mostrar job de importacao/automacao ativo e parada quando aplicavel.

### Estado raiz estavel

- Implementacao inicial deve preservar um unico App state root em `App.tsx`.
- Navegacao pode ser views/anchors/abas CSS dentro do App, sem remountar fluxos
  operacionais.
- Modais globais continuam fora das views para evitar perda de foco/estado.
- So extrair hooks/rotas reais depois de estabilizar invariantes e testes.

### Risco: canvas desktop fixo vs matriz responsiva completa

- O app atual usa `APP_STAGE_WIDTH`, `APP_STAGE_HEIGHT` e um stage limitado pelas
  dimensoes disponiveis, com minimos voltados ao desktop.
- O handoff pede matriz responsiva 2025-2026, incluindo mobile.
- Ha conflito de produto:
  - Operacao real e desktop-web com automacao Windows; cadastro em massa e tabela ampla
    dependem de tela, teclado e Byte Empresa.
  - Full mobile parity exigiria redesenhar tabela, bulk actions, grade editor e
    automacao como monitoramento/edicao estreita, nao apenas CSS.
- Recomendacao:
  - Prioridade desktop-first operacional em 1366x768, 1440x900 e 1920x1080.
  - Garantir 1024x768 sem quebra horizontal critica.
  - Narrow/mobile apenas graceful monitoring/editing se explicitamente escopado.
  - Decisao de produto obrigatoria antes de prometer paridade mobile completa.

## 6. Mapeamento detalhado de modulos reais

| Modulo/recurso | Destino IA | Adaptacao Nex Dark | Estados | Invariante |
|---|---|---|---|---|
| `CatalogOverviewPanel` | Topo do workbench Produtos/Catalogo; opcional resumo no Overview | Card glass compacto com readiness, valores e issues; azul so para filtro ativo | vazio, pronto, precisa revisao, filtro ativo | Clicar issue apenas filtra; nao altera dados |
| `ProductTable` | Corpo principal do workbench | Tabela real preservada em desktop; sticky head glass; rows densas; sem cards mobile genericos no escopo inicial | loading, vazio, busca vazia, normal, filtrado, edit locked, ordering, create set, automacao row atual | Escopo visivel em lote continua explicito; windowing continua |
| `ProductTableRow`/celulas | Linhas da tabela | Chips discretos, foco claro, current row com trilho azul/teal | default, hover, focus, editando, selecionado ordem, selecionado conjunto, atual automacao, pendente grade | Inline edit so quando permitido; row actions nao disparam modos conflitantes |
| `ProductListControls` | Toolbar do workbench | Topbar/tool rail glass; grupos Edicao/Assistida/Organizacao/Compartilhar/Risco mais compactos | normal, loading, painel codigos aberto, painel descricao aberto, ordering, create set, busy, historico ready | Ordering e create set continuam exclusivos; edit/bulk respeitam os bloqueios atuais; undo/redo intacto |
| `productListToolPanels` | Popover/painel contextual | Popovers glass ancorados aos botoes; foco restaurado | aberto, fechado, escape, validacao, busy | Escape fecha e retorna foco; opcoes preservadas |
| `ProductEntryPanel` | Importar ou CTA Novo produto; pode ficar utility panel | Modal/sheet glass ou bloco compacto; rotulo manual como excecao rapida | vazio, preenchido, submitting, erro, preview margem | Payload e validacao atual preservados |
| Importacao (`ImportStagePanel`) | Workspace Importar | Dropzone/selector do kit conectado ao input real; IA e leitura local apresentadas como escolhas equivalentes e explicitas | idle, arquivo selecionado, importing, local, success, error, warnings, diagnostics, recentes | Escolha do usuario decide o endpoint; job lifecycle e polling/status atuais preservados |
| `ImportDiagnosticsPanel` | Dentro de Importar e Activity | Chips semanticos com opacidade tier 2/3; warnings legiveis | aprovado, nao verificado, rejeitado, erro, sem dados | Nao esconder warnings tecnicos importantes |
| Recent imports | Importar + Activity | Timeline/lista glass compacta | nenhum, 1, varios, warnings, grades available | LocalStorage defensivo e limite atual preservados |
| Grade modal/familias | Workspace Grades ou modal mantido | Modal glass amplo; sidebar de produtos; tabs de familias; progress summary com semantica | sem produto, produto selecionado, dirty, transition locked, overflow, complete, pending, erro | Dirty/transition/save-next nao regressam |
| Execucao (`ExecutionCenterPanel`) | Workspace Executar + indicador global | Action tiles para acoes grandes; parada fixa; readiness card | ready, running, stopped, error, bloqueado por grades/targets, progresso | Stop acessivel; readiness nao altera API |
| Operational Health | Utility/Overview/Topbar | Chips compactos de runtime/API/socket/automacao | ok, warning, error, checking, websocket fallback | Falha WS nao bloqueia polling |
| `OperationalSummaryPanel` | Sidebar utilitaria ou Overview | Cards glass de totais; menos peso que tabela | zero, valores atuais, acumulado, analytics empty | Numeros formatados atuais preservados |
| Usage analytics | Overview/utility | Card discreto, nao competindo com execucao | empty, populated | Derivado de dados reais, sem demo |
| Undo/redo + diario | Activity/recovery + topbar buttons | Diario local como timeline de eventos confirmados; undo/redo como controle separado com contagens e rotulos disponiveis, sem inventar timeline de snapshots | diario vazio/preenchido, canUndo, canRedo, busy, erro | Snapshots antes de destrutivas/lote; guard de teclado preservado; diario nao se torna fonte do undo |
| Settings targets | Configuracoes utility | Modal/view glass tecnico; coordenadas mono | loading, saving, capture countdown, erro, success | Targets e normalizacao preservados |
| Settings GradeBot | Configuracoes utility | Secao dedicada; ordem ERP mono/chips | loading, saving, captura botoes, erro | Ordem visual de grade nao substitui ordem ERP da automacao |
| Settings diagnostics | Configuracoes/diagnostico | Pre glass mono com wrapping controlado | vazio, contexto carregado, preparando, erro | Ambiente Windows/Byte Empresa continua requisito |
| Dialogos de confirmacao | Global layer | Modal glass escuro com foco visivel | open, busy, error, cancel, confirm | Confirmacoes destrutivas permanecem |
| Notice dialogs/toasts | Global HUD | Toasts glass; tons semanticos discretos | success, warning, error, info, dismiss | Mensagens acionaveis; nao vazar stack bruta |
| AuthShell | Fora do backlog de produto | Se auth habilitado, apenas aplicar tokens basicos sem destaque de roadmap | loading, setup, login, app | Auth opcional/legado; nao criar melhorias de produto |

## 7. Adaptacao do design system

### Tabela de tokens

| Fonte kit | Producao semantica | Uso planejado |
|---|---|---|
| `--bg` / `#0c0e12` | `--ls-bg-app` | Fundo base solido quando wallpaper off |
| `--surface` / `rgba(22,24,28,.48)` | `--ls-surface-glass` | Cards, sidebar, topbar, modais |
| `--glass-bg-dark-strong` | `--ls-surface-glass-strong` | Popovers, toasts, areas sobre conteudo denso |
| `--fg` | `--ls-text-primary` | Texto principal |
| `--muted` | `--ls-text-muted` | Descricoes, meta, labels secundarios |
| `rgba(255,255,255,.38)` | `--ls-text-subtle` | Micro-labels e placeholders |
| `--accent-blue` / `#0a84ff` | `--ls-accent-primary` | CTA, selecao, foco, progresso |
| `--accent-green` | `--ls-status-success` | Concluido/aprovado |
| `--accent-orange` | `--ls-status-warning` | Pendencia/atencao |
| `--accent-red` | `--ls-status-danger` | Erro/parada/risco |
| `--accent-teal` | `--ls-status-info` | Info/automacao/status tecnico |
| `--panel-radius:18px` | `--ls-radius-panel` | Cards e paineis principais |
| `--window-radius:16px` | `--ls-radius-window` | Topbar/modal/popover |
| `--dur-fast/mid/slow` | `--ls-motion-fast/mid/slow` | Hover/view/fade |
| `--ease-ios` | `--ls-ease-standard` | Transicoes padrao |

### Tres tiers de opacidade

- Tier 1 chrome:
  - Background `rgba(22,24,28,.48)` com blur alto.
  - Sidebar/topbar/cards maiores sobre wallpaper.
- Tier 2 content dense:
  - Background `rgba(18,20,24,.58-.72)`.
  - Tabela, popovers, modal bodies, diagnostics.
- Tier 3 control/semantic:
  - Pills `rgba(255,255,255,.07-.14)` e active azul `rgba(10,132,255,.22-.42)`.
  - Chips de estado com trilho/ponto, nao lavagem de cor pesada.

### Wallpaper policy

- Wallpaper permitido no chrome, nao como distracao atras de tabela densa.
- Conteudo operacional denso recebe overlay/surface forte para contraste.
- Oferecer fallback solido quando:
  - `prefers-reduced-transparency` for suportado/detectado via classe futura.
  - Performance cair em maquina fraca.
  - Contraste visual falhar em screenshot.
- Upload customizado e appearance settings dependem de decisao de produto.
- Se implementado, salvar apenas preferencia leve em localStorage; nao envolver backend.

### Semantica de cor

- Azul: acao primaria, filtro ativo, foco, progresso principal, view ativa.
- Verde: aprovado/concluido/ready real.
- Laranja/amarelo: pendencia, warning, revisao necessaria.
- Vermelho: erro, risco, parada, destrutivo.
- Teal/ciano: informacao tecnica ou automacao em progresso, se nao competir com azul.

### Tipografia, espaco, raio e movimento

- Fonte: Inter, Apple/SF, Segoe, system; remover dependencia visual de Space Grotesk.
- Body: 13px/1.45; minimo 12px para texto de apoio; evitar abaixo de 10px salvo label
  puramente meta.
- H1: unico por view/shell, 20-22px desktop.
- H2 card/tabela: 15-18px conforme hierarquia.
- Gaps: 8/10/12/14/16px; evitar saltos grandes que reduzam densidade.
- Radius: 10 controles, 12 inputs, 16 popovers, 18 panels, 24 dock/shell quando usado.
- Motion: hover 140ms, view 280ms, wallpaper 520ms; reduced motion zera animacoes.

### Acessibilidade

- Preservar skip link para workspace.
- Foco visivel azul com outline de 2px.
- Dialogos com `aria-modal`, trap de foco e retorno de foco.
- `aria-live` em jobs, readiness, automacao e toasts.
- Contraste minimo WCAG AA para texto normal em superficies reais.
- Tabela desktop continua tabela semantica; nao substituir por divs sem necessidade.
- Teclado: Escape fecha popovers/modais; Ctrl/Cmd+Z guardado fora de inputs quando
  apropriado.

## 8. Invariantes de estado e comportamento

- Import job lifecycle:
  - `POST /actions/import-romaneio` cria job.
  - UI consulta status/result e publica progresso.
  - Mensagens de erro/sucesso/warnings permanecem.
  - IA/LLM e leitura local permanecem modos independentes escolhidos pelo usuario.
- WebSocket + polling:
  - Eventos `state_changed`, `job_updated`, `connected` atualizam UI.
  - Polling continua cobrindo falha de socket.
- App state root:
  - Um App raiz estavel preserva produtos, forms, filtros, imports, settings,
    grade modal, dialogs, notifications e automation.
  - Navegacao inicial nao deve remountar esse estado.
- Bulk visible scope:
  - Acoes em lote sobre lista filtrada continuam explicitando escopo visivel.
  - Itens ocultos por filtro continuam preservados quando essa for a regra atual.
- Modos e bloqueios:
  - Ordering mode e create set mode continuam mutuamente exclusivos.
  - Edit mode e bulk actions respeitam os gates atuais, sem assumir exclusividade
    adicional que o codigo nao imponha.
  - Bulk actions bloqueiam quando ordering/create set ativos.
- Snapshots/undo-redo:
  - Snapshot antes de limpar, deletar, lote ou destrutivas.
  - Guard de teclado nao deve disparar enquanto usuario edita campo.
  - Limite de 50 snapshots preservado.
- Grade:
  - Dirty state visivel.
  - Transition lock bloqueia troca/fechamento inseguro.
  - Save e save-next preservam comportamento.
  - Familias visuais nao alteram ordem ERP da automacao.
- Automacao:
  - Readiness mostra grades pendentes, produtos, estado e erro.
  - Linha/produto atual de automacao continua destacado.
  - Stop sempre acessivel durante execucao.
  - Confirmacao humana e status Windows continuam requisito para acoes desktop.
- LocalStorage:
  - Preferencias existentes de modo/filtros/recentes/grade families/diario continuam.
  - Novas preferencias visuais devem ser defensivas contra JSON invalido.
- Auth:
  - Nao iniciar trabalho de auth como produto.
  - Se auth habilitado, aplicar apenas compatibilidade visual basica em fase propria.

## 9. Grafo de trabalho por fases

### Fase 0 - Freeze e contratos

- Escopo:
  - Aprovar decisoes de produto e tokens sem tocar UI.
  - Criar tickets/slices com invariantes.
- Arquivos provaveis:
  - Docs apenas: este plano, tickets futuros.
- Dependencias:
  - Aprovacao de default workspace, mobile, Overview, wallpaper, appearance, nome.
- Aceite:
  - Decisoes registradas; nenhum codigo alterado.
- Evidencia/verificacao:
  - Review documental.
- Rollback seam:
  - Remover/arquivar tickets; sem impacto runtime.

### Fase 1 - Tokens visuais isolados

- Escopo:
  - Introduzir tokens Nex Dark em CSS sem mudar layout/estado.
  - Trocar fonte para Inter/system se asset/fallback definido.
  - Mapear aliases legacy para evitar quebrar classes existentes.
- Arquivos provaveis:
  - `frontend-ts/src/styles.css`.
- Dependencias:
  - Fase 0.
- Aceite:
  - Build passa; tela atual ainda funcional; cores/fonte base coerentes.
- Evidencia/verificacao:
  - `cd frontend-ts && npm run build && npm run test:logic`.
  - Screenshots 1366x768 e 1440x900 comparados antes/depois.
- Rollback seam:
  - Reverter bloco de tokens/aliases.

### Fase 2 - Chrome visual sem remount

- Escopo:
  - Adaptar shell/sidebar/topbar/wallpaper/fallback como reskin.
  - Preservar render atual e todos os componentes montados.
  - Introduzir indicador global de job/automacao se derivado de estado existente.
- Arquivos provaveis:
  - `App.tsx`, `styles.css`, possivelmente assets/copias de wallpaper se aprovados.
- Dependencias:
  - Fase 1; decisao sobre wallpaper.
- Aceite:
  - App state raiz unico intacto.
  - Import/grade/settings dialogs continuam abrindo sem perda de foco.
- Evidencia/verificacao:
  - Build/test logic.
  - Smoke manual: abrir app, importar selector, editar busca, abrir settings/grades.
- Rollback seam:
  - Feature flag/classe de shell antiga ou revert de classes de chrome.

### Fase 3 - IA leve por views/anchors

- Escopo:
  - Implementar navegacao como views/anchors sem remountar estado operacional.
  - Default Produtos/Catalogo ou last-used conforme decisao.
  - Import, Grades, Execute focadas; Activity/Settings utilitarios.
- Arquivos provaveis:
  - `App.tsx`, `appLocalState.ts`, `styles.css`; possivel novo arquivo de nav config.
- Dependencias:
  - Fase 2.
- Aceite:
  - Trocar view nao reinicia import job, form, filtro, grade draft ou dialogs.
  - Indicador global continua visivel.
- Evidencia/verificacao:
  - Teste manual de troca de views durante importacao/automacao simulada em API real
    quando possivel.
  - Build/test logic.
- Rollback seam:
  - Voltar a layout single-page atual mantendo componentes.

### Fase 4 - Adaptacao de modulos densos

- Escopo:
  - Refinar ProductListControls, ProductTable, CatalogOverview e ImportStagePanel.
  - Separar visual de tabela de estados/comportamentos.
  - Nao alterar endpoints nem algoritmos.
- Arquivos provaveis:
  - `productListControls.tsx`, `productTable.tsx`, `productTableRow.tsx`,
    `catalogOverviewPanel.tsx`, `importStagePanel.tsx`, `importDiagnostics.tsx`,
    `styles.css`.
- Dependencias:
  - Fase 3 ou pode rodar parcialmente apos Fase 1 se sem IA.
- Aceite:
  - Bulk scope, filtros, busca, inline edit, empty/loading e recentes preservados.
- Evidencia/verificacao:
  - `npm run test:logic`, `npm run build`.
  - Smoke: lista vazia, filtro sem resultado, lote filtrado, editar celula, CSV.
- Rollback seam:
  - Reverter por componente; nenhum estado novo obrigatorio.

### Fase 5 - Grades, execucao, settings e recovery

- Escopo:
  - Adaptar GradeModal, ExecutionCenterPanel, SettingsModal, dialogs/toasts/diario.
  - Parada e readiness com maior visibilidade.
- Arquivos provaveis:
  - `gradeModal.tsx`, `executionCenterPanel.tsx`, `settingsModal.tsx`,
    `confirmationDialog.tsx`, `noticeDialog.tsx`, `noticeToastStack.tsx`,
    `styles.css`.
- Dependencias:
  - Fases 1-4.
- Aceite:
  - Grade dirty/save-next intactos; settings captura/diagnostico intactos; stop visivel.
- Evidencia/verificacao:
  - Build/test logic.
  - Smoke: abrir grade, mudar valor, salvar e proxima, abrir settings, captura countdown
    se ambiente permitir, readiness de execucao.
- Rollback seam:
  - Reverter componentes isolados; manter API intacta.

### Fase 6 - Hardening visual e release-ready

- Escopo:
  - A11y, contraste, performance, screenshots, docs de release.
  - Regenerar `frontend-ts/dist` somente aqui, se release for aprovada.
- Arquivos provaveis:
  - `styles.css`, docs de release, `frontend-ts/dist` apenas no corte final.
- Dependencias:
  - Todas as fases anteriores aceitas.
- Aceite:
  - Matriz desktop aprovada, sem vazamento de prototipo.
  - `frontend-ts/dist` atualizado apenas quando pronto para publicar.
- Evidencia/verificacao:
  - `cd frontend-ts && npm run build && npm run test:logic`.
  - Backend full pytest apenas se API/backend tocados; se visual-only, justificar skip.
  - Screenshots e axe/keyboard/contrast.
- Rollback seam:
  - Reverter dist + fontes de frontend da release visual.

## 10. Matriz de prioridade e decisoes

### Now

- Aprovar IA default: Produtos/Catalogo ou ultima workspace usada.
- Congelar tokens Nex Dark e aliases semanticos.
- Reskin de tokens/chrome sem alterar comportamento.
- Indicador global de job/automacao derivado de estado existente.
- Desktop-first 1366/1440/1920 + 1024 como minimo gracioso.

### Next

- Views/anchors sem remount.
- Reorganizacao visual de Catalogo, Importar e Executar.
- Activity/recovery consolidando diario, undo/redo e recentes.
- Grade modal com polish visual e foco/dirty reforcados.

### Later

- Appearance settings completas.
- Wallpaper selector/upload customizado.
- Overview rica se provar valor operacional.
- Extracao gradual de hooks/componentes de `App.tsx` apos estabilizacao.

### Out

- Auth/senha/sessao como backlog de produto.
- Mobile parity completa sem decisao explicita.
- Copiar demo data/simulacoes/prototype annotations.
- Refactor de backend/API junto com reskin visual.
- Prometer recuperacao de jobs em memoria apos restart.

### Decisoes/perguntas de produto

1. Workspace inicial:
   - Recomendacao: ultima usada; fallback `Produtos/Catalogo`.
   - Pergunta: aceitar ou preferir `Overview`?
2. Mobile parity:
   - Recomendacao: desktop-first com narrow monitoring/editing gracioso.
   - Pergunta: existe requisito real de operar cadastro/grades em celular?
3. Overview:
   - Recomendacao: opcional e secundaria; nao default inicialmente.
   - Pergunta: manter como resumo ou remover do primeiro corte?
4. Wallpaper custom upload:
   - Recomendacao: nao no primeiro corte; usar wallpapers oficiais/fallback solido.
   - Pergunta: usuario final deve escolher imagem propria?
5. Appearance settings:
   - Recomendacao: adiar; se houver, localStorage only.
   - Pergunta: precisa controle de brilho/transparencia no produto?
6. Nome da area:
   - Recomendacao: `Produtos` para linguagem diaria, com subtitulo `Catalogo local`.
   - Pergunta: preferir `Catalogo` por coerencia com docs/prototipo?

## 11. Matriz de testes e verificacao

### Checks de projeto

- Frontend logica/build:
  - `cd frontend-ts && npm run test:logic`
  - `cd frontend-ts && npm run build`
- Backend:
  - Se slice for visual-only e API intocada: nao rodar full `python -m pytest` a cada
    fatia; registrar skip justificado.
  - Se tocar API/backend/contratos: `python -m pytest` obrigatorio.
- Dist:
  - Nao regenerar `frontend-ts/dist` em fatias intermediarias.
  - Regenerar somente na Fase 6 release-ready.

### Viewports de screenshot

- Primarios:
  - 1366x768
  - 1440x900
  - 1920x1080
- Secundarios:
  - 1024x768
- Mobile:
  - 390x844 ou 430x932 apenas se narrow/mobile estiver escopado para a fatia.
  - Nao usar mobile screenshot como promessa de full parity.

### Workflow smoke scenarios

- Boot:
  - UI carrega produtos/totais/marcas/margem/automacao/history.
  - WebSocket conectado ou fallback polling legivel.
- Importacao:
  - Selecionar arquivo.
  - Iniciar importacao.
  - Ver progresso/status/result/warnings.
  - Testar erro de arquivo invalido se fixture disponivel.
  - Confirmar que IA e leitura local aparecem como escolhas distintas, sem hierarquia.
- Cadastro manual:
  - Criar produto minimo.
  - Confirmar lista/totais atualizados.
- Revisao/tabela:
  - Busca com resultado e sem resultado.
  - Filtros de review/grade/marca/codigo/categoria.
  - Inline edit liberado e travado.
  - Aplicar marca/categoria em escopo filtrado.
  - Ordenacao e create set bloqueiam lote.
- Grades:
  - Abrir modal.
  - Alterar quantidade e ver dirty.
  - Salvar.
  - Salvar e proxima pendencia.
  - Tentativa de fechar/trocar durante transition locked.
- Automacao:
  - Readiness com bloqueios.
  - Start complete/catalog/grades quando permitido.
  - Stop acessivel.
  - Current row destacado quando estado exposto.
  - Confirmacao humana quando endpoint/ambiente exigir.
- Recovery:
  - Snapshot antes de destrutiva/lote.
  - Undo/redo via botao e atalho com guard em input.
  - Diario/toast apos sucesso e erro.
- Settings:
  - Abrir/fechar com foco restaurado.
  - Recarregar contexto.
  - Preparar ByteEmpresa.
  - Salvar targets/grade config se ambiente permitir.

### A11y, contraste, teclado e performance

- Axe ou auditoria equivalente em Chrome para views principais.
- Navegacao por teclado:
  - Skip link, topbar/nav, tabela, popovers, modais, toasts nao focaveis indevidos.
- Contraste:
  - Texto 13px AA em superficies glass reais.
  - Chips de warning/error/success legiveis sem depender apenas de cor.
- Reduced motion:
  - `prefers-reduced-motion` remove animacoes longas.
- Performance:
  - Tabela grande continua com janela de renderizacao.
  - Backdrop-filter/wallpaper nao degradam interacao em 1366x768.
- Prototipo leakage:
  - Nenhum `data-od-id`, `demoProducts`, `Simular`, `Protótipo`, `Dados demonstrativos`,
    `R$ --` ou copy de simulacao no app final.

### Estados de benchmark visual

- Lista vazia.
- Lista com 3-5 produtos variados.
- Lista grande suficiente para scroll/windowing.
- Filtro ativo com escopo parcial.
- Import job running.
- Import success com warnings.
- Grade pendente e grade completa.
- Automacao ready, running e error.
- Settings com capture countdown.
- Modal/dialog/toast simultaneos dentro do limite esperado.

## 12. Definicao de pronto e proximo passo

### Definition of done do plano aprovado

- Decisoes de produto respondidas ou defaults aceitos.
- Tickets/fatias criados a partir das fases 0-6.
- Invariantes listados em cada ticket.
- Visual reskin separado de navegacao/refactor/estado.
- Estrategia de rollback por fase documentada.
- Checks e screenshots definidos antes da primeira implementacao.
- Auth mantido como opcional/legado, fora do backlog ativo.
- Nenhuma promessa de mobile parity completa sem decisao explicita.
- Nenhuma afirmacao de gate de revisao pre-persistencia inexistente.

### Proximo passo concreto

1. Aprovar ou alterar as decisoes da secao 10.
2. Criar tickets/slices de implementacao com base nas fases 1-6.
3. So depois iniciar codigo, com a primeira fatia limitada a tokens/chrome visual.
4. Nao codar ainda a partir deste documento sem aprovacao explicita.
