# Operacao

## App local

- Inicie com `Iniciar LojaSync.bat` ou `python launcher.py`.
- Verifique `GET http://127.0.0.1:8800/health`.
- Trate `data/lojasync.db` como dado do usuario.
- Escolha explicitamente importacao por IA ou leitura local; um modo nao e fallback automatico do outro.

## Provider modular (API + modelo)

O LojaSync escolhe o backend de IA por env:

| `LOJASYNC_LLM_PROVIDER` | Uso |
|---|---|
| `kimi` | API Kimi Code direta |
| `zai` | Z.AI / GLM |
| `9router` / `openai` / `openai_compat` | Gateway OpenAI-compatible **na nuvem** (GPT/Claude/Gemini) |
| `legacy` | LLM local `/api/chat` |

### Arquitetura LLM (PCs da loja) — LojaSync

O PC da loja roda o LojaSync **sozinho**. Ele **nao** depende do notebook do operador nem do 9router Windows local (`127.0.0.1:20128`).

| Caminho | Quando | Destino |
|---|---|---|
| **API direta (Kimi)** | default de importacao | `https://api.kimi.com/coding/v1` |
| **9router na VM (DigitalOcean)** | seletor A/B (Claude/GPT/Gemini etc.) | `http://68.183.26.96:20128/v1` |

Esse 9router e o da VM `sennin-core-01` (mesmo stack do Sennin/Maestro). Dashboard: `http://68.183.26.96:20128/dashboard`.
Alternativa HTTPS (tunnel Cloudflare da mesma VM): `https://chess-router.bombapvp.com/v1`.

**Nao** usar espelhos de terceiros (`aurora.simple-ai.cc`) — nao e o 9router de voces.

```powershell
# Default importacao: Kimi direto
[Environment]::SetEnvironmentVariable("LOJASYNC_LLM_PROVIDER", "kimi", "User")
[Environment]::SetEnvironmentVariable("KIMI_BASE_URL", "https://api.kimi.com/coding/v1", "User")
[Environment]::SetEnvironmentVariable("KIMI_MODEL", "kimi-for-coding-highspeed", "User")
[Environment]::SetEnvironmentVariable("KIMI_API_KEY", "<chave-kimi>", "User")
[Environment]::SetEnvironmentVariable("KIMI_DISABLE_THINKING", "1", "User")

# 9router da VM DigitalOcean (Claude/GPT/Gemini no seletor)
[Environment]::SetEnvironmentVariable("NINE_ROUTER_BASE_URL", "http://68.183.26.96:20128/v1", "User")
[Environment]::SetEnvironmentVariable("NINE_ROUTER_API_KEY", "<chave-lojasync-no-9router-da-vm>", "User")

# PROIBIDO no PC da loja (so o 9router do notebook do operador em dev):
# NINE_ROUTER_BASE_URL=http://127.0.0.1:20128/v1
# BOMBA_LAB_NINE_ROUTER_KEY  → key do 9router LOCAL, nao da VM
```

O seletor de modelo no menu de Importacao envia `llm_model` + `llm_provider` por job:
- ids `kimi-for-coding*` / `k3` → **API Kimi direta**
- ids `cx/*`, `cc/*`, `gemini/*`, `kimi/*` (prefixo 9router) → **9router da VM** (`NINE_ROUTER_BASE_URL`)

Benchmark de todos os modelos do gateway na foto de romaneio:

```powershell
python scripts/bench_9router_romaneio.py --workers 2
# so vision: python scripts/bench_9router_romaneio.py --vision-only
```

Relatorio: `docs/research/bench-9router-romaneio.md`.

## Importacao com Kimi K2.7 Code (highspeed)

O provider `kimi` usa a API OpenAI-compatible do Kimi Code. A chave deve ficar somente no ambiente do Windows, nunca em arquivo versionado:

```powershell
[Environment]::SetEnvironmentVariable("LOJASYNC_LLM_PROVIDER", "kimi", "User")
[Environment]::SetEnvironmentVariable("LLM_PROVIDER", "kimi", "User")
[Environment]::SetEnvironmentVariable("KIMI_BASE_URL", "https://api.kimi.com/coding/v1", "User")
[Environment]::SetEnvironmentVariable("KIMI_MODEL", "kimi-for-coding-highspeed", "User")
[Environment]::SetEnvironmentVariable("KIMI_API_KEY", "<chave-local>", "User")
[Environment]::SetEnvironmentVariable("KIMI_DISABLE_THINKING", "1", "User")
```

**Default operacional:** provider **`kimi`** (API direta), modelo **`kimi-for-coding-highspeed`**, thinking desligado na extracao (`KIMI_DISABLE_THINKING=1`). O alias `kimi-for-coding` so deve ser usado se highspeed falhar na conta.

Feche e reabra o launcher depois de alterar o ambiente.

- **TXT / CSV**: enviados como texto (chunks estruturados).
- **PDF com texto embutido util**: preferido como texto (`KIMI_PDF_PREFER_TEXT=1`, default); evita vision.
- **PDF escaneado / imagem**: rasterizacao local + vision (DPI 144, sem slice vertical por padrao).

Validacao de import continua **exata** (soma dos itens vs total da nota/tabela): qualquer diferenca reprova.

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
