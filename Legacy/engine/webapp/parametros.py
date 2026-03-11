"""Central de parâmetros opcionais do LojaSync Web.

Este arquivo não é obrigatório – se estiver ausente, o sistema utiliza
todos os *defaults* internos. Porém, quando presente, fornece um ponto
único para documentar e ajustar:

1. **Hosts & Portas** – valores usados pelo ``launcher.py``.
2. **Automação PyAutoGUI** – tempos e toggles aplicados sobre
   ``modules/automation/byte_empresa.py``.
3. **Catálogo de Botões** – descrição rápida das ações de UI (web ou
   desktop) e parâmetros associados.
4. **Registro de Funções** – mapeia funções críticas para trechos de
   código e facilita manutenção futura.

⚠️ Importante: mantenha tipos simples (``int``, ``float``, ``str`` ou
``bool``). Ferramentas que usam este arquivo ignoram valores inválidos
para evitar que o programa quebre.
"""

from __future__ import annotations

from typing import Any, Dict


# ---------------------------------------------------------------------------
# 1) Hosts & Serviços -------------------------------------------------------
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
FRONTEND_PORT = 5173
BACKEND_PORT = 8800
LLM_HOST = HOST
LLM_PORT = 8002
BROWSER_OVERRIDE_HOST = "127.0.0.1"


# ---------------------------------------------------------------------------
# 2) Automação PyAutoGUI ----------------------------------------------------
# ---------------------------------------------------------------------------
# Cada campo possui ``value`` (utilizado em tempo de execução) e uma
# ``description`` exibida na UI de configurações.

AUTOMATION: Dict[str, Dict[str, Dict[str, Any]]] = {
    "delays": {
        "DELAY_CLICK": {
            "value": 0,
            "description": "Tempo entre cliques para evitar duplo clique acidental.",
        },
        "DELAY_TAB": {
            "value": 0.0001,
            "description": "Pausa entre tabs nas telas do Byte Empresa.",
        },
        "DELAY_DIGITACAO": {
            "value": 0.00001,
            "description": "Velocidade da digitação simulada (seg por caractere).",
        },
        "DELAY_ENTRE_TELAS": {
            "value": 0.00001,
            "description": "Espera após salvar a tela 1 antes de iniciar a tela 2.",
        },
        "DELAY_ENTRE_PRODUTOS": {
            "value": 0.00001,
            "description": "Intervalo entre produtos consecutivos.",
        },
    },
    "tabs": {
        "T1_TABS_TO_CATEGORIA": {
            "value": 3,
            "description": "Quantidade de TABs até o campo categoria na tela 1.",
        },
        "T1_TABS_TO_CODFAB": {
            "value": 16,
            "description": "Tabs até o campo código do fabricante.",
        },
        "T1_TABS_TO_SALVAR": {
            "value": 3,
            "description": "Tabs do campo código até o botão salvar (tela 1).",
        },
        "T2_TABS_TO_PRECO": {
            "value": 1,
            "description": "Tabs até o campo preço na tela 2.",
        },
        "T2_TABS_TO_QTD": {
            "value": 8,
            "description": "Tabs até o campo quantidade na tela 2.",
        },
        "T2_TABS_TO_VENDA": {
            "value": 2,
            "description": "Tabs até o campo preço de venda na tela 2.",
        },
        "T2_TABS_TO_SALVAR": {
            "value": 2,
            "description": "Tabs até o botão salvar ao final da tela 2.",
        },
    },
    "toggles": {
        "ENABLE_TELA1": {
            "value": True,
            "description": "Executa a tela 1 (dados gerais).",
        },
        "ENABLE_TELA2": {
            "value": True,
            "description": "Executa a tela 2 (estoque/preço).",
        },
        "ENABLE_CLICK_ATIVAR_JANELA": {
            "value": True,
            "description": "Clique inicial para trazer o Byte Empresa ao foco.",
        },
        "ENABLE_CLICAR_TRES_PONTINHOS": {
            "value": True,
            "description": "Executa o clique final nos três pontinhos.",
        },
    },
    "timing": {
        "TIMEOUT_AUTOMACAO": {
            "value": 900,
            "description": "Tempo limite (s) para aguardar retorno da automação remota.",
        }
    },
}


# ---------------------------------------------------------------------------
# 3) Catálogo de Botões -----------------------------------------------------
# ---------------------------------------------------------------------------
# Esta sessão documenta botões importantes. ``button_id`` pode ser o ID do
# elemento HTML ou o identificador interno usado na UI desktop.

BUTTONS: Dict[str, Dict[str, Any]] = {
    "btn-salvar": {
        "label": "Salvar Dados",
        "layer": "frontend",
        "module": "engine/webapp/script.js",
        "function": "handleProductFormSubmit",
        "description": "Envia o formulário atual para o backend (/products).",
        "parameters": {
            "debounce_ms": 250,
            "allow_empty_grades": False,
        },
    },
    "btn-importar": {
        "label": "Importar Romaneio",
        "layer": "frontend",
        "module": "engine/webapp/script.js",
        "function": "handleRomaneioImport",
        "description": "Abre seletor de arquivo, envia para /romaneio/import e acompanha o job.",
        "parameters": {
            "max_file_mb": 15,
            "preview_rows": 5,
        },
    },
    "desktop.btn-automation-start": {
        "label": "Executar Cadastro",
        "layer": "desktop",
        "module": "engine/modules/interface/main_gui.py",
        "function": "abrir_configuracoes → iniciar automação",
        "description": "Aciona o backend para enviar produtos ao executor PyAutoGUI.",
        "parameters": {
            "require_targets": True,
            "sync_with_remote_agents": True,
        },
    },
}


# ---------------------------------------------------------------------------
# 4) Registro de Funções ----------------------------------------------------
# ---------------------------------------------------------------------------

FUNCTION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "backend.import_romaneio": {
        "module": "engine/webapp/backend.py",
        "callable": "import_romaneio",
        "description": "Orquestra parsing do PDF via serviço LLM e salva os itens extraídos.",
        "parameters": {
            "timeout_seconds": 900,
            "max_pages": 35,
        },
    },
    "backend.patch_product": {
        "module": "engine/webapp/backend.py",
        "callable": "update_product",
        "description": "Atualiza campos individuais (nome, quantidade, preço final etc).",
        "parameters": {
            "allow_empty_final_price": True,
        },
    },
    "automation.byte_empresa": {
        "module": "engine/modules/automation/byte_empresa.py",
        "callable": "executar_tela1_mecanico / executar_tela2_mecanico",
        "description": "Fluxo PyAutoGUI responsável por preencher o Byte Empresa.",
        "parameters": {
            "safe_mode": True,
            "log_debug": True,
        },
    },
}


__all__ = [
    "HOST",
    "FRONTEND_PORT",
    "BACKEND_PORT",
    "LLM_HOST",
    "LLM_PORT",
    "BROWSER_OVERRIDE_HOST",
    "AUTOMATION",
    "BUTTONS",
    "FUNCTION_REGISTRY",
]
