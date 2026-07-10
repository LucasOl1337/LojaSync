![LojaSync v1.2.6](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.6/v1.2.6-card.png)

# v1.2.6 - Estados operacionais claros e monitor configuravel (10/07/2026)

LojaSync v1.2.6 fecha a auditoria das branches locais posteriores ao v1.2.5. O patch porta somente duas entregas confirmadas que ainda nao estavam no release publicado: a migracao visual de estados operacionais e a opcao de porta do monitor LLM no launcher.

## Mudancas percebidas

| Area | Trabalho real confirmado | Evidencia (arquivos/commits/testes) | Como o usuario percebe na pratica | Status/risco |
| --- | --- | --- | --- | --- |
| UX operacional | Tokens consistentes de sucesso, aviso e erro; chips, prontidao, diario e linhas com pendencia ganharam contraste e marcacao lateral | `frontend-ts/src/styles.css`; origem auditada `472e8d2..aa89e6a`; build e smoke visual desktop/mobile | Alertas e produtos que exigem revisao ficam mais faceis de distinguir sem mudar o fluxo | Confirmado; baixo risco visual |
| Launcher/LLM | Nova opcao `--llm-monitor-port` encaminhada ao runtime do monitor | `launcher.py`, `tests/test_launcher.py`; origem auditada `b62964d` | Quem usa porta alternativa pode iniciar o monitor sem depender apenas de defaults internos | Confirmado; aditivo e retrocompativel |
| Distribuicao | Bundle React e metadata de versao sincronizados em 1.2.6 | `frontend-ts/dist/*`, `pyproject.toml`, `package*.json`, `app.py`, OpenAPI e teste de release | Atualizacao chega pronta para executar e reporta a versao correta | Invisivel no fluxo normal; baixo risco |
| Auditoria | Branches locais, worktrees, sessoes e prototipos foram classificados sem apagar ou publicar material bloqueado | Git/worktrees, `SwarmLedger-*.md`, `lojasync-concepts-visual/`, releases GitHub | Nenhuma mudanca direta; evita misturar prototipos e logs no produto | Confirmado; material local preservado fora do release |

## Escopo auditado

- Baseline remoto: `v1.2.5` / `origin/main` em `567aa23119ebd80822127bb828c4157d512321ce`.
- Snapshot candidato: branch `codex/release-v1.2.6` criada da worktree limpa de release.
- Resumo do delta final: 19 arquivos, 262 linhas adicionadas e 83 removidas, incluindo bundle renomeado e um card PNG novo.
- Branches nao ancestrais revisadas: `swarm`, `swarm-gov/lojasync/geral`, `swarm-gov/lojasync/migracao-visual` e `swarm-gov/lojasync/ready-to-ship`.
- Worktrees preservadas: checkout principal bloqueado, enxame continuo, release v1.2.5 e governor documental.
- Sessoes/agentes rastreados de forma consolidada: Codex/Enxame LojaSync, Codex/ShipSwarm Governor e coleta de release atual. Nao houve evidencia nova atribuivel a Claude, ZCode, Wispr Flow, Traywork/TraeWork ou OpenCode.
- Mudancas equivalentes ja presentes em v1.2.5 e nao duplicadas: SEO, validacao JSON, falhas de conexao do Agent-First, rebuild por assets publicos e gate de metadata.
- Mantidos fora: `SwarmLedger-*.md` bloqueados e `lojasync-concepts-visual/` sem integracao/validacao aprovada.

## Validacao

- `python -m pytest -q`: suite backend completa aprovada.
- `cd frontend-ts && npm run test:logic`: 112 testes aprovados.
- `cd frontend-ts && npm run build`: aprovado; `frontend-ts/dist/` regenerado.
- Smoke visual no navegador integrado: desktop e 390 x 844, sem overflow horizontal, overlay ou erros de console; alternancia de modo exercitada.
- `git diff --check`: aprovado; somente avisos esperados de LF/CRLF no Windows.

## Riscos, compatibilidade e migracao

- Sem breaking changes e sem migracao de dados.
- A automacao desktop continua dependente de Windows, Byte Empresa aberto e coordenadas calibradas.
- O fallback LLM continua dependente do provedor/configuracao externa; a nova flag apenas torna a porta do monitor configuravel.
- A pseudo-classe CSS `:has()` exige navegadores Chromium modernos, compativel com o runtime desktop atual.

## Veredito

Release recomendada como patch SemVer: mudancas aditivas, escopo pequeno, compatibilidade preservada e gates automatizados/visuais aprovados.

---

Base: `v1.2.5` -> `v1.2.6`  
Tag: `v1.2.6`  
Publicacao: GitHub `main` e GitHub Release.
