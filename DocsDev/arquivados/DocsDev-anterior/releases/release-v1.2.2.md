![LojaSync v1.2.2](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.2/v1.2.2-card.png)

# v1.2.2 - Coleta pos-enxame e fixes operacionais (02/07/2026)

LojaSync e uma plataforma desktop-web local para cadastro assistido de produtos no Byte Empresa, com painel React, API FastAPI, leitura de romaneios/NF-e, persistencia SQLite e automacao Windows. Esta release integra apenas os commits aprovados do enxame e deixa fora a alteracao de auth/senha reprovada pelas regras locais de produto.

## Novidades

1. **CodeGraph operacional:** adicionados inventario, status, contexto, listagem e mapa visual em `DocsDev/codegraph/`, com instrucao local em `AGENTS.md` para orientar navegacao estrutural futura.

## Melhorias

1. **Busca por codigo:** a busca de produtos encontra codigos mesmo quando o operador omite ou troca separadores, cobrindo casos como `orig88`, `b300` e `090.840.002`.
2. **Totais do frontend:** quantidades invalidas, negativas ou fracionarias deixam de contaminar os totais correntes de custo e venda.
3. **Grades por LLM:** o parser atual e o parser legado aceitam JSON util quando a resposta vem embutida em texto explicativo.
4. **GradeBot:** tamanhos repetidos sao somados antes da montagem das tarefas de cadastro.
5. **Preco vindo de OCR:** valores com `r$` ou `RS` no inicio passam a ser aceitos pelo normalizador monetario.

## Correcoes

1. **Jobs em erro:** stages `error` agora recebem `completed_at`, mantendo status mensuravel sem criar resultado inexistente.
2. **Asset v1.2.1:** incluido o card/documentacao da release `v1.2.1` que ja estava em `main` desde o reparo posterior ao tag anterior.

## Sistemas

1. Versao atualizada para `1.2.2` em `pyproject.toml`, frontend, metadata FastAPI e `/health`.
2. Build estatico versionado aponta para `frontend-ts/dist/assets/index-B2jZET8s.js`.
3. Branch `swarm` foi resetada para o novo `main`; nao ha commits restantes fora do principal.

## Validacao

1. `python -m pytest`: 135 passed, 5 deselected.
2. `cd frontend-ts && npm run test:logic`: 89 passed.
3. `cd frontend-ts && npm run build`: passou.
4. `codegraph status .`: OK, 210 arquivos indexados.

---

## Notas tecnicas

- Base: `v1.2.1` -> `v1.2.2`.
- Tag oficial: `v1.2.2`.
- Commits integrados do enxame: `bc72898`, `aa03aa4`, `91d4ffa`, `bfe9368`, `f0369e1`, `76a09cb`.
- Commit reprovado: `1557ee0` (`fix(auth): rotate sessions on password change`).
