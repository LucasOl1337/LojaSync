LojaSync

Plataforma para cadastro e automação de produtos em ERP, com foco em fluxo de romaneio e nota fiscal, consolidação de grades e execução assistida por backend web com automação desktop.

Visão geral

O projeto reúne três pilares operacionais.
1. WebApp, que é o núcleo atual com FastAPI e frontend estático para gestão de produtos, importação de romaneio, extração de grades e orquestração de automações.
2. Engine modular legada desktop, com módulos Tkinter e automação PyAutoGUI que sustentam partes do domínio e da lógica operacional.
3. Bots e serviços auxiliares para execução remota e rotinas específicas, como o gradebot.

Arquitetura, mapa mental

LojaSync/
- engine/
  - webapp/ aplicação principal atual
    - backend.py API FastAPI para produtos, ações e automação
    - database.py store em memória com persistência JSONL e métricas
    - sequencias.py orquestra sequência de automação Byte Empresa (programa ERP de terceiros)
    - remote_manager.py WebSocket para agentes remotos
    - launcher.py sobe frontend, backend e serviços auxiliares
    - index.html e script.js frontend operacional
    - data/ bases locais de produtos, targets e métricas
  - modules/ módulos legados de core, interface e automation
  - LLM3/ microserviço FastAPI de chat e LLM, usando conexao com a nuvem ollama e modelo qwen 235b, funciona para extrair imagens, pdfs, textos de romaneios com produtos de forma automatica, usando o LLM para processar os dados de forma otimizada e ser capaz de lidar com diferentes formatos de romaneios ( sao muitos)
- automation/
  - gradebot/ bot local de preenchimento de grade via PyAutoGUI

Camadas funcionais

Camada de apresentação
- Frontend em engine/webapp/index.html e script.js.
- UI desktop legada em engine/modules/interface com Tkinter.

Camada de aplicação e API
- engine/webapp/backend.py concentra os contratos HTTP e WebSocket.

Camada de domínio e processamento
- Regras de produto, margens, consolidação e parsing de grades.

Camada de automação
- engine/webapp/sequencias.py com engine/modules/automation/byte_empresa.py.
- Automação específica de grades em automation/gradebot/gradebot.py.

Camada de dados local
- JSONL e JSON em engine/webapp/data e engine/data.

Competências do sistema

1. Cadastro e gestão de produtos
- HUD básico com campos de negócio, incluindo nome, código, preço, categoria, marca, grade e cor.
- Ações em lote para aplicar categoria e marca, juntar duplicados, formatar e restaurar códigos, reordenar e limpar lista.
- Métricas operacionais de volume e automação, como quantidade, custo, venda, tempo economizado e caracteres poupados.

2. Fluxo romaneio e nota fiscal
- Upload e processamento assíncrono de romaneio.
- Endpoint dedicado de importação com polling de status e resultado.
- Parser de grades em pipeline separado e assíncrono.

3. Automação de cadastro no ERP Byte Empresa
- Execução da sequência de telas com controle de início, status e cancelamento.
- Dependência de calibração de coordenadas em targets.json para clique e digitação assistida.

4. Operação distribuída com agentes remotos
- WebSocket de registro e heartbeat para agentes externos.
- Envio de comando com ack e result, com timeout controlado.
- Snapshot de agentes conectados e estado operacional.
(nao e mais usado, antes era usado para rodar o pyautogui em um pc diferente do que estava rodando o webapp, pois ele tambem podia funcionar como um servidor conectado por limewire)

5. Serviço LLM separado
- Serviço FastAPI dedicado em engine/LLM3 para chat e inferência.
- Pode ser executado de forma independente ou orquestrada pelo launcher.

Endpoints mais importantes do backend web

Saúde e catálogo
- GET /health
- GET /catalog/sizes

Produtos
- GET /products
- POST /products
- DELETE /products
- DELETE /products/{ordering_key}

Ações de negócio
- POST /actions/apply-category
- POST /actions/apply-brand
- POST /actions/join-duplicates
- POST /actions/format-codes
- POST /actions/restore-original-codes
- POST /actions/reorder
- POST /actions/apply-margin
- GET /actions/export-json

Romaneio e grades
- POST /actions/import-romaneio
- GET /actions/import-romaneio/status/{job_id}
- GET /actions/import-romaneio/result/{job_id}
- POST /actions/parser-grades
- GET /actions/parser-grades/status/{job_id}
- GET /actions/parser-grades/result/{job_id}

Automação
- GET /automation/targets
- POST /automation/targets
- POST /automation/targets/capture
- POST /automation/execute
- GET /automation/status
- POST /automation/cancel
- GET /automation/agents
- WS /automation/remote/ws

Como executar, modo recomendado

Requisito
- Python 3.10 ou superior.

1. Preparar ambiente
- cd engine/webapp
- python -m venv .venv
- Linux e macOS: source .venv/bin/activate
- Windows PowerShell: .venv\Scripts\Activate.ps1
- python -m pip install --upgrade pip
- python -m pip install -r requirements.txt
- para iniciar o app, usar python launcher.py

3. Acessar
- Frontend em http://127.0.0.1:5173
- Para ver feedback, status, e detalhe do LLM  http://127.0.0.1:5174
- API backend em http://127.0.0.1:8800
- FastAPI docs em http://127.0.0.1:8800/docs

Variáveis de ambiente úteis

- LOJASYNC_HOST
- LOJASYNC_FRONTEND_PORT
- LOJASYNC_BACKEND_PORT
- LOJASYNC_LLM_PORT
- LOJASYNC_LLM_MONITOR_PORT
- LOJASYNC_LLM_MONITOR_ENABLED
- LOJASYNC_LLM_HOST
- LOJASYNC_BROWSER_HOST
- REMOTE_AGENT_TOKEN
- LLM_BASE_URL, ou LLM_HOST e LLM_PORT

Essas variáveis permitem ajustar portas, host de exposição, integrações e autenticação de agente remoto.

Fluxo de uso sugerido para operação diária

1. Cadastrar base inicial manualmente, ou importar romaneio.
2. Aplicar ações em lote, como categoria, marca, junta de duplicados e margem.
3. Revisar totais e descrição e, se necessário, melhorar descrições.
4. Calibrar alvos de automação em /automation/targets na máquina de execução.
5. Disparar automação e acompanhar status em tempo real.
