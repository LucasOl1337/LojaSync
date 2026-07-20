![LojaSync v1.2.1](https://github.com/LucasOl1337/LojaSync/releases/download/v1.2.1/v1.2.1-card.png)

# v1.2.1 - Backward-compat aliases no launcher (22/06/2026)

LojaSync e uma plataforma desktop-web local para cadastro assistido de produtos no Byte Empresa, com painel React, API FastAPI, leitura de romaneios/NF-e, persistencia SQLite e automacao Windows. Esta release corrige compatibilidade do launcher para callers legados e patches de teste.

## Novidades

- Nao houve nova funcionalidade de produto nesta release.

## Melhorias

- Nao houve melhoria funcional alem do ajuste de compatibilidade descrito em correcoes.

## Correcoes

- **Aliases do launcher:** `launcher.py` agora expoe `_locate_npm_command`, `_make_http_server`, `_is_tcp_listening` e `_is_port_bindable` no escopo do modulo antes de `Launcher.run` executar quando o arquivo e chamado como script. Callers legados e patches de teste que referenciam esses nomes voltam a funcionar.

## Sistemas

- **Gate launcher/frontend:** `pytest tests/ -k "launcher or frontend"` validou 14 testes relacionados ao launcher e ao fluxo frontend.
- **Escopo do patch:** diff do release altera somente `launcher.py`, com 8 linhas adicionadas.

---

## Notas tecnicas

- Base: `v1.2.0` -> `v1.2.1`.
- Tag oficial: `v1.2.1`.
- Commit do release: `b61b10711935c24f851fa0f7a596d44760d0dc3d`.
- Validacao registrada no release original: `pytest tests/ -k 'launcher or frontend'`: 14/14 pass.
