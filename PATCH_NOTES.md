# LojaSync v1.2.4 - Patch Notes

Data: 2026-07-09

Esta release consolida a troca do fluxo de IA para Minimax via LLM3/Ollama compativel, com guarda local obrigatoria quando a IA nao aprova a importacao sozinha. O objetivo pratico e simples: usar o Minimax como motor assistido, mas impedir que OCR ou leitura de romaneio sem validacao cadastre quantidade errada.

## Destaques

- Minimax `minimax-m3` definido como modelo padrao de texto e visao no LLM3.
- Fallback automatico para Gemma removido do padrao; configuracoes antigas ainda podem tentar um modelo configurado, mas o fallback seguro volta para Minimax.
- Chamadas LLM3 agora usam `temperature=0` e `seed=42` por padrao para reduzir variancia.
- Importacao com IA ganhou guarda local: se o Minimax nao chegar em validacao automatica aprovada, a leitura local validada assume antes da persistencia.
- PDFs renderizados como imagem passam por fatias verticais antes do envio ao LLM, melhorando OCR em romaneios escaneados.
- UI de importacao separa melhor "Importar com IA" de "Leitura local (avancado)" e a lateral nao corta mais o acumulado global em zoom normal.
- Base Agent-First documentada com indice de acoes HTTP, playbook, OpenAPI e CLI operacional.

## Sessoes e agentes auditados

- **Codex / Minimax OCR hardening:** troca operacional para LLM3/Ollama, Minimax deterministico, remocao de fallback Gemma, guarda local e testes de regressao.
- **Codex / Import UX:** ajuste dos botoes de importacao, erro de IA mais acionavel e correcao de scroll lateral.
- **Codex / Agent-First:** `DocsDev/agent/*`, `tools/agent_run.py` e exportacao OpenAPI para acoes HTTP auditaveis.
- **Claude, ZCode, Wispr Flow, OpenCode e Trae Work:** nenhuma sessao nova atribuivel encontrada localmente para esta rodada; mantidos como itens sem evidencia local direta.

## Melhorias

- `Legacy/engine/LLM3/backend.py`: padrao Minimax em texto/visao, opcoes deterministicas e fallback restrito.
- `app/interfaces/api/http/jobs/llm.py`: suporta provedor Z.AI experimental sem torna-lo padrao e fatia imagens no caminho LLM3.
- `app/interfaces/api/http/jobs/runtime.py`: guarda local para todo resultado Minimax nao aprovado automaticamente.
- `app/application/imports/parsing.py`: prompts e parsing reforcados para codigo, NCM, nomes curtos e imagens fatiadas.
- `frontend-ts/src/importStagePanel.tsx` e `frontend-ts/src/styles.css`: textos e layout do painel de importacao ajustados para uso real.

## Correcoes e sistemas

- Importacao por IA nao cai mais silenciosamente para leitura local antes de tentar o servico configurado.
- Erros de saldo/plano/modelo indisponivel ficam mais claros para o operador.
- Resultados Minimax vazios, incompletos, rejeitados ou sem ancora de validacao passam por guarda local antes de persistir.
- Versao atualizada para `1.2.4` em runtime, frontend e metadata.
- Build estatico versionado do frontend atualizado para a release.

## Validacao da release

- `python -m pytest -q`: 152 passed, 5 deselected, 5 subtests passed.
- `cd frontend-ts && npm run test:logic`: 89 passed.
- `git diff --check`: passou; apenas avisos LF/CRLF esperados no Windows.
- `2866.pdf` repetido 3 vezes com Minimax + guarda local: 3/3 aprovado, 12 pecas, total R$ 1.258,80.
- `DocsDev/validation/llm3-minimax-guard-final-super-romaneios-full-20260708-231104.json`: bateria parcial em Super Romaneios com 15/15 arquivos aprovados antes da interrupcao manual; 11 usaram guarda local.
- `tests/test_llm3_model_config.py`, `tests/test_llm_provider.py` e `tests/test_import_parsing.py`: cobrem Minimax deterministico, fatiamento LLM3 e guarda local.

## Riscos conhecidos

- Minimax remoto ainda pode sofrer rate limit ou latencia; a guarda local cobre persistencia, mas nao elimina espera.
- OCR puramente visual continua caro e mais lento que PDF textual.
- A automacao desktop continua dependente de Windows, posicoes de tela e disponibilidade do Byte Empresa.
- Z.AI fica como experimento configuravel, nao como provedor padrao desta release.
