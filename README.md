# LojaSync 1.1.0

Projeto principal ativo do LojaSync.

## Estrutura

- `app/`: aplicacao principal
- `data/`: dados operacionais do runtime principal
- `docs/`: arquitetura e migracao
- `tests/`: testes automatizados
- `Legacy/`: codigo e artefatos preservados do runtime anterior

## Execucao

```bat
py launcher.py
```

## Publicacao

O repositorio deve refletir exatamente o estado validado localmente, com a linha principal direto na raiz de `LojaSync` e o legado preservado em `Legacy/`.
