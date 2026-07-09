# SwarmLedger - documentacao

## 2026-07-09 - governor

- Assunto: documentacao.
- Branch: `swarm-gov/lojasync/documentacao`.
- Mudanca: criado `DocsDev/INDEX.md` para centralizar os documentos vivos de operacao, arquitetura, migracao visual, releases e handoffs.
- Validacao planejada: `git diff --check`.
- Risco: baixo; alteracao documental sem impacto em runtime.

## 2026-07-09 - governor - Agent-First headless

- Assunto: documentacao.
- Branch: `swarm-gov/lojasync/documentacao`.
- Mudanca: documentado gate headless no playbook Agent-First, separando leitura, simulacao, mutacao real, recuperacao e automacao desktop.
- Validacao planejada: `git diff --check`.
- Risco: baixo; alteracao documental sem impacto em runtime.

## 2026-07-09 - governor - fonte canonica DocsDev

- Assunto: documentacao.
- Branch: `swarm-gov/lojasync/documentacao`.
- Mudanca: clarificada em `DocsDev/INDEX.md` a relacao entre `DocsDev/` como fonte operacional canonica e `docs/` como ponte/material publico para reduzir drift documental.
- Validacao planejada: `git diff --check`.
- Risco: baixo; alteracao documental sem impacto em runtime.

## 2026-07-09 - governor - matriz de validacao rapida

- Assunto: documentacao.
- Branch: `swarm-gov/lojasync/documentacao`.
- Mudanca: adicionada a `DocsDev/INDEX.md` uma matriz de validacao barata por escopo, cobrindo documentacao, contrato Agent-First, backend, frontend e release local.
- Validacao planejada: `git diff --check`.
- Risco: baixo; alteracao documental sem impacto em runtime.

## 2026-07-09 - Indice ponte para docs publicos

- Assunto: documentacao.
- Branch: `swarm-gov/lojasync/documentacao`.
- Mudanca: criado `docs/INDEX.md` para direcionar manutencao para `DocsDev/INDEX.md` e documentar o papel dos subdiretorios publicos.
- Arquivos tocados: `docs/INDEX.md`, `SwarmLedger-documentacao.md`.
- Validacao: `git diff --check`.
- Risco: baixo; alteracao somente documental, sem runtime, auth, seed, deploy ou migracao remota.
