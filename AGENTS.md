## CodeGraph

Este repositorio tem indice CodeGraph local em `.codegraph/`. Proximos agentes devem consultar CodeGraph antes de usar buscas textuais para perguntas estruturais, fluxos, chamadas, definicoes de simbolos e impacto de mudancas.

- Comece por `codegraph_status` para confirmar saude do indice.
- Use `codegraph_files` para navegar a estrutura indexada.
- Use `codegraph_context` para entender uma area funcional.
- Use `codegraph_trace`, `codegraph_callers`, `codegraph_callees` e `codegraph_impact` para fluxos e dependencia entre simbolos.
- Use leitura direta apenas para detalhes que o CodeGraph nao cobrir ou para texto literal.
- Consulte primeiro `DocsDev/codegraph/inventory.md`.
- Abra `DocsDev/codegraph/codegraph-visual.html` no navegador para ver o mapa clicavel dos modulos e fluxos principais.
- Se a listagem do CodeGraph divergir dos arquivos reais, rode `codegraph index . --force` e depois `codegraph status .`.
