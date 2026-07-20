Este checkout e o app local LojaSync para cadastro de estoque no Byte Empresa. Ele usa dados SQLite locais; push na `main` atualiza a origem consumida por outros PCs via `patchatt.bat`.

- So faca commit, push, tag ou release com ordem explicita do dono.
- Nunca use `git clean`, `git reset --hard`, `git checkout --`, `git restore` ou `git stash` nesta arvore compartilhada.
- Nunca exponha a API local por tunel nem execute automacao desktop sem confirmacao humana explicita.
- Preserve `data/lojasync.db`, arquivos de runtime e mudancas locais de terceiros.
- Consulte INDEX.md para onde esta cada coisa e quando ler cada documento.
