# Swarm Ledger - bugs

## 2026-07-09T06:31Z - executor

- Branch: `swarm-gov/lojasync/bugs`
- Mudanca: corrigido o CLI `tools/agent_run.py` para aceitar `--path` em acoes catalogadas com placeholders, evitando o erro em que a propria mensagem indicava uma opcao inexistente.
- Testes: `python -m pytest tests/test_agent_run_cli.py tests/test_agent_first_dry_run.py`
- Risco: baixo; alteracao limitada ao CLI agent-first e coberta por teste unitario de placeholder, override e rejeicao de path relativo.
