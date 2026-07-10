# LojaSync v1.2.6 - Patch Notes

Data: 2026-07-10

Patch de auditoria pos-v1.2.5 com duas entregas confirmadas que ainda nao estavam no release publicado: estados operacionais visualmente consistentes e porta configuravel para o monitor LLM.

## Destaques

- Sucesso, aviso e erro agora usam tokens visuais consistentes em chips, validacao, diario, prontidao e tabela.
- Produtos com pendencias de revisao recebem marcacao lateral e contraste sem alterar as acoes existentes.
- O launcher aceita `--llm-monitor-port <porta>` e encaminha o valor ao runtime do monitor.
- Bundle React, FastAPI, health check, OpenAPI e metadata sincronizados em `1.2.6`.

## Relatorio consolidado

| Area | Trabalho real confirmado | Evidencia (arquivos/commits/testes) | Como o usuario percebe na pratica | Status/risco |
| --- | --- | --- | --- | --- |
| UX operacional | Estados e pendencias com linguagem visual consistente | `frontend-ts/src/styles.css`; origem `472e8d2..aa89e6a`; build e smoke visual | Alertas e itens a revisar ficam mais faceis de localizar | Confirmado; baixo risco visual |
| Launcher/LLM | Flag de porta do monitor encaminhada ao `Launcher` | `launcher.py`, `tests/test_launcher.py`; origem `b62964d` | Porta alternativa pode ser definida diretamente na inicializacao | Confirmado; aditivo |
| Distribuicao | Versao e bundle estatico atualizados | metadata, OpenAPI, `frontend-ts/dist/*`, teste de release | App pronto para atualizar e versao correta no health/API | Invisivel no uso comum; baixo risco |
| Auditoria | Branches, worktrees, sessoes e prototipos classificados sem descarte | Git/worktrees, ledgers locais e GitHub Releases | Evita publicar logs/prototipos ou duplicar fixes | Confirmado; estado local preservado |

## Baseline e snapshot

- Baseline remoto: `v1.2.5` / `origin/main` em `567aa23119ebd80822127bb828c4157d512321ce`.
- Candidato: `codex/release-v1.2.6`, criado da worktree limpa `LojaSync-release-v1.2.5`.
- Delta final: 19 arquivos, 262 linhas adicionadas e 83 removidas, incluindo bundle renomeado e um card PNG novo.
- Branches nao ancestrais auditadas: `swarm`, `swarm-gov/lojasync/geral`, `swarm-gov/lojasync/migracao-visual` e `swarm-gov/lojasync/ready-to-ship`.
- Checkout principal antigo, `SwarmLedger-*.md` e `lojasync-concepts-visual/` foram preservados sem alteracao e ficaram fora do release.

## Sessoes e agentes rastreados

- Codex / Enxame LojaSync: linha funcional ja integrada no v1.2.5.
- Codex / ShipSwarm Governor: branches de geral, migracao visual, ready-to-ship, landing, performance, bugs e documentacao cruzadas contra o diff real.
- Codex / coleta v1.2.6: baseline, equivalencia, qualidade, testes, smoke visual e publicacao.
- Claude, ZCode, Wispr Flow, Traywork/TraeWork e OpenCode: nenhuma evidencia nova atribuivel por commit/worktree para este delta.

## Itens auditados e nao duplicados

- SEO da branch `swarm`, validacao de JSON, falhas de conexao do Agent-First, rebuild por assets publicos e gate de metadata ja estavam funcionalmente presentes em v1.2.5.
- Ledgers de rodadas bloqueadas e conceito visual desconectado continuam como evidencia/prototipo local, nao como produto publicavel.
- Nenhuma mudanca de auth/senha foi proposta ou priorizada.

## Validacao

- `python -m pytest -q`: suite backend completa aprovada.
- `cd frontend-ts && npm run test:logic`: 112 passed.
- `cd frontend-ts && npm run build`: passou; bundle versionado regenerado.
- Smoke visual: desktop e 390 x 844, sem overflow horizontal, overlay ou erros de console; alternancia de modo exercitada.
- `git diff --check`: passou; apenas avisos esperados de LF/CRLF no Windows.

## Riscos e migracao

- Sem breaking changes e sem passos de migracao.
- Automacao desktop segue dependente de Windows, Byte Empresa e coordenadas calibradas.
- LLM continua dependente do provedor/configuracao externa; a nova flag apenas configura a porta do monitor.
- `:has()` depende de Chromium moderno, compativel com o runtime desktop atual.

## Veredito

Recomendado publicar como patch SemVer v1.2.6: escopo pequeno, aditivo e retrocompativel, com checks automatizados e smoke visual aprovados.
