# Swarm Ledger - Documentacao

## 2026-07-09T00:18:35-03:00

- Status: bloqueado antes de alterar documentacao operacional.
- Evidencia: `git status --short --branch` mostrou worktree ja sujo com alteracoes em codigo, docs, build gerado, testes e varios untracked.
- Branch: a execucao iniciou em `main`; a criacao de `swarm/lojasync/documentacao` falhou porque ja existe a ref local `refs/heads/swarm`.
- Observacao: em checagem posterior, a branch corrente apareceu como `swarm-lojasync-geral-blocked`; nao foi possivel atribuir essa troca a esta automacao com seguranca.
- Decisao: nao foi feita melhoria documental para evitar misturar trabalho do enxame com alteracoes preexistentes.

## 2026-07-09T00:38:15-03:00

- Status: bloqueado novamente antes de alterar documentacao operacional viva.
- Evidencia: `git status --short --branch` mostrou `main...origin/main` com untracked preexistentes: `SwarmLedger-*.md` e `lojasync-concepts-visual/`.
- Branch: `git branch --list` mostrou apenas `main`, `swarm` e `swarm-lojasync-geral-blocked`; `git rev-parse --verify refs/heads/swarm` retornou commit existente e `refs/heads/swarm/lojasync/documentacao` nao existe.
- CodeGraph: `codegraph status .` esta OK e atualizado, mas nao avancei para leitura/edicao de docs por causa das regras de branch/worktree.
- Observacao: na checagem final, `git status --short --branch` passou a mostrar `swarm-lojasync-geral-blocked` sem checkout executado por esta automacao; a worktree continuou suja apenas com untracked.
- Decisao: nenhuma melhoria documental foi aplicada para nao misturar trabalho do enxame com estado sujo na `main`.

## 2026-07-09T00:58:04-03:00

- Status: bloqueado antes de alterar documentacao operacional viva.
- Evidencia: `git status --short --branch` mostrou a branch `swarm-lojasync-geral-blocked` com untracked preexistentes: `SwarmLedger-*.md` e `lojasync-concepts-visual/`.
- Observacao final: uma checagem posterior tambem mostrou `SwarmLedger-bugs.md` como untracked, reforcando atividade paralela de outro enxame.
- Branch: a branch obrigatoria `swarm/lojasync/documentacao` ainda nao aparece em `git branch --list`; existe apenas a branch local `swarm`, que bloqueia esse namespace.
- CodeGraph: `codegraph status C:\Projetos\LojaSync` esta OK e atualizado (`214` arquivos, `4.956` nos, `12.705` arestas).
- Decisao: nenhuma lacuna documental foi escolhida ou editada, para nao misturar trabalho do enxame com estado sujo de outro trabalho.
