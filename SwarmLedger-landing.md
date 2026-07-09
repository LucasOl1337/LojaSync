# Swarm Ledger - landing

## 2026-07-09T09:25Z - governor

- Branch: `swarm-gov/lojasync/landing`
- Entrega: `frontend-ts/public/oferta.html` ganhou um skip link acessivel por teclado para pular direto para a oferta; `frontend-ts/dist/oferta.html` foi atualizado pelo build.
- Validacao: `cd frontend-ts && npm run build` passou.
- Risco: baixo; alteracao limitada a acessibilidade da landing estatica, sem mudar copy, preco ou fluxo de CTA.

## 2026-07-09 - Governor executor

- Branch: `swarm-gov/lojasync/landing`
- Entrega: `frontend-ts/public/oferta.html` ganhou JSON-LD de `Offer` para expor nome, preco, moeda, disponibilidade limitada e aplicacao oferecida; `frontend-ts/dist/oferta.html` foi atualizado pelo build.
- Validacao: `node` parseou o JSON-LD embutido e `cd frontend-ts && npm run build` passou.
- Risco: baixo; altera metadados estruturados da oferta early access sem mudar layout ou fluxo de CTA.

## 2026-07-09 - Governor executor

- Branch: `swarm-gov/lojasync/landing`
- Entrega: metadados de compartilhamento da landing `frontend-ts/public/oferta.html` agora declaram dimensoes do hero, `twitter:image:alt` e preload/fetch priority da imagem principal; `frontend-ts/dist/` foi regenerado pelo build.
- Validacao: `cd frontend-ts && npm run build` passou.
- Risco: baixo; altera apenas HTML estatico publico da oferta early access.
