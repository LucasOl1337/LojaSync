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
