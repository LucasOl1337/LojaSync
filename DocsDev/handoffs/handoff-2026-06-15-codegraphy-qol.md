# Handoff - CodeGraphy, Arquitetura e QoL

Data/hora local da geracao: 2026-06-15 06:49:43 -03:00  
Projeto: `C:\Projetos\LojaSync`  
Tema principal: rodada longa de manutencao com CodeGraphy, investigacao de arquitetura/eficiencia e melhorias de qualidade de vida do usuario final.

## Objetivo Central

O objetivo ativo da sessao foi modernizar e auditar o repositorio LojaSync, que ficou muito tempo sem manutencao e recebeu boa parte do codigo de modelos antigos. A meta combinou:

- Implantar e usar CodeGraphy como ferramenta de leitura arquitetural.
- Investigar hotspots, acoplamento, eficiencia e riscos de manutencao.
- Identificar bugs criticos e hardenings, sem transformar problemas teoricos em prioridade quando seis meses de uso real nao mostraram incidencia.
- Criar melhorias de qualidade de vida para o operador final, principalmente no fluxo diario de revisao/cadastro de produtos.

## Decisoes Tomadas

- Prioridade principal: arquitetura, manutenibilidade, eficiencia e QoL. Bugs sem evidencia real de incidencia foram rebaixados para hardening ou baixo risco.
- Mudancas de frontend devem ser feitas em fatias pequenas, com teste RED/GREEN, build, verificacao em Chrome e registro em auditoria.
- Filtros, chips e estados visuais de revisao devem ser navegacao local reversivel. Nao devem alterar API, payload, produtos, ordenacao real, selecao de linha ou automacao.
- O CodeGraphy deve ser usado como evidencia de tamanho/impacto, mas `codegraph affected` nao deve ser usado como unico gate porque ja deixou de apontar testes relevantes.
- `frontend-ts/dist/index.html` deve ficar sem diff quando o Vite apenas troca hashes do build.
- Por regra do usuario/AGENTS: executar autonomamente quando possivel, interpretar possiveis erros de transcricao por contexto e nao usar Playwright; preferir Chrome/Codex app para verificacao visual.
- Para esta passagem de bastao, foi criado `DocsDev/`. As docs importantes foram copiadas para la sem remover os originais em `docs/`, para evitar quebrar referencias existentes.

## Planejamento Registrado

Foram registradas tres rodadas em `DocsDev/architecture/qol-feature-rounds.md`:

1. Fundacao e seguranca de mudanca: reduzir risco, preservar contratos e criar auditor de review.
2. QoL guiado por fluxo real: melhorar tarefas repetidas do operador sem quebrar habitos atuais.
3. Rodada criativa: novas features pequenas, reversiveis e auditaveis, sempre com auditor que confira regressao.

Checklist recorrente usado nas fatias:

- Escolher uma feature pequena.
- Adicionar ou atualizar teste antes da implementacao.
- Rodar teste, build, `git diff --check` e Chrome quando houver UI.
- Atualizar `codegraphy-audit.md` com regra, motivacao, prova e impacto.

## Implementado ou Alterado Nesta Rodada

### Documentacao e CodeGraphy

- Criado/atualizado `docs/architecture/codegraphy-audit.md` com snapshot, criterio de priorizacao, hotspots, hardenings, evidencias das fatias e guardrails.
- Criado/atualizado `docs/architecture/qol-feature-rounds.md` com as rodadas planejadas e fatias QoL executadas.
- Criado `DocsDev/` e copiadas para ele as docs principais:
  - `DocsDev/architecture/blueprint.md`
  - `DocsDev/architecture/codegraphy-audit.md`
  - `DocsDev/architecture/qol-feature-rounds.md`
  - `DocsDev/distribution/productization-plan.md`
  - `DocsDev/migration/component-inventory.md`
  - `DocsDev/migration/equivalence-matrix.md`
  - `DocsDev/loja-sync-divulgacao/icp.md`
  - `DocsDev/loja-sync-divulgacao/pitch-base.md`

Snapshot CodeGraphy mais recente conhecido:

- Arquivos: 188
- Nos: 3.734
- Edges: 8.184
- DB: 8.30 MB
- Status: indice atualizado

### Arquitetura e Hotspots

O foco foi reduzir gradualmente o peso de `frontend-ts/src/App.tsx` e de pontos grandes do backend sem fazer um refactor destrutivo.

Extracoes/organizacao frontend registradas:

- `gradeLogic.ts`
- `productPricing.ts`
- `productOrdering.ts`
- `uiFormatting.ts`
- `productEditing.ts`
- `productForm.ts`
- `keyboardShortcuts.ts`
- `appConfig.ts`
- `importDiagnostics.tsx`
- `importStagePanel.tsx`
- `operationalHealthPanel.tsx`
- `gradeModal.tsx`
- `productTable.tsx`
- `productTableRow.tsx`
- `editableProductCell.tsx`
- `productListControls.tsx`
- `productListToolPanels.tsx`
- `executionCenterPanel.tsx`
- `productEntryPanel.tsx`
- `operationalSummaryPanel.tsx`
- `settingsModal.tsx`

Extracoes/organizacao backend registradas:

- `app/application/imports/pdf_text.py`
- `app/application/imports/job_validation.py`
- `app/domain/products/money.py`
- `app/domain/products/grade_utils.py`
- `app/domain/products/post_processing.py`
- `app/application/products/post_process_prompt.py`
- `app/application/automation/product_payload.py`

### Hardening e Correcao de Riscos

Foram feitos hardenings locais com testes, tratados como reducao de risco e nao como incidentes confirmados:

- Rejeicao de preco malformado ou negativo em criacao/edicao.
- Protecao de totais/previews contra precos negativos vindos de dados antigos/importados.
- Normalizacao/tolerancia de quantidade invalida ou negativa de dados legados.
- Rejeicao de inteiros de prompt com sufixo.
- Validacao de pontos de calibracao invalidos.
- Normalizacao de configuracao de grades.
- Deduplicacao de chaves no rascunho de ordenacao.
- Preservacao de quantidade zero na edicao inline.
- Rejeicao de quantidade inline com sufixo como `12abc`.
- Bloqueio de quantidade fracionada no cadastro manual.
- Ordenacao de tamanhos normalizados como `P/M`, `M/G` e tamanhos de mes como `6M`.

### QoL do Usuario Final

Fatias de QoL implementadas e documentadas:

- Checklist inicial de prontidao para `Cadastro Completo`, derivado de produtos, grades pendentes, automacao e targets.
- Diario local de operacao em `localStorage`, com eventos confirmados pela UI.
- Complemento do diario para criacao/edicao/remocao de produtos e acoes em massa relevantes.
- Visao rapida `Revisar`, persistida em `localStorage`, agrupando pendencias visuais.
- Chips por linha para pendencias de revisao.
- Chips acionaveis que aplicam o filtro correspondente sem selecionar linha nem mudar ordenacao.
- Faixa de contexto do filtro ativo com contagem e acoes reversiveis.
- Estado vazio filtrado com mensagens e recuperacao (`Mostrar todos`, `Voltar para Revisar`).
- Filtro/chip `Sem categoria`: produtos com categoria vazia entram em `Revisar`, aparecem no filtro `Sem categoria` e recebem chip. Motivacao: o ByteEmpresa usa `categoria` para grupo e categoria vazia/desconhecida cai no fallback `m`.

## Provas e Validacoes Conhecidas

Provas mais recentes da fatia `Sem categoria`:

- RED: `npm run test:logic` falhou em 4 testes esperados antes da implementacao.
- GREEN: `npm run test:logic` passou com 58 testes.
- `npm run build` passou.
- Chrome abriu `http://127.0.0.1:5173/`, renderizou o login do LojaSync e logs de erro/warn ficaram `[]`.
- `git diff --check` passou, restando apenas avisos LF/CRLF ja existentes.
- Vite foi parado e a porta 5173 ficou livre.
- `frontend-ts/dist/index.html` ficou sem diff.
- `codegraph sync .` ficou atualizado; `codegraph status .` confirmou 188 arquivos, 3.734 nos e 8.184 edges.

Observacao: apos a criacao deste handoff e a copia para `DocsDev/`, nao foi rodada novamente a suite completa. As operacoes finais foram de documentacao/copia.

## Estado Atual Do Worktree

O worktree esta intencionalmente sujo por causa da rodada longa. Ha muitos arquivos modificados e muitos arquivos novos nao rastreados, incluindo novos helpers, testes e documentos.

Nao houve stage nem commit nesta sessao.

Arquivos/documentos mais importantes para o proximo agente verificar primeiro:

- `DocsDev/handoffs/handoff-2026-06-15-codegraphy-qol.md`
- `DocsDev/architecture/codegraphy-audit.md`
- `DocsDev/architecture/qol-feature-rounds.md`
- `frontend-ts/src/productFilters.ts`
- `frontend-ts/test/productFilters.test.mjs`
- `frontend-ts/src/App.tsx`
- `frontend-ts/src/productListControls.tsx`
- `frontend-ts/src/productTable.tsx`
- `frontend-ts/src/productTableRow.tsx`
- `app/application/imports/job_validation.py`
- `app/application/automation/product_payload.py`
- `app/domain/products/grade_utils.py`

## Pendencias

- A meta global ainda nao esta completa; esta sessao estava em rodada incremental.
- A proxima fatia QoL estava sendo investigada quando a sessao foi encerrada. A ideia era continuar a partir dos filtros/revisao de produtos e campos usados pela automacao, mas nada novo foi implementado depois da fatia `Sem categoria`.
- Definir se `DocsDev/` passa a ser a pasta canonica de documentacao ou apenas um espelho centralizado de handoff. Por enquanto os originais em `docs/` foram preservados.
- Revisar e organizar o grande conjunto de arquivos nao rastreados antes de stage/commit.
- Rodar uma verificacao mais ampla antes de qualquer merge: testes frontend, build, testes Python relevantes e Chrome.
- Continuar reduzindo hotspots que ainda permanecem grandes, especialmente `frontend-ts/src/App.tsx`, `app/application/products/service.py`, `app/application/automation/service.py`, `app/application/imports/parsing.py` e `app/interfaces/api/http/jobs/runtime.py`.

## Riscos, Bugs e Pontos De Atencao

- Varios hardenings mexem em validacao de entrada. Como o usuario informou que esses bugs nao apareceram em seis meses de uso, revisar impacto operacional antes de tratar como urgente.
- `DocsDev/` agora contem copias; se alguem editar `docs/` e `DocsDev/` separadamente, pode haver divergencia.
- O indice CodeGraphy nao substitui testes. Ele ajuda a orientar impacto, mas ja houve evidencia de que `codegraph affected` pode nao listar todos os testes relevantes.
- O repositorio em Windows mostra avisos LF/CRLF em varios arquivos no `git diff --check`; nao foram tratados nesta rodada.
- Nao usar Playwright conforme regra do projeto; usar Chrome/Codex app para verificacao visual.
- `frontend-ts/dist/index.html` pode mudar hash no build. Se a unica mudanca for hash/asset, restaurar para evitar ruido no diff.
- A automacao ByteEmpresa usa categoria para escolher grupo e tem fallback. O filtro `Sem categoria` apenas torna isso visivel ao operador; nao muda a automacao.

## Proximos Passos Recomendados

1. Abrir `DocsDev/architecture/codegraphy-audit.md` e `DocsDev/architecture/qol-feature-rounds.md` para recuperar o mapa da rodada.
2. Rodar:

```powershell
git status --short
codegraph status .
npm run test:logic --prefix frontend-ts
npm run build --prefix frontend-ts
```

3. Se houver mudanca UI, abrir no Chrome/Codex app e confirmar DOM, console limpo e fluxo principal.
4. Escolher uma proxima fatia pequena, de preferencia QoL operacional ou reducao de hotspot com teste puro.
5. Manter o padrao RED/GREEN, build, Chrome, `git diff --check`, CodeGraphy e atualizacao do handoff/auditoria.
6. Antes de commit, agrupar arquivos por tema. A rodada tem muitas mudancas independentes e pode precisar de commits separados.

## Resumo Para O Proximo Agente

Continue como uma rodada longa, nao como bugfix isolado. O usuario quer manutencao real, arquitetura mais legivel, eficiencia e features de qualidade de vida. A prioridade foi corrigida durante a conversa: nao focar apenas em bugs teoricos. Trabalhe em fatias pequenas, preserve comportamento atual, prove com testes e registre a motivacao. O estado atual tem muito progresso, mas ainda precisa de revisao cuidadosa, organizacao de commits e continuidade nas proximas features/refactors.
