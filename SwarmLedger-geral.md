# Swarm Ledger - geral

## 2026-07-09 06:09 - governor

- Branch: `swarm-gov/lojasync/geral`
- Entrega: `tools/agent_run.py` agora trata JSON invalido em `--body` como erro de uso do CLI, sem traceback e sem disparar requisicao HTTP.
- Validacao: `python -m pytest tests\test_agent_run_cli.py -q`.
- Resultado: 3 testes passaram.
- Risco: baixo; mudanca restrita ao tratamento de entrada invalida no CLI Agent-First.

## 2026-07-09 01:33 - executor

- Branch: `swarm-gov/lojasync/geral`
- Entrega: `tools/agent_run.py` agora aceita `--path` no comando `run`, permitindo executar acoes catalogadas com placeholders usando caminho concreto.
- Validacao: `python -m pytest tests/test_agent_run_cli.py tests/test_agent_first_dry_run.py`
- Resultado: 4 testes passaram.
- Risco: baixo; mudanca limitada ao CLI Agent-First e coberta por teste unitario.

## 2026-07-09 05:20 - governor

- Branch: `swarm-gov/lojasync/geral`
- Entrega: `launcher.py` agora expoe `--llm-monitor-port`, alinhando a CLI com a configuracao interna do monitor LLM.
- Validacao: `python -m py_compile C:\Projetos\LojaSync-swarm-governor\launcher.py`; `python -m pytest C:\Projetos\LojaSync-swarm-governor\tests\test_launcher.py -q`.
- Resultado: 9 testes passaram.
- Risco: baixo; mudanca limitada ao parser de argumentos e repasse para `Launcher`.
