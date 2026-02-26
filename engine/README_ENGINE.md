# LojaSync Engine Overview

## Objetivo
- **[Descrição]** Ambiente completo de desenvolvimento/execução do WebApp LojaSync.
- **[Componentes principais]** Código fonte FastAPI `webapp/`, utilitários (`tools/`, `scripts/`), dependências e assets necessários.

## Estrutura
- **`webapp/`** Backend FastAPI, frontend Vite, launchers e automações.
- **`webapp/LLM/`** Serviço FastAPI que orquestra reparo automático de PDFs (via `pypdf`) e integra com Ollama.
- **`webapp/tools/`** Utilitários como `pdf_repair_gui.py` (GUI) e `repdf.py` (CLI/GUI leve).
- **`webapp/data/`** Recursos estáticos e fixtures usados pelo frontend/automação.
- **`webapp/launcher.py`** Sobe frontend, backend e LLM simultaneamente.

## Dependências
- **[Python]** Versão 3.10+ recomendada.
- **[Pacotes]** `pip install -r webapp/requirements.txt` (ver arquivo para lista completa).
- **[PyPDF]** `pip install pypdf` obrigatório para reparo automático.
- **[qpdf (opcional)]** Instalar via `conda install -c conda-forge qpdf` ou `choco install qpdf` se desejar o modo rápido na GUI.

## Execução (Desenvolvimento)
- **[Passo 1]** Criar/ativar ambiente virtual.
- **[Passo 2]** Instalar dependências: `python -m pip install -r webapp/requirements.txt`.
- **[Passo 3]** Rodar launcher: `python webapp/launcher.py`.
  - Frontend: `http://127.0.0.1:5173`
  - Backend FastAPI: `http://127.0.0.1:8800`
  - Serviço LLM: `http://127.0.0.1:8002`

## Reparação Automática de PDF
- **[Backend LLM]** Função `_extract_pdf_text()` em `webapp/LLM/backend/app/main.py` aplica fallback PyPDF caso Ollama rejeite o PDF.
- **[Arquivos gerados]** PDFs reparados são armazenados em `webapp/LLM/tmp_reparos/` com sufixo `_reparado.pdf`.
- **[Logs]** Procure por "PDF reparado automaticamente" no console do serviço LLM.

## Notas para IA / Novos Desenvolvedores
- **[Pontos de entrada]** `webapp/backend.py` (API principal) e `webapp/LLM/backend/app/main.py` (pipeline LLM).
- **[Fluxo Importação Romaneio]** Upload → `/api/upload` (LLM) → `_process_pipeline` → resposta formatada → backend `/actions/import-romaneio` grava itens.
- **[Configuração]** Variáveis via `.env` (se existir) ou padrões definidos em `webapp/backend.py` e `webapp/LLM/backend/app/main.py`.
- **[Testes manuais]** Use `repdf.py` para validar reparo PyPDF isoladamente.

## Próximos Passos
- **[Automação de build]** Avaliar empacotamento PyInstaller para gerar executáveis na pasta `client/`.
- **[Documentação adicional]** Atualizar este arquivo quando novos módulos forem adicionados ou paths mudarem.
