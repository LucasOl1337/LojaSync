# Indice

## Onde esta cada coisa

| Caminho | Conteudo |
| --- | --- |
| `app/` | Dominio, servicos, persistencia e APIs Python |
| `frontend-ts/src/` | Interface React e cliente HTTP |
| `frontend-ts/dist/` | Bundle versionado da interface |
| `tests/` e `frontend-ts/test/` | Testes Python e logica da interface |
| `Legacy/` | Compatibilidade ainda usada por partes do launcher e da automacao |
| `tools/` | CLI de agente, contratos HTTP e utilitarios |
| `data/` | Banco e estado local; nao trate como fixture |

## Quando ler

| Documento | Condicao |
| --- | --- |
| `README.md` | SOMENTE ao chegar sem contexto do produto ou da stack |
| `docs/desenvolvimento.md` | SOMENTE ao iniciar, validar ou alterar codigo |
| `docs/operacao.md` | SOMENTE ao operar a API, dados, importacao ou automacao |
| `docs/release.md` | SOMENTE ao preparar versao, bundle, tag ou distribuicao |
| `DocsDev/` | SOMENTE para consulta historica pontual; nao e fonte de verdade |
| `DocsDev/arquivados/` | NUNCA ler; e acervo fossil |
