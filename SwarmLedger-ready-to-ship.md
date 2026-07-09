# SwarmLedger-ready-to-ship

## 2026-07-09 - Guarda de assets estaticos da release

- Branch: `swarm-gov/lojasync/ready-to-ship`.
- Mudanca: reforcado o smoke HTTP do frontend versionado para validar que o `index.html` real e seus assets referenciados tambem sao servidos pelo `StaticFiles` do app FastAPI.
- Arquivos tocados: `tests/test_http_frontend.py`.
- Validacao: `python -m pytest tests/test_http_frontend.py` passou com 5 testes.
- Risco: baixo; alteracao test-only, sem tocar runtime, auth, seed, deploy ou migracao remota.
