# LojaSync

Release atual: v1.2.9

LojaSync e um app local para preparar produtos e automatizar cadastros de estoque no Byte Empresa. A interface permite cadastro e edicao em lote, importacao de romaneios por IA ou leitura local, consolidacao de grades e desfazer/refazer.

O produto esta funcional para uso local. Importacao por IA usa API Kimi direta (default) e/ou 9router na VM DigitalOcean; automacao depende de Windows, Byte Empresa aberto e ambiente calibrado. Login nao faz parte do fluxo normal.

## Atualizar outro PC (loja)

1. Checkout limpo do repositorio (sem mudancas locais).
2. Rodar `patchatt.bat` **ou** `git checkout main && git pull --ff-only origin main`.
3. Configurar envs de User no Windows (chaves **nao** vao no GitHub):
   - `LOJASYNC_LLM_PROVIDER=kimi`
   - `KIMI_API_KEY`, `KIMI_MODEL=kimi-for-coding-highspeed`, `KIMI_DISABLE_THINKING=1`
   - `NINE_ROUTER_BASE_URL=http://68.183.26.96:20128/v1`
   - `NINE_ROUTER_API_KEY` (key **LojaSync store PCs** no 9router da VM)
4. Iniciar com `Iniciar LojaSync.bat`. Confirmar `GET http://127.0.0.1:8800/health` com `"version":"1.2.9"`.

## Stack

- Python 3.11+, FastAPI, Pydantic e SQLite
- React 18, TypeScript e Vite
- PyAutoGUI e pywinauto no Windows
- Modulos legados para LLM e partes da automacao
