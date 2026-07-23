# Operacao

## App local

- Inicie com `Iniciar LojaSync.bat` ou `python launcher.py`.
- Verifique `GET http://127.0.0.1:8800/health`.
- Trate `data/lojasync.db` como dado do usuario.
- Escolha explicitamente importacao por IA ou leitura local; um modo nao e fallback automatico do outro.

## Pipeline de importacao por evidencia (padrao)

A importacao por IA usa um pipeline **evidence-first** (`LOJASYNC_IMPORT_PIPELINE=evidence`, padrao):

1. Extrai evidencia deterministica do arquivo (texto/PDF local, ancoras de remessa e totais, linhas estruturadas).
2. Envia paginas inteiras ao modelo de visao (sem pre-fatiar por padrao).
3. Reconcilia itens com as ancoras; se incompleto, tenta recortes verticais com sobreposicao.
4. Publica resultado explicito: `approved` (status `ok`), `needs_review` (status `needs_review`; validacao `unverified` ou alerta de plausibilidade apos aprovacao) ou `rejected` (job em erro).

Metricas uteis no resultado do job: `import_pipeline`, `import_outcome`, `import_needs_review`, `evidence_*`, `completeness_*`, `llm_stage_item_counts`, `observability`.

Para reverter ao fluxo anterior (sem recovery por incompleto e com fatiamento antecipado), defina:

```powershell
[Environment]::SetEnvironmentVariable("LOJASYNC_IMPORT_PIPELINE", "legacy", "User")
```

Ajustes opcionais do recovery: `LOJASYNC_RECOVERY_PAGE_SLICES` (padrao 2+), `LOJASYNC_RECOVERY_SLICE_OVERLAP` (padrao 0.12).

## Importacao com Kimi K2.7 Code

O provider `kimi` usa a API OpenAI-compatible do Kimi Code. A chave deve ficar somente no ambiente do Windows, nunca em arquivo versionado:

```powershell
[Environment]::SetEnvironmentVariable("LOJASYNC_LLM_PROVIDER", "kimi", "User")
[Environment]::SetEnvironmentVariable("LLM_PROVIDER", "kimi", "User")
[Environment]::SetEnvironmentVariable("KIMI_BASE_URL", "https://api.kimi.com/coding/v1", "User")
[Environment]::SetEnvironmentVariable("KIMI_MODEL", "kimi-for-coding", "User")
[Environment]::SetEnvironmentVariable("KIMI_API_KEY", "<chave-local>", "User")
```

Feche e reabra o launcher depois de alterar o ambiente. PDFs sao rasterizados localmente e enviados como imagens de **pagina inteira** primeiro; TXT e outros arquivos textuais sao enviados como texto. O K2.7 Code mantem thinking ativo, por isso o LojaSync nao envia `temperature` nem tenta desabilitar thinking. Recortes verticais so entram no recovery quando a evidencia indica resultado incompleto (a menos que `KIMI_VISION_PAGE_SLICES` force pre-slice, ou o pipeline esteja em `legacy`).

Por padrao, uma importacao Kimi reprovada nao troca silenciosamente para o parser local. `KIMI_ALLOW_LOCAL_GUARD=true` reabilita esse comportamento de forma explicita.

Kimi Code usa a cota da assinatura voltada a ferramentas de programacao. Para integracao comercial/continuada em produto, a documentacao da Kimi recomenda uma chave da Kimi Platform.

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
