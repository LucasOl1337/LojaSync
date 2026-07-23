# Tierlist — perfeição = soma **exata** dos itens da tabela

Critério: `sum(quantidade × preco) == total da tabela` (centavo a centavo).  
Qualquer delta ≠ 0 → **reprovado**.

## Notas do set (amostra multi-nota)

| Nota | Tipo | Total tabela (alvo) | Observação |
|---|---|---:|---|
| NF-e_664145 | PDF texto + XML | **17.629,82** (vProd) | Desconto 3.240 → vNF **14.389,82** |
| nota3.jpeg | foto folha 3 | **2.793,00** | soma manual VALOR TOTAL da página |
| NF-e_356525 / 329113 | PDF grandes | 28k / 25k | muitos timeouts (contexto) |

## Resultado duro

| Pergunta | Resposta |
|---|---|
| Algum modelo acertou **soma exata da tabela** em **todas** as notas? | **NÃO** |
| Algum acertou soma exata da tabela (vProd) na 664145? | **NÃO** (todos que rodaram deram **14.389,82**) |
| Alguém acertou **exato** a nota3 (2.793)? | **NÃO** (melhor: **2.786,50**, Δ −6,50) |
| Kimi API direta em perfeição multi-exemplo? | **NÃO** — só `highspeed` responde de forma estável; **não** fecha centavo |

## Caso especial: desconto (NF-e 664145)

Quem extraiu com sucesso (120 itens):

- soma = **14.389,82** = **vNF** (total da nota após desconto)
- **não** = **17.629,82** = soma SEFAZ das linhas (vProd)

Ou seja: **perfeitos no total da nota (vNF)**, **reprovados no total bruto dos produtos (tabela)**.

Se a regra de negócio for “bater o valor da nota (vNF)”, quase todos os que completaram a 664145 passam juntos.  
Se a regra for “bater a soma unitário×qtd como na tabela fiscal (vProd)”, **todos reprovam** (Δ = −3.240).

## Tierlist (uso prático LojaSync)

Ordenado por: (1) quantas vezes chegou perto de validar, (2) |Δ| em foto, (3) latência, (4) preferência Kimi.

### S — Perfeição multi-nota (soma tabela exata)
**Vazio.** Ninguém.

### A — Melhor fidelidade na foto + estável no PDF (ainda sem centavo perfeito na foto)
| Modelo | Por quê |
|---|---|
| **Gemini 3.1 flash-lite (9router)** | nota3 Δ **−6,5**; 664145 vNF exato; **~13–18 s** |
| **Claude Sonnet 4.6 (9router)** | nota3 Δ **−6,5**; 664145 vNF exato; ~40–70 s |

### B — Bom no PDF com desconto (vNF), fraco/médio na foto
| Modelo | Por quê |
|---|---|
| **GPT-5.6-terra / 5.4 / 5.5 (9router)** | 664145 vNF exato; nota3 Δ **−75 a −139** |
| **GPT-5.4-mini (9router)** | rápido no PDF; foto pior |
| **Kimi highspeed (API direta)** | **único Kimi utilizável**; 664145 vNF exato; nota3 Δ **−112** (50 itens, 2681) |

### C — Instável / incompleto
| Modelo | Por quê |
|---|---|
| Claude Opus (9router) | vNF ok na 664145; nota3 às vezes vazio |
| Kimi coding / k3 (direta) | timeout ou JSON vazio em vários casos |
| Kimi via 9router | timeout / content vazio frequente |

### F — Não usar para romaneio vision neste momento
Kimi k3 (timeout), Kimi 9router, GPT codex (sem vision), xAI no 9router (403).

## Preferência Kimi (API direta)

Pedido: preferir Kimi se houver perfeição em vários exemplos.

| Modelo Kimi | Verdict |
|---|---|
| **kimi-for-coding-highspeed** (API direta, thinking off) | **Melhor Kimi** — responde; **não** perfeito na tabela; no desconto bate **vNF** |
| kimi-for-coding (direta) | Instável / vazio |
| k3 (direta) | Timeout frequente |
| Kimi no 9router | Ruim para este fluxo |

**Conclusão Kimi:** dá para **preferir highspeed na API direta** como provider default de engenharia (chave, controle), mas **não** porque seja o mais perfeito nos totais. Nos testes, **Gemini flash-lite e Claude Sonnet** ficam mais perto da soma real da foto.

## Recomendação de uso no LojaSync

1. **Validação:** reprovar se `sum(itens) ≠ total` (sem tolerância “quase”).
2. **Definir qual total:** `vProd` (tabela) vs `vNF` (nota com desconto) — mudam o veredito da 664145.
3. **Stack sugerida com preferência Kimi:**
   - Default: **Kimi highspeed API direta** (operacional)
   - Se validação falhar: **1 retry** com **Gemini 3.1 flash-lite** ou **Claude Sonnet 4.6** via 9router
   - PDF digital: preferir texto embutido + validação; não depender só de vision
4. **Não** esperar perfeição multi-nota só com LLM 1-shot em foto/DANFE parcial.

## Dados brutos desta rodada (parcial, ~2 notas completas + timeouts em PDFs grandes)

Ver log/bench em `%TEMP%\lojasync_tierlist_exact\` quando finalizado; tabela acima consolida o que fechou com critério **exact**.
