# LojaSync v1.2.2 - Patch Notes

Data: 2026-07-02

Esta release fecha a coleta pos-enxame com correcoes pequenas e auditadas em busca, totais, jobs, parser de grades, automacao e normalizacao monetaria. Tambem atualiza a versao exposta pelo backend/frontend e registra a documentacao de release.

## Destaques

- Busca de produtos mais tolerante a codigos digitados sem separadores ou com separadores diferentes.
- Totais atuais do frontend ignoram quantidades invalidas, negativas ou fracionarias para manter custo/venda finitos.
- Jobs em erro agora registram horario de conclusao, facilitando polling e diagnostico.
- Parser de grades atual e legado aceitam JSON embutido em texto retornado por LLM.
- GradeBot soma tamanhos repetidos antes de montar tarefas de cadastro.
- Normalizador de preco aceita marcadores OCR `r$` e `RS` no inicio do valor.

## Correcoes

- `frontend-ts/src/productFilters.ts`: compacta campos de busca e termos digitados para encontrar codigos como `090840002`, `090.840.002` e `orig88`.
- `frontend-ts/src/productPricing.ts`: passa a aceitar apenas quantidades inteiras seguras e nao negativas nos totais correntes.
- `app/shared/jobs/in_memory.py`: marca jobs em stage `error` com `completed_at` sem criar resultado falso.
- `app/domain/grades/parser.py` e `Legacy/engine/modules/parsers/parser_grades.py`: usam `JSONDecoder.raw_decode` para encontrar o primeiro payload JSON util dentro do texto.
- `app/application/automation/product_payload.py`: agrega quantidades quando o mesmo tamanho aparece mais de uma vez.
- `app/domain/products/money.py`: remove `R$`, `r$` ou `RS` como marcador inicial de moeda antes de normalizar o decimal.

## Sistemas e documentacao

- Versao atualizada para `1.2.2` em `pyproject.toml`, `frontend-ts/package.json`, `frontend-ts/package-lock.json`, metadata FastAPI e `/health`.
- `README.md` atualizado para apontar a release atual `v1.2.2`.
- Adicionados materiais CodeGraph em `DocsDev/codegraph/` e instrucoes locais em `AGENTS.md` para orientar futuros agentes.
- Incluido reparo de asset/documentacao da release `v1.2.1` em `DocsDev/releases/` e `release-assets/`.

## Validacao da release

- `python -m pytest`: 135 passed, 5 deselected.
- `cd frontend-ts && npm run test:logic`: 89 passed.
- `cd frontend-ts && npm run build`: passou; bundle `frontend-ts/dist/assets/index-B2jZET8s.js`.
- `codegraph status .`: OK, indice atualizado com 210 arquivos.

## Riscos conhecidos

- A automacao desktop continua dependente de Windows, posicoes de tela e disponibilidade do Byte Empresa.
- O fallback por LLM depende do servico configurado em `LLM_BASE_URL`/`LLM_HOST`/`LLM_PORT`.
- O fluxo de auth/senha segue tratado como infraestrutura opcional/legada, nao como melhoria ativa do produto principal.
