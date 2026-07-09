# Swarm Ledger - bugs

## 2026-07-09T06:31Z - executor

- Branch: `swarm-gov/lojasync/bugs`
- Mudanca: corrigido o CLI `tools/agent_run.py` para aceitar `--path` em acoes catalogadas com placeholders, evitando o erro em que a propria mensagem indicava uma opcao inexistente.
- Testes: `python -m pytest tests/test_agent_run_cli.py tests/test_agent_first_dry_run.py`
- Risco: baixo; alteracao limitada ao CLI agent-first e coberta por teste unitario de placeholder, override e rejeicao de path relativo.

## 2026-07-09T08:25Z - governor

- Branch: `swarm-gov/lojasync/bugs`
- Mudanca: corrigido o parser de quantidade de produtos para aceitar strings decimais simples como `"2.0"` e `"3,0"` sem zerar grades, cores ou payloads normalizados.
- Testes: `python -m pytest tests/test_product_entities.py tests/test_automation_product_payload.py`
- Risco: baixo; alteracao centralizada no parser de quantidade nao-negativa e mantendo valores invalidos/negativos como zero.

## 2026-07-09T06:15:04-03:00 - governor

- Assunto: bugs.
- Branch: `swarm-gov/lojasync/bugs`.
- Mudanca: `coerce_nonnegative_int` do payload de automacao agora reutiliza o parser de quantidade do dominio, preservando quantidades como `"2,0"` em grades antes do envio ao Byte Empresa.
- Validacao: `python -m pytest tests\test_automation_product_payload.py -q` => 6 passed.
- Risco: baixo; alteracao centraliza coercao ja usada por `Product.normalize` e mantem invalidos/negativos em zero.

## 2026-07-09T08:55:00-03:00 - governor

- Assunto: bugs.
- Branch: `swarm-gov/lojasync/bugs`.
- Mudanca: PATCH de produto agora ignora `null` em campos centrais obrigatorios antes de chamar o servico, evitando corrupcao com `"None"` ou erro em edicao parcial.
- Validacao: `python -m pytest tests\test_product_routes_sqlite.py -q` => 9 passed, 5 subtests passed.
- Risco: baixo; mantem `null` para campos opcionais e restringe a filtragem a campos centrais que nao devem ser limpos.
