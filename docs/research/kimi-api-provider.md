# API oficial Kimi/Moonshot para o LojaSync

Pesquisa em fontes oficiais, verificada em 22/07/2026. Nenhuma chave local foi lida.

## Duas plataformas e dois tipos de chave

A Kimi mantem duas APIs cujas chaves nao sao intercambiaveis:

- **Kimi Code**, incluido na assinatura e voltado a ferramentas de programacao: base OpenAI-compatible `https://api.kimi.com/coding/v1`, modelo K2.7 Code `kimi-for-coding` (ou `kimi-for-coding-highspeed`).
- **Kimi Platform**, pay-as-you-go e indicada para integracao em produtos: base internacional `https://api.moonshot.ai/v1`, com IDs como `kimi-k2.7-code` quando liberados para a conta.

A chave fornecida para esta adaptacao pertence ao Kimi Code e foi validada somente no primeiro endpoint. A documentacao oficial alerta que usar beneficios do Kimi Code fora das ferramentas/cenarios autorizados pode restringir a conta; para distribuicao do LojaSync, prefira uma chave da Kimi Platform.

Fontes: [Kimi Code Overview](https://www.kimi.com/code/docs/en/), [Kimi Code Model Configuration](https://www.kimi.com/code/docs/en/kimi-code/models.html), [Kimi Code Error Reference](https://www.kimi.com/code/docs/en/kimi-code/error-reference.html).

## Contrato da Kimi Platform

- Base URL internacional: `https://api.moonshot.ai/v1`.
- Chat Completions: `POST https://api.moonshot.ai/v1/chat/completions`.
- Autenticação: `Authorization: Bearer <MOONSHOT_API_KEY>`; é uma chave secreta de servidor gerada no painel da plataforma.
- A API é compatível com o formato/SDK da OpenAI. A própria Moonshot instancia `OpenAI(api_key=..., base_url="https://api.moonshot.ai/v1")`.
- Convém validar a disponibilidade real para a conta com `GET /v1/models`: a Moonshot informa que modelos e capacidades podem mudar e que um 404 pode indicar modelo inexistente ou não liberado para aquela conta. A documentação também alerta que chaves de plataformas Kimi diferentes não são intercambiáveis.

Fontes: [Create Chat Completion](https://platform.kimi.ai/docs/api/chat), [List Models](https://platform.kimi.ai/docs/api/list-models), [Kimi K2.7 Code](https://platform.kimi.ai/docs/guide/kimi-k2-7-code-quickstart).

## Existe “Kimi 2.7”?

Sim, mas o nome oficial é **Kimi K2.7 Code**, modelo dedicado a programação. Os IDs aceitos documentados são:

- `kimi-k2.7-code`
- `kimi-k2.7-code-highspeed` — o mesmo modelo, servido em maior velocidade.

Não há um ID oficial `kimi-2.7`, `kimi-k2.7` ou um K2.7 geral. Na Kimi Platform usa-se `kimi-k2.7-code`; na Kimi Code, o alias equivalente é `kimi-for-coding`.

Há uma ressalva importante para a integração: K2.7 Code mantém thinking ativo, usa `temperature=1.0`, `top_p=0.95`, `n=1` e penalties `0`; outros valores geram erro. Portanto o LojaSync não deve mandar `temperature: 0` nem tentar desabilitar thinking. O modelo suporta 256K tokens de contexto.

Para extração geral de documentos/notas, a documentação oficial atualmente usa por padrão o modelo mais recente `kimi-k3` no fluxo de Q&A de arquivos e o descreve como seu modelo flagship mais capaz. Se o objetivo não for estritamente “2.7”, `kimi-k3` é a recomendação mais alinhada ao caso de uso documental; `kimi-k2.6` também é explicitamente descrito como general-purpose e aceita modos thinking/non-thinking. A escolha final deve ser confirmada com `GET /v1/models` usando a conta do proprietário.

Fontes: [lista oficial de modelos](https://platform.kimi.ai/docs/models), [parâmetros por modelo](https://platform.kimi.ai/docs/api/models-overview), [Kimi K3](https://platform.kimi.ai/docs/guide/kimi-k3-quickstart), [Kimi K2.6](https://platform.kimi.ai/docs/guide/kimi-k2-6-quickstart).

## Imagens e PDF

K2.7 Code suporta visão. Em Chat Completions, imagens entram em `messages[].content` como array contendo uma parte `text` e uma parte `image_url`. A imagem pode ser base64 (`data:image/...;base64,...`) ou referência de arquivo `ms://<file_id>`. Os formatos documentados são PNG, JPEG, WebP e GIF. URLs remotas comuns não são suportadas nesse fluxo; a documentação pede base64 ou upload.

PDF não aparece como tipo multimodal direto de Chat Completions — os tipos documentados ali são texto, imagem e vídeo. O fluxo oficial para PDF é separado:

1. `POST /v1/files` com `purpose="file-extract"`;
2. obter o conteúdo extraído do arquivo (há OCR para PDF/imagem);
3. incluir esse texto extraído nas mensagens enviadas a `/v1/chat/completions`.

Assim, para o LojaSync há duas opções oficiais: usar `file-extract` para o PDF e enviar o texto resultante; ou, se o app já rasteriza páginas, enviar cada página como `image_url` base64 ao modelo visual. A conclusão de que PDF não é aceito diretamente como uma parte de Chat Completions é uma inferência do conjunto de tipos documentado e do fluxo oficial específico para arquivos.

Fontes: [Vision Input](https://platform.kimi.ai/docs/guide/use-kimi-vision-model), [File-Based Q&A](https://platform.kimi.ai/docs/guide/use-kimi-api-for-file-based-qa), [Files API](https://platform.kimi.ai/docs/api/files).

## Recomendação prática

Para a chave Kimi Code validada nesta adaptacao: `base_url=https://api.kimi.com/coding/v1`, Bearer token vindo de variável de ambiente local, modelo `kimi-for-coding`, imagens em partes `image_url`, e sem sobrescrever os parâmetros fixos do modelo. Antes da primeira importação real, testar uma única nota representativa.

Para maior aderência semântica à extração de notas fiscais: comparar a mesma nota com `kimi-k3`, pois é o modelo que a Moonshot recomenda implicitamente ao torná-lo padrão no guia atual de documentos, enquanto K2.7 é dedicado a código.
