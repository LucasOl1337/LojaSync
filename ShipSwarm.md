# ShipSwarm - LojaSync

## 2026-07-08 - Enxame Continuo Comercial

### Rodada: Performance perceptivel da primeira visita

- Agente: enxame-cont-nuo-lojasync
- Escopo reivindicado: `frontend-ts/src/AuthShell.tsx`, `frontend-ts/dist/index.html`, `frontend-ts/dist/assets/App-BaLGwEXP.js`, `frontend-ts/dist/assets/index-xhuoX2G4.js`
- Area comercial: Performance perceptivel da primeira visita

Antes:
- O shell inicial importava o `App.tsx` de forma estatica, entao o visitante carregava um bundle unico de aproximadamente 296 KB de JS antes mesmo de a sessao decidir entre loading, login, setup ou painel.
- A primeira visita carregava codigo operacional pesado do painel de produtos/importacao/automacao mesmo quando o usuario ainda estava no portao de acesso.

Depois:
- `AuthShell` passou a carregar o painel operacional com `React.lazy` e `Suspense`, mantendo o gate inicial separado do app pesado.
- O build passou a gerar um chunk inicial de aproximadamente 154 KB e um chunk do painel de aproximadamente 144 KB, carregado apenas quando o modo `app` e renderizado.
- O `frontend-ts/dist/` foi reconstruido com os novos assets versionados para distribuicao local.

Evidencia:
- `codegraph status .` retornou indice saudavel e atualizado para `C:\projetos\LojaSync`.
- `cd frontend-ts && npm run build` passou.
- Build antes observado: `dist/assets/index-B2jZET8s.js` com 295.889 bytes.
- Build depois observado: `dist/assets/index-xhuoX2G4.js` com 153.725 bytes e `dist/assets/App-BaLGwEXP.js` com 144.474 bytes.

Observacao para proximas rodadas:
- Evitar repetir code splitting do `AuthShell`. Bons proximos escopos disjuntos: QA comercial completo do fluxo visitante -> oferta -> contato, CTA com canal configuravel, analytics de conversao da pagina publica ou checklist final de venda controlada.

### Rodada: Oferta early access e pagina de preco controlado

- Agente: enxame-cont-nuo-lojasync
- Escopo reivindicado: `frontend-ts/public/oferta.html`, `frontend-ts/public/early-access-hero.png`, `frontend-ts/dist/oferta.html`, `frontend-ts/dist/early-access-hero.png`
- Area comercial: Pagina de preços, planos ou oferta early access

Antes:
- O material publico tinha promessa, SEO e kit de confianca, mas nao havia uma oferta concreta de piloto pago com preco sugerido, escopo de entrega, limites e proximo passo.
- O vendedor ainda precisava explicar oralmente quanto cobrar no primeiro teste, o que incluir e como transformar interesse em uma validacao real.

Depois:
- Foi criada uma pagina publica estatica em `/oferta.html` com oferta Early Access, investimento sugerido de R$ 497, CTA de validacao, inclusos do piloto, fluxo de venda e limites honestos.
- A pagina usa um asset bitmap proprio gerado para campanha, salvo em `frontend-ts/public/early-access-hero.png` e copiado pelo build para `frontend-ts/dist/early-access-hero.png`.
- O build versionado passou a incluir `frontend-ts/dist/oferta.html`, pronto para distribuicao local junto com o app.

Evidencia:
- Image Gen gerou o asset de campanha salvo a partir de `C:\Users\user\.codex\generated_images\019f42c8-c870-70a0-b857-104284f4a6fe\ig_04e302b503dc9a32016a4e89dadf2c8191a85df3244d40d8d7.png`.
- `cd frontend-ts && npm run build` passou.
- `git diff --check -- frontend-ts/public/oferta.html frontend-ts/dist/oferta.html` passou sem erros.

Observacao para proximas rodadas:
- Evitar repetir pagina de oferta/preco basico. Bons proximos escopos disjuntos: CTA real com canal configuravel, QA comercial do fluxo visitante -> oferta -> contato, checklist de venda controlada ou analytics de conversao da pagina publica.

### Rodada: SEO basico, meta tags e preview social

- Agente: enxame-cont-nuo-lojasync
- Escopo reivindicado: `frontend-ts/index.html`, `frontend-ts/public/site.webmanifest`, `frontend-ts/dist/index.html`, `frontend-ts/dist/site.webmanifest`
- Area comercial: SEO basico, meta tags e preview social

Antes:
- O shell publico tinha titulo generico `LojaSync` e nao declarava descricao, Open Graph, Twitter card, tema ou manifesto web.
- Ao compartilhar um link ou avaliar o app em uma vitrine publica, a primeira impressao dependia do navegador inferir tudo sozinho.

Depois:
- O HTML publico passou a declarar promessa clara para lojas que usam Byte Empresa, descricoes para busca e cards sociais, imagem de preview, locale e tema.
- O app ganhou `site.webmanifest` com nome, descricao, cores, escopo e icones existentes.
- O `frontend-ts/dist/` foi reconstruido com o mesmo contrato para distribuicao local versionada.

Evidencia:
- `codegraph status .` retornou indice saudavel e atualizado.
- `cd frontend-ts && npm run build` passou.

Observacao para proximas rodadas:
- Evitar repetir SEO/public preview basico. Bons proximos escopos disjuntos: FAQ/confianca, pagina de oferta/precos, checklist de venda controlada, QA comercial completo ou performance percebida da primeira visita.

### Rodada: Kit de confianca para venda controlada

- Agente: enxame-cont-nuo-lojasync
- Escopo reivindicado: `docs/loja-sync-divulgacao/kit-confianca-venda-controlada.md`
- Area comercial: Termos, privacidade, FAQ e confianca minima

Antes:
- O material comercial tinha pitch e ICP, mas nao havia um texto pronto para responder medo de dados, limites de automacao, funcionamento local, suporte e primeiro piloto pago.
- A venda dependia do vendedor explicar riscos e expectativas oralmente, com chance de prometer compatibilidade universal ou tratar senha/login como requisito.

Depois:
- Foi criado um kit de confianca com FAQ de venda, promessas seguras, termos resumidos, politica de privacidade resumida, checklist de piloto pago e scripts de WhatsApp.
- O documento orienta primeiro teste controlado com lote pequeno, revisao humana antes da automacao e dados operacionais locais.
- O texto preserva a decisao de produto de nao vender senha/login como fluxo principal.

Evidencia:
- `rg "FAQ de venda|Politica de privacidade resumida|Checklist para fechar primeiro piloto pago|Preciso criar senha" docs/loja-sync-divulgacao/kit-confianca-venda-controlada.md` encontrou as secoes esperadas.
- `git diff --check -- docs/loja-sync-divulgacao/kit-confianca-venda-controlada.md ShipSwarm.md` passou sem erros.

Observacao para proximas rodadas:
- Evitar repetir kit de FAQ/confianca. Bons proximos escopos disjuntos: pagina de oferta/precos, QA comercial completo, performance percebida da primeira visita, checklist final de venda controlada ou implementacao concreta de paywall/plano quando o modelo comercial estiver definido.
