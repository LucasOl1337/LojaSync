![LojaSync v1.2.3](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.3/v1.2.3-card.png)

# v1.2.3 - Venda controlada, onboarding e release multiagente (08/07/2026)

LojaSync e uma plataforma desktop-web local para cadastro assistido de produtos no Byte Empresa, com painel React, API FastAPI, leitura de romaneios/NF-e, persistencia SQLite e automacao Windows. Esta release consolida a rodada multiagente posterior ao `v1.2.2` e integra apenas os itens aprovados para publicacao.

## Novidades

1. **Oferta Early Access:** nova pagina publica em `/oferta.html` apresenta piloto inicial sugerido de R$ 497, limites do teste, entregaveis e proximo passo comercial.
2. **Kit de confianca:** documento comercial com FAQ, privacidade resumida, termos de piloto, checklist de venda controlada e scripts de WhatsApp.
3. **Smoke de assets versionados:** teste garante que o `frontend-ts/dist/index.html` nao aponte para CSS/JS inexistentes.

## Melhorias

1. **SEO e preview social:** titulo, descricao, Open Graph, Twitter card, tema e manifest melhoram a primeira impressao em links publicos controlados.
2. **Primeiro lote guiado:** a lista vazia agora oferece CTAs reais para importar o primeiro romaneio ou cadastrar produto manualmente.
3. **Carregamento inicial menor:** `AuthShell` usa `React.lazy` e `Suspense` para separar o painel operacional do gate inicial.
4. **Documentacao viva:** docs duplicados viraram pontes, materiais obsoletos foram marcados como historico/superseded e auth foi reforcado como infraestrutura opcional/legada.

## Sessoes e agentes

1. **Codex / ShipSwarm:** integrou SEO publico, oferta Early Access, kit de confianca, performance inicial e onboarding vazio.
2. **Codex / DailyBugSwarm:** integrou ledger de QA diario e smoke test de assets do frontend versionado.
3. **Codex / DocsSwarm:** integrou higiene documental, classificacao de fontes canonicas e pontes `docs/` -> `DocsDev/`.
4. **Claude:** sem sessao/commit atribuivel encontrado localmente desde `v1.2.2`; apenas referencia historica ao `CLAUDE.md` do CodeGraph.
5. **ZCode, Wispr Flow, OpenCode e Trae Work:** sem sessoes/commits atribuiveis encontrados localmente desde `v1.2.2`.

## Itens fora do release

1. `f87b1d1` (`Improve unauthenticated access gate`) ficou fora por priorizar auth/senha como experiencia comercial ativa.
2. Branch `swarm` / `05d6bb1` ficou fora porque e uma alternativa SEO paralela e conflitante com o `main`.
3. `lojasync-concepts-visual/` ficou fora por ser prototipo visual nao conectado ao runtime e sem validacao visual final.
4. Snapshots `refs/codex/snapshots/*` foram auditados como memoria de worktree e nao integrados automaticamente.

## Sistemas

1. Versao atualizada para `1.2.3` em `pyproject.toml`, frontend, metadata FastAPI e `/health`.
2. Build estatico versionado aponta para `frontend-ts/dist/assets/index-vXSbsgx9.js`, `frontend-ts/dist/assets/App-WUILa4KL.js` e `frontend-ts/dist/assets/index-CXySh6k9.css`.
3. `PATCH_NOTES.md`, `changelog.md`, `DocsDev/releases/release-v1.2.3.md`, `DocsDev/releases/release-v1.2.3.json` e `release-assets/v1.2.3-card.png` documentam a release.

## Validacao

1. `codegraph status .`: OK durante a auditoria; o indice foi sincronizado depois da integracao do smoke test.
2. `git diff --check`: passou, apenas avisos LF/CRLF do Windows.
3. `python -m pytest`: 135 passed, 5 deselected.
4. `python -m pytest tests/test_http_frontend.py`: 5 passed na worktree do commit de smoke antes da integracao.
5. `cd frontend-ts && npm run build`: passou.
6. `cd frontend-ts && npm run test:logic`: 89 passed.

---

## Notas tecnicas

- Base: `v1.2.2` -> `v1.2.3`.
- Tag oficial: `v1.2.3`.
- Ultimo release publicado antes desta rodada: `v1.2.2` em 02/07/2026.
- Commits principais integrados: `d8b91f9`, `8c5b799`, `466165c`, `acae87d`, `eb6cd03`, `1bf27e2`, `72dd8bf` e `dc24e29`.
- Commit reprovado: `f87b1d1` (`Improve unauthenticated access gate`).
