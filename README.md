# LojaSync

Release atual: v1.2.8

LojaSync e um app local para preparar produtos e automatizar cadastros de estoque no Byte Empresa. A interface permite cadastro e edicao em lote, importacao de romaneios por IA ou leitura local, consolidacao de grades e desfazer/refazer.

O produto esta funcional para uso local. Importacao por IA depende do runtime LLM legado; automacao depende de Windows, Byte Empresa aberto e ambiente calibrado. Login nao faz parte do fluxo normal.

## Stack

- Python 3.11+, FastAPI, Pydantic e SQLite
- React 18, TypeScript e Vite
- PyAutoGUI e pywinauto no Windows
- Modulos legados para LLM e partes da automacao
