# docs index

Este diretorio guarda pontes e materiais publicos/externos do LojaSync. A fonte operacional canonica para manutencao continua em `../DocsDev/`.

## Onde comecar

- Manutencao, releases, arquitetura, validacoes e handoffs: `../DocsDev/INDEX.md`.
- Documentacao publica ou material de distribuicao: arquivos e subdiretorios neste `docs/`.
- Quando existir conteudo equivalente em `DocsDev/`, edite primeiro a versao canonica e mantenha este diretorio como ponte para evitar drift.

## Subdiretorios

- `architecture/`: pontes ou material publico de arquitetura.
- `distribution/`: material de distribuicao/publicacao.
- `loja-sync-divulgacao/`: material de divulgacao.
- `migration/`: pontes ou material externo de migracao visual.

## Validacao rapida

Para alteracoes somente de documentacao, rode:

```powershell
git diff --check
```
