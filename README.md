# LojaSync

Plataforma para cadastro e automação de produtos em ERP, com foco em fluxo de romaneio e nota fiscal, consolidação de grades e execução assistida por backend web com automação desktop.

---

## Visão Geral

O LojaSync é um sistema desktop-web projetado para **lojistas** que precisam cadastrar grandes volumes de produtos em sistemas ERP (Byte Empresa). Ele combina um painel web moderno com automação desktop para eliminar trabalho manual repetitivo.

### O que o sistema faz

- **Importação automática de romaneios** — Upload de PDF, imagem ou texto de nota fiscal. Um serviço LLM processa o documento e extrai os produtos com código, descrição, quantidade e preço.
- **Gestão de produtos em lote** — Interface web para revisar, editar, aplicar categoria, marca, margem, formatar códigos, criar conjuntos e juntar duplicados antes de enviar ao ERP.
- **Extração de grades** — Pipeline assíncrono que detecta tamanhos (PP, P, M, G, GG...) a partir da nota fiscal e aplica aos produtos cadastrados.
- **Automação de cadastro no ERP** — Sequência automatizada via PyAutoGUI que preenche as telas do Byte Empresa, campo por campo, produto por produto.
- **GradeBot** — Bot dedicado para preenchimento automatizado da tela de grade do ERP, com calibração de coordenadas e velocidade ajustável.
- **Métricas operacionais** — Rastreamento de tempo economizado, caracteres poupados e volume acumulado.

---

## Arquitetura

O projeto segue **Clean Architecture** com separação em camadas:

```
lojasync/
├── launcher.py                          # Entrypoint — sobe frontend, backend e serviços
├── app/
│   ├── domain/                          # Regras de negócio puras (sem framework)
│   │   ├── products/                    #   Entidades, repositório abstrato, pricing
│   │   ├── brands/                      #   Repositório abstrato de marcas
│   │   ├── grades/                      #   Parser de extração de grades
│   │   └── metrics/                     #   Entidade de métricas operacionais
│   │
│   ├── application/                     # Casos de uso e orquestração
│   │   ├── products/service.py          #   CRUD, lote, margens, códigos, conjuntos
│   │   └── automation/service.py        #   Automação local, GradeBot, targets
│   │
│   ├── infrastructure/                  # Adaptadores de I/O
│   │   └── persistence/
│   │       ├── jsonl/stores.py          #   Repositório de produtos em JSONL
│   │       └── files/settings_files.py  #   Marcas, margem e métricas em JSON
│   │
│   ├── interfaces/                      # Camada de apresentação
│   │   ├── api/
│   │   │   ├── http/app.py              #   Factory do FastAPI
│   │   │   ├── http/routes.py           #   Endpoints REST e WebSocket
│   │   │   └── schemas/products.py      #   Schemas Pydantic de request/response
│   │   └── webapp/static/               #   Frontend (HTML + CSS + JS)
│   │
│   ├── bootstrap/wiring/container.py    # Composição e injeção de dependência
│   └── shared/                          # Utilitários transversais
│       ├── config/settings.py           #   Configurações da aplicação
│       ├── paths/runtime_paths.py       #   Caminhos de runtime
│       └── logging/setup.py             #   Configuração de logging
│
├── data/                                # Dados locais (JSONL, targets, romaneios)
├── docs/                                # Documentação arquitetural e de migração
└── tests/                               # Testes unitários, integração e funcionais
```

### Dependências externas

| Componente | Papel |
|---|---|
| **Byte Empresa** | ERP de terceiros onde os produtos são cadastrados |
| **LLM3** | Microserviço FastAPI separado para processamento de documentos via LLM (Qwen 2.5B via Ollama) |
| **LLM Monitor** | Interface web para acompanhar requisições ao serviço LLM |

---

## Camadas Funcionais

### Domain

Regras de negócio puras, sem dependência de FastAPI, PyAutoGUI ou I/O. Contém:
- `Product` com normalização, pricing e serialização
- Cálculo de preço final por margem (arredondamento `.90`)
- Parser de grades com suporte a JSON, dict, lista e texto livre
- Repositórios abstratos (`ProductRepository`, `BrandRepository`)

### Application

Orquestra os casos de uso:
- **ProductService** — CRUD, ações em lote, consolidação, formatação de códigos, criação de conjuntos
- **AutomationService** — Execução do fluxo Byte Empresa, GradeBot, gestão de targets e coordenadas

### Infrastructure

Implementações concretas de persistência:
- **JSONL** para produtos ativos e histórico
- **JSON** para marcas, margem e métricas

### Interfaces

- **API REST** via FastAPI com schemas Pydantic
- **WebSocket** para eventos de UI em tempo real
- **Frontend** estático com formulário de cadastro, tabela de produtos, ferramentas de lista e controles de automação

---

## Endpoints da API

### Produtos

| Método | Rota | Descrição |
|:---:|---|---|
| `GET` | `/products` | Lista produtos ativos |
| `POST` | `/products` | Cria produto |
| `PATCH` | `/products/{ordering_key}` | Atualiza produto |
| `DELETE` | `/products/{ordering_key}` | Remove produto |
| `DELETE` | `/products` | Limpa lista |

### Ações em Lote

| Método | Rota | Descrição |
|:---:|---|---|
| `POST` | `/actions/apply-category` | Aplica categoria a todos |
| `POST` | `/actions/apply-brand` | Aplica marca a todos |
| `POST` | `/actions/apply-margin` | Aplica margem de preço |
| `POST` | `/actions/join-duplicates` | Junta produtos duplicados |
| `POST` | `/actions/join-grades` | Consolida grades |
| `POST` | `/actions/format-codes` | Formata códigos |
| `POST` | `/actions/restore-original-codes` | Restaura códigos originais |
| `POST` | `/actions/create-set` | Cria conjunto de produtos |
| `POST` | `/actions/improve-descriptions` | Limpa descrições |
| `POST` | `/actions/reorder` | Reordena lista |
| `POST` | `/actions/restore-snapshot` | Restaura snapshot |
| `GET` | `/actions/export-json` | Exporta JSONL |

### Romaneio e Grades

| Método | Rota | Descrição |
|:---:|---|---|
| `POST` | `/actions/import-romaneio` | Inicia importação de romaneio (assíncrono) |
| `GET` | `/actions/import-romaneio/status/{job_id}` | Status da importação |
| `GET` | `/actions/import-romaneio/result/{job_id}` | Resultado da importação |
| `POST` | `/actions/parser-grades` | Inicia extração de grades (assíncrono) |
| `GET` | `/actions/parser-grades/status/{job_id}` | Status da extração |
| `GET` | `/actions/parser-grades/result/{job_id}` | Resultado da extração |

### Automação e GradeBot

| Método | Rota | Descrição |
|:---:|---|---|
| `POST` | `/automation/execute` | Dispara automação de cadastro |
| `GET` | `/automation/status` | Status da automação |
| `POST` | `/automation/cancel` | Cancela automação |
| `GET` | `/automation/targets` | Coordenadas de calibração |
| `POST` | `/automation/targets` | Salva coordenadas |
| `POST` | `/automation/targets/capture` | Captura posição do mouse |
| `GET` | `/automation/agents` | Lista agentes conectados |
| `POST` | `/automation/grades/run` | Executa GradeBot |
| `POST` | `/automation/grades/batch` | GradeBot em lote |
| `POST` | `/automation/grades/stop` | Para GradeBot |
| `GET` | `/automation/grades/config` | Configuração do GradeBot |
| `POST` | `/automation/grades/config` | Salva configuração do GradeBot |

### Outros

| Método | Rota | Descrição |
|:---:|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/catalog/sizes` | Catálogo de tamanhos |
| `GET` | `/brands` | Lista marcas |
| `POST` | `/brands` | Adiciona marca |
| `GET` | `/settings/margin` | Margem atual |
| `POST` | `/settings/margin` | Altera margem |
| `GET` | `/totals` | Totais e métricas |
| `WS` | `/ws/ui` | WebSocket de eventos de UI |

---

## Como Executar

### Requisitos

- Python 3.11 ou superior
- Windows (automação desktop depende de PyAutoGUI e Win32)

### Instalação

```powershell
cd lojasync
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Iniciar

```powershell
python launcher.py
```

**Opções do launcher:**

```
--host              Host dos servidores (padrão: 127.0.0.1)
--frontend-port     Porta do frontend (padrão: 5173)
--backend-port      Porta do backend (padrão: 8800)
--llm-port          Porta do serviço LLM (padrão: 8002)
--no-browser        Não abrir navegador automaticamente
--disable-llm-monitor   Desabilitar monitor do LLM
```

### Acessar

| Serviço | URL |
|---|---|
| Frontend | http://127.0.0.1:5173 |
| API Backend | http://127.0.0.1:8800 |
| API Docs (Swagger) | http://127.0.0.1:8800/docs |
| LLM Monitor | http://127.0.0.1:5174 |

---

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `LOJASYNC_HOST` | Host de bind dos servidores | `127.0.0.1` |
| `LOJASYNC_FRONTEND_PORT` | Porta do frontend | `5173` |
| `LOJASYNC_BACKEND_PORT` | Porta do backend | `8800` |
| `LOJASYNC_LLM_PORT` | Porta do serviço LLM | `8002` |
| `LOJASYNC_LLM_HOST` | Host do serviço LLM | mesmo do host |
| `LOJASYNC_LLM_MONITOR_PORT` | Porta do monitor LLM | `5174` |
| `LOJASYNC_LLM_MONITOR_ENABLED` | Habilitar monitor LLM | `true` |
| `LOJASYNC_BROWSER_HOST` | Host para abrir no navegador | `127.0.0.1` |
| `LLM_BASE_URL` | URL base do serviço LLM | auto |
| `LLM_HTTP_TIMEOUT_SECONDS` | Timeout para requisições LLM | `900` |

---

## Fluxo de Uso

```
1. Importar romaneio (PDF/imagem) ou cadastrar produtos manualmente
                        ↓
2. Revisar lista de produtos na interface web
                        ↓
3. Aplicar ações em lote:
   • Categoria e marca
   • Juntar duplicados
   • Formatar códigos
   • Definir margem de preço
   • Extrair e aplicar grades (via nota fiscal)
                        ↓
4. Calibrar coordenadas de automação (targets)
                        ↓
5. Executar cadastro em massa no Byte Empresa
                        ↓
6. Acompanhar progresso e métricas em tempo real
```

---

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI, Uvicorn, Pydantic |
| Frontend | HTML5, CSS3 (Space Grotesk), JavaScript vanilla |
| Automação | PyAutoGUI, keyboard, pygetwindow |
| PDF | PyPDF2, pdfplumber, PyMuPDF |
| LLM | Ollama + Qwen 2.5B (serviço externo) |
| Dados | JSONL / JSON em disco local |
| Runtime | Python 3.11+, Windows |

---

## Licença

Projeto privado. Uso interno.
