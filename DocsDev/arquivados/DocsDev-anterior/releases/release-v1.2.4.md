![LojaSync v1.2.4](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.4/v1.2.4-card.png)

# v1.2.4 - Minimax protegido e importacao confiavel (09/07/2026)

LojaSync e uma plataforma desktop-web local para cadastro assistido de produtos no Byte Empresa. Esta release fixa o caminho de IA em Minimax via LLM3/Ollama compativel e adiciona uma guarda local para impedir persistencia de OCR sem validacao.

## Novidades

1. **Minimax como padrao:** `minimax-m3` fica definido para texto e visao no LLM3.
2. **Guarda local obrigatoria:** todo resultado Minimax sem aprovacao automatica passa pela leitura local validada antes de gravar produtos.
3. **OCR fatiado:** PDFs renderizados como imagem sao enviados em fatias verticais ao LLM para reduzir perdas de linhas.

## Melhorias

1. **Sem Gemma escondido:** o fallback padrao foi reduzido para Minimax; Gemma nao entra automaticamente.
2. **Menos variancia:** chamadas LLM3 usam `temperature=0` e `seed=42` por padrao.
3. **Importacao mais clara:** a UI separa "Importar com IA" de "Leitura local (avancado)" e evita corte no acumulado global.
4. **Agent-First:** acoes HTTP, OpenAPI, playbook e CLI local documentam operacoes seguras.

## Sessoes e agentes

1. **Codex / Minimax OCR hardening:** integrou Minimax deterministico, guarda local, fatiamento e testes.
2. **Codex / Import UX:** ajustou textos, erro de IA e scroll lateral.
3. **Codex / Agent-First:** adicionou catalogo de acoes, OpenAPI e CLI operacional.
4. **Claude, ZCode, Wispr Flow, OpenCode e Trae Work:** sem sessao nova atribuivel encontrada localmente nesta rodada.

## Sistemas

1. Versao atualizada para `1.2.4` em `pyproject.toml`, frontend, metadata FastAPI e `/health`.
2. `Legacy/engine/LLM3/backend.py` remove fallback padrao para Gemma e torna a chamada deterministica.
3. `app/interfaces/api/http/jobs/runtime.py` impede persistencia de Minimax sem aprovacao automatica ou guarda local aprovada.
4. `PATCH_NOTES.md`, `changelog.md`, `DocsDev/releases/release-v1.2.4.md`, `DocsDev/releases/release-v1.2.4.json` e `release-assets/v1.2.4-card.png` documentam a release.

## Validacao

1. `python -m pytest -q`: 152 passed, 5 deselected, 5 subtests passed.
2. `cd frontend-ts && npm run test:logic`: 89 passed.
3. `git diff --check`: passou, apenas avisos LF/CRLF do Windows.
4. `2866.pdf` repetido 3 vezes: 3/3 aprovado com guarda local.
5. Super Romaneios parcial final: 15/15 aprovados em `DocsDev/validation/llm3-minimax-guard-final-super-romaneios-full-20260708-231104.json`.

---

## Notas tecnicas

- Base: `v1.2.3` -> `v1.2.4`.
- Tag planejada: `v1.2.4`.
- Ultimo release oficial antes desta rodada: `v1.2.3` em 08/07/2026.
- Z.AI permanece como experimento configuravel, mas o padrao publicado e Minimax via LLM3.
