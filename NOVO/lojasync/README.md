# LojaSync 1.1.0

Projeto principal ativo do LojaSync.

## Objetivo

Esta base substitui o runtime anterior como versao oficial do projeto, mantendo o comportamento funcional e reorganizando a engenharia em uma estrutura mais limpa.

## Estrutura

- `app/domain/`: regras de negocio
- `app/application/`: casos de uso e orquestracao
- `app/infrastructure/`: persistencia e integracoes
- `app/interfaces/`: API HTTP, websocket e frontend
- `app/bootstrap/`: composicao da aplicacao
- `docs/`: arquitetura e migracao
- `tests/`: testes automatizados

## Execucao

```bat
py launcher.py
```

## Observacao

O runtime anterior foi preservado na pasta `Legacy/` na raiz do repositório.
