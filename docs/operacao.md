# Operacao

## App local

- Inicie com `Iniciar LojaSync.bat` ou `python launcher.py`.
- Verifique `GET http://127.0.0.1:8800/health`.
- Trate `data/lojasync.db` como dado do usuario.
- Escolha explicitamente importacao por IA ou leitura local; um modo nao e fallback automatico do outro.

## API para agentes

Catalogo: `tools/agent/actions-index.json`

OpenAPI: `tools/agent/openapi.json`

```powershell
python tools/agent_run.py list
python tools/agent_run.py health
python tools/agent_run.py run products.list
python tools/agent_run.py run actions.join_duplicates --dry-run
python tools/export_openapi.py
```

Para mutacao com suporte a `dry_run`, simule primeiro e revise o resultado. Depois da execucao real, confira `products.list` ou `totals.get`. As operacoes em lote catalogadas gravam snapshot de undo; use `history.undo` se a verificacao falhar.

## Automacao desktop

Antes de qualquer `/automation/execute*` ou execucao de grades:

1. Obtenha confirmacao humana.
2. Confira `automation.status`.
3. Confirme Windows interativo, Byte Empresa aberto e configuracao calibrada.
4. Nao execute se o runtime nao estiver ocioso e pronto.

A CLI bloqueia a execucao real das acoes catalogadas com `needs_human`; a confirmacao deve ocorrer fora dela.

## Acesso remoto

`Iniciar LojaSync Online.bat` publica a porta local por um tunel Cloudflare. Use SOMENTE com ordem explicita e encerre o tunel ao terminar.
