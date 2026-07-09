# SwarmLedger-ready-to-ship

## 2026-07-09 - Guarda de assets estaticos da release

- Branch: `swarm-gov/lojasync/ready-to-ship`.
- Mudanca: reforcado o smoke HTTP do frontend versionado para validar que o `index.html` real e seus assets referenciados tambem sao servidos pelo `StaticFiles` do app FastAPI.
- Arquivos tocados: `tests/test_http_frontend.py`.
- Validacao: `python -m pytest tests/test_http_frontend.py` passou com 5 testes.
- Risco: baixo; alteracao test-only, sem tocar runtime, auth, seed, deploy ou migracao remota.

## 2026-07-09 - Build TS reage a assets publicos

- Branch: `swarm-gov/lojasync/ready-to-ship`.
- Mudanca: incluido `frontend-ts/public` nos inputs que o launcher usa para decidir se `frontend-ts/dist` precisa ser reconstruido, evitando release local com paginas ou assets publicos desatualizados.
- Arquivos tocados: `app/bootstrap/launcher/env.py`, `tests/test_launcher.py`.
- Validacao: `python -m pytest tests/test_launcher.py` passou com 10 testes.
- Risco: baixo; mudanca restrita ao gate de build local do launcher, sem deploy, seed, migracao remota ou auth.

## 2026-07-09 - agent_run sem stack trace quando API esta offline

- Branch: `swarm-gov/lojasync/ready-to-ship`.
- Mudanca: `tools/agent_run.py` agora captura `URLError` e retorna payload JSON com `http=0`, mantendo `health` e `run` com saida operacional controlada quando o backend local nao esta ouvindo.
- Validacao: `python -m pytest tests/test_agent_run_cli.py` passou; `python tools\agent_run.py --base http://127.0.0.1:9 health` retornou exit code `1` esperado, com payload JSON e sem stack trace.
- Risco: baixo; caminho HTTP 4xx/5xx continua usando `HTTPError` e respostas 2xx permanecem inalteradas.
