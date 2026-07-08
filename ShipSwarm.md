# ShipSwarm - LojaSync

## 2026-07-08 - Enxame Continuo Comercial

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
