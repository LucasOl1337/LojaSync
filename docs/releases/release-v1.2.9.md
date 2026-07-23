# v1.2.9 — Importação IA (Kimi + 9router VM) e seletor de modelo

Data: 23/07/2026

LojaSync v1.2.9 consolida a importação por IA para PCs da loja: Kimi API direta como default, 9router oficial na VM DigitalOcean para Claude/GPT/Gemini, seletor de modelo na UI e feedback ao vivo das chamadas LLM.

## Mudanças percebidas

| Área | Trabalho | Como o usuário percebe |
| --- | --- | --- |
| Default IA | Kimi highspeed direto, thinking desligado | Importação mais rápida e estável sem depender do PC do operador |
| 9router | Endpoint canônico `http://68.183.26.96:20128/v1` (VM DO) | Modelos Claude/GPT/Gemini no seletor falam com a VM na nuvem |
| Seletor de modelo | Menu de importação com modelos Kimi e 9router | Escolha explícita por job (A/B sem mexer em env) |
| Feedback LLM | Log de chamadas no painel de progresso | Dá para ver provider, modelo e status da chamada em tempo real |
| Pipeline | Importação sempre passa pela LLM (sem pular com guard local) | Extração e grades no JSON do LojaSync; validação de soma exata |
| Histórico | UI de importação com exclusão permanente | Limpar jobs ruins sem lixo no histórico |
| Operação | Docs e defaults alinhados à loja | `patchatt.bat` puxa a main; envs de chave ficam só no Windows |

## Arquitetura LLM (loja)

- **Kimi direto** → `https://api.kimi.com/coding/v1` (default)
- **9router VM** → `http://68.183.26.96:20128/v1` (seletor Claude/GPT/Gemini)
- **Não** usar 9router local do notebook do operador (`127.0.0.1:20128`) nem espelho Aurora de terceiros

Chaves (`KIMI_API_KEY`, `NINE_ROUTER_API_KEY`) ficam no ambiente User do Windows de cada PC — nunca no repositório.

## Atualização no PC da loja

```bat
patchatt.bat
```

Ou: `git pull --ff-only origin main` em árvore limpa, depois reiniciar o app.

Base: `v1.2.8` → `v1.2.9`

Publicação: `main`, tag `v1.2.9` e GitHub Release.
