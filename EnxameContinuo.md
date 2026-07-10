# Enxame Continuo - LojaSync

Arquivo de coordenacao da automacao `enxame-cont-nuo-lojasync` na worktree
`C:\Projetos\LojaSync-enxame` e branch `enxame/lojasync/continuo`.

## BACKLOG DO ENXAME

- [ ] Isolar o CodeGraph da worktree: `codegraph status .` resolve o projeto como
  `C:\Projetos` e mistura milhares de arquivos externos; `codegraph index . --force`
  foi tentado nesta rodada, mas tambem herdou o indice ancestral.

## Claims ativos

| Sessao | Area | Entrega | Arquivos reivindicados | Status |
|---|---|---|---|---|
| - | - | - | - | nenhum claim ativo |

## Rodadas concluidas

### 2026-07-09-05 - Pulso diario de produtividade

- Area sorteada: Analytics de produto e eventos de uso.
- Entrega: o resumo operacional ganhou o painel `Pulso de hoje`, que transforma
  eventos locais de produto, importacao, automacao e grades em indicadores de
  atividades, conclusoes, fluxos assistidos, taxa sem falhas, distribuicao por
  categoria, ritmo dominante e horario da ultima acao.
- Arquivos: `frontend-ts/src/usageAnalytics.ts`,
  `frontend-ts/src/usageAnalyticsPanel.tsx`,
  `frontend-ts/src/operationalSummaryPanel.tsx`, `frontend-ts/src/App.tsx`,
  `frontend-ts/src/appLocalState.ts`, `frontend-ts/src/styles.css`,
  `frontend-ts/test/usageAnalytics.test.mjs`,
  `frontend-ts/test/appLocalState.test.mjs`, `frontend-ts/package.json`,
  `frontend-ts/dist/**`.
- Antes: o app registrava eventos operacionais, mas guardava apenas seis e nao
  apresentava nenhum resumo de uso ou produtividade ao dono.
- Depois: o dono acompanha o pulso do dia sem sair do fluxo; a retencao local
  limitada a 120 eventos evita que uma rotina intensa apague a leitura diaria.
- Evidencia literal da suite frontend: `tests 101`, `pass 101`, `fail 0`.
- Evidencia literal do build final: `53 modules transformed.` e
  `built in 164ms`.
- Evidencia literal do diff: `git diff --check` sem erros.
- Commit: este commit.

### 2026-07-09-04 - Visao comercial acionavel do catalogo

- Area sorteada: Telas e paginas de frontend.
- Entrega: a area de trabalho ganhou o painel `Visao do catalogo`, que mostra
  capital no lote, venda projetada, ganho bruto potencial e percentual de
  prontidao do catalogo.
- Arquivos: `frontend-ts/src/catalogOverview.ts`,
  `frontend-ts/src/catalogOverviewPanel.tsx`, `frontend-ts/src/App.tsx`,
  `frontend-ts/src/styles.css`, `frontend-ts/test/catalogOverview.test.mjs`,
  `frontend-ts/package.json`, `frontend-ts/dist/**`.
- Antes: totais existiam na barra lateral e as regras de revisao estavam
  implementadas, mas o dono precisava interpretar a tabela e nao conseguia
  acionar os filtros de pendencia pela tela atual.
- Depois: indicadores comerciais ficam visiveis no topo da area operacional;
  cartoes de pendencias filtram a lista por revisao, grade, codigo, marca ou
  categoria, persistem a escolha e removem automaticamente filtros obsoletos.
- Evidencia literal da suite frontend: `tests 99`, `pass 99`, `fail 0`.
- Evidencia literal do build final: `51 modules transformed.` e
  `built in 168ms`.
- Evidencia literal do diff de fontes: `git diff --check` sem erros.
- Commit: este commit.

### 2026-07-09-03 - Produto existente como modelo de novo cadastro

- Area sorteada: Novos recursos / capacidades criativas.
- Entrega: cada linha da lista ganhou a acao acessivel `Usar como modelo`, que
  preenche o cadastro manual com nome, custo, venda, categoria, marca,
  descricao, grades e cores do produto escolhido.
- Arquivos: `frontend-ts/src/productTemplate.ts`,
  `frontend-ts/test/productTemplate.test.mjs`, `frontend-ts/package.json`,
  `frontend-ts/src/productTableRow.tsx`, `frontend-ts/src/productTable.tsx`,
  `frontend-ts/src/App.tsx`, `frontend-ts/src/styles.css`,
  `frontend-ts/dist/**`.
- Antes: cadastrar uma variacao parecida exigia redigitar os dados do produto
  ou editar uma copia fora do LojaSync.
- Depois: um clique prepara o formulario, leva o foco ao nome e confirma a acao;
  codigo e quantidade sao reiniciados para evitar duplicacao acidental, e as
  colecoes aninhadas sao clonadas sem alterar a linha original.
- Evidencia literal da suite frontend: `tests 96`, `pass 96`, `fail 0`.
- Evidencia literal do build final: `49 modules transformed.` e
  `built in 179ms`.
- Evidencia literal do diff: `git diff --check` sem erros.
- Commit: este commit.

### 2026-07-09-01 - Busca responsiva em catalogos grandes

- Area sorteada: Performance perceptivel.
- Entrega: o texto pesquisavel dos produtos agora e normalizado e compactado uma
  vez por atualizacao/ordenacao do catalogo; consultas digitadas reutilizam esse
  indice em memoria.
- Arquivos: `frontend-ts/src/productFilters.ts`, `frontend-ts/src/App.tsx`,
  `frontend-ts/test/productFilters.test.mjs`, `frontend-ts/dist/**`.
- Antes: o benchmark de 20.000 produtos e 12 consultas reconstruiu o texto de
  todos os produtos a cada consulta, com `median_ms=733.93` e `p95_ms=954.33`.
- Depois: o mesmo benchmark reutilizou o indice, preservou o checksum `3029025`
  e mediu `median_ms=27.58` e `p95_ms=41.75` (96,2% menos tempo mediano).
- Evidencia literal: `SEARCH_BENCHMARK strategy=per-query-normalization products=20000 queries=12 median_ms=733.93 p95_ms=954.33 checksum=3029025`.
- Evidencia literal: `SEARCH_BENCHMARK strategy=prebuilt-index products=20000 queries=12 median_ms=27.58 p95_ms=41.75 checksum=3029025`.
- Evidencia literal: `tests 90`, `pass 90`, `fail 0`.
- Evidencia literal do build: `47 modules transformed.` e `built in 181ms`.
- Commit: este commit.

### 2026-07-09-02 - Catalogo visivel exportavel em CSV

- Area sorteada: Novos recursos / capacidades criativas.
- Entrega: a barra de ferramentas ganhou `Baixar CSV`, que exporta o catalogo
  inteiro ou somente os produtos visiveis quando ha uma busca ativa.
- Arquivos: `frontend-ts/src/productExport.ts`,
  `frontend-ts/test/productExport.test.mjs`,
  `frontend-ts/src/productListControls.tsx`, `frontend-ts/src/App.tsx`,
  `frontend-ts/src/styles.css`, `frontend-ts/package.json`,
  `frontend-ts/dist/**`.
- Antes: dados do catalogo ficavam presos a tabela e precisavam ser
  retranscritos para planilhas ou compartilhamento externo.
- Depois: um clique gera arquivo datado em UTF-8, separado por ponto e virgula,
  com nome, codigo, quantidade, precos, categoria, marca, grade, cores e
  descricao; a exportacao respeita a busca atual e neutraliza formulas de
  planilha.
- Evidencia literal da suite frontend: `tests 93`, `pass 93`, `fail 0`.
- Evidencia literal do build final: `48 modules transformed.` e
  `built in 179ms`.
- Commit: este commit.
