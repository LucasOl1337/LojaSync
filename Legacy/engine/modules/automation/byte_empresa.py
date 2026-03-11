"""
🎯 AUTOMAÇÃO DO BYTE EMPRESA
============================

Responsável por toda a automação do sistema ByteEmpresa:
- Ativação de janela e coordenadas
- Execução das telas 1 e 2
- Controle completo do fluxo de cadastro
"""

import time
import json
import pyautogui
from tkinter import messagebox
from typing import Dict, Tuple, Optional, Any
from ..core.validator import obter_letra_categoria
from ..config.constants import (
    DELAY_CLICK, DELAY_TAB, DELAY_DIGITACAO,
    DELAY_ENTRE_TELAS, DELAY_ENTRE_PRODUTOS
)
try:
    from ...webapp import parametros as _user_params  # type: ignore
except ImportError:  # pragma: no cover - arquivo opcional
    _user_params = None
from ..core.file_manager import get_app_base_dir


def _sleep_cancelable(segundos: float, cancel_event: Optional[object] = None):
    """Dormir em pequenos passos para permitir cancelamento imediato."""
    if not segundos:
        return
    fim = time.time() + segundos
    passo = 0.05
    while time.time() < fim:
        if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
            raise KeyboardInterrupt("Cancelado pelo usuário")
        restante = fim - time.time()
        time.sleep(passo if restante > passo else max(0, restante))


# =========================
# Configuração em tempo real
# =========================
_CFG_CACHE: Optional[Dict[str, float]] = None
_PARAM_OVERRIDES: Dict[str, Any] = {}

_BASE_VALUES = {
    'DELAY_CLICK': DELAY_CLICK,
    'DELAY_TAB': DELAY_TAB,
    'DELAY_DIGITACAO': DELAY_DIGITACAO,
    'DELAY_ENTRE_TELAS': DELAY_ENTRE_TELAS,
    'DELAY_ENTRE_PRODUTOS': DELAY_ENTRE_PRODUTOS,
}


def _extract_param_value(section: Dict[str, Any], key: str) -> Any:
    data = section.get(key)
    if isinstance(data, dict):
        return data.get("value")
    return data


def _load_parametros_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if not _user_params:
        return overrides
    auto_cfg = getattr(_user_params, "AUTOMATION", None)
    if not isinstance(auto_cfg, dict):
        return overrides

    delays = auto_cfg.get("delays", {}) or {}
    for key in ("DELAY_CLICK", "DELAY_TAB", "DELAY_DIGITACAO", "DELAY_ENTRE_TELAS", "DELAY_ENTRE_PRODUTOS"):
        raw = _extract_param_value(delays, key)
        if raw is None:
            continue
        try:
            overrides[key] = float(raw)
        except (TypeError, ValueError):
            pass

    tabs = auto_cfg.get("tabs", {}) or {}
    tab_keys = (
        "T1_TABS_TO_CATEGORIA",
        "T1_TABS_TO_CODFAB",
        "T1_TABS_TO_SALVAR",
        "T2_TABS_TO_PRECO",
        "T2_TABS_TO_QTD",
        "T2_TABS_TO_VENDA",
        "T2_TABS_TO_SALVAR",
    )
    for key in tab_keys:
        raw = _extract_param_value(tabs, key)
        if raw is None:
            continue
        try:
            overrides[key] = int(raw)
        except (TypeError, ValueError):
            pass

    toggles = auto_cfg.get("toggles", {}) or {}
    for key in ("ENABLE_TELA1", "ENABLE_TELA2", "ENABLE_CLICK_ATIVAR_JANELA", "ENABLE_CLICAR_TRES_PONTINHOS"):
        raw = _extract_param_value(toggles, key)
        if raw is None:
            continue
        overrides[key] = bool(raw)

    timing = auto_cfg.get("timing", {}) or {}
    raw_timeout = _extract_param_value(timing, "TIMEOUT_AUTOMACAO")
    if raw_timeout is not None:
        try:
            overrides["TIMEOUT_AUTOMACAO"] = float(raw_timeout)
        except (TypeError, ValueError):
            pass

    return overrides

def _cfg_path():
    return get_app_base_dir() / "data" / "automacao.json"

def _load_cfg_file() -> Dict[str, Any]:
    try:
        p = _cfg_path()
        if not p.exists():
            return {}
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Mantém os tipos conforme salvos (float, int, bool, str)
        return dict(data or {})
    except Exception:
        return {}

def _get_effective_value(key: str, default: Any) -> Any:
    param_val = _PARAM_OVERRIDES.get(key)
    if param_val is not None:
        return param_val
    cfg = _CFG_CACHE or {}
    cfg_val = cfg.get(key)
    if cfg_val is not None:
        return cfg_val
    return default


def _apply_overrides():
    global DELAY_CLICK, DELAY_TAB, DELAY_DIGITACAO, DELAY_ENTRE_TELAS, DELAY_ENTRE_PRODUTOS, _CFG_CACHE
    _CFG_CACHE = _load_cfg_file()
    DELAY_CLICK = _get_effective_value('DELAY_CLICK', _BASE_VALUES['DELAY_CLICK'])
    DELAY_TAB = _get_effective_value('DELAY_TAB', _BASE_VALUES['DELAY_TAB'])
    DELAY_DIGITACAO = _get_effective_value('DELAY_DIGITACAO', _BASE_VALUES['DELAY_DIGITACAO'])
    DELAY_ENTRE_TELAS = _get_effective_value('DELAY_ENTRE_TELAS', _BASE_VALUES['DELAY_ENTRE_TELAS'])
    DELAY_ENTRE_PRODUTOS = _get_effective_value('DELAY_ENTRE_PRODUTOS', _BASE_VALUES['DELAY_ENTRE_PRODUTOS'])

def get_config_automacao() -> Dict[str, Any]:
    """Retorna os valores efetivos atuais (após override)."""
    if _CFG_CACHE is None:
        _apply_overrides()
    defaults: Dict[str, Any] = {
        'DELAY_CLICK': _BASE_VALUES['DELAY_CLICK'],
        'DELAY_TAB': _BASE_VALUES['DELAY_TAB'],
        'DELAY_DIGITACAO': _BASE_VALUES['DELAY_DIGITACAO'],
        'DELAY_ENTRE_TELAS': _BASE_VALUES['DELAY_ENTRE_TELAS'],
        'DELAY_ENTRE_PRODUTOS': _BASE_VALUES['DELAY_ENTRE_PRODUTOS'],
        # Tabs entre ações
        'T1_TABS_TO_CATEGORIA': 3,
        'T1_TABS_TO_CODFAB': 16,
        'T1_TABS_TO_SALVAR': 3,
        'T2_TABS_TO_PRECO': 1,
        'T2_TABS_TO_QTD': 8,
        'T2_TABS_TO_VENDA': 2,
        'T2_TABS_TO_SALVAR': 2,
        # Toggles
        'ENABLE_TELA1': True,
        'ENABLE_TELA2': True,
        'ENABLE_CLICK_ATIVAR_JANELA': True,
        'ENABLE_CLICAR_TRES_PONTINHOS': True,
        'TIMEOUT_AUTOMACAO': 900,
    }
    out: Dict[str, Any] = {}
    for key, default in defaults.items():
        out[key] = _get_effective_value(key, default)
    return out

def salvar_config_automacao(cfg: Dict[str, Any]):
    p = _cfg_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def recarregar_config_automacao():
    _apply_overrides()

# Aplica overrides no import do módulo
_PARAM_OVERRIDES = _load_parametros_overrides()
_apply_overrides()


def _check_cancel(cancel_event: Optional[object] = None):
    """Lança interrupção se cancelado."""
    if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
        raise KeyboardInterrupt("Cancelado pelo usuário")


def ativar_janela_byte_empresa(coordenadas: dict) -> Tuple[bool, str]:
    """
    🎯 ATIVADOR DE JANELA BYTE EMPRESA
    
    Ativa a janela do Byte Empresa através de duplo clique na posição calibrada.
    
    PARÂMETROS:
    coordenadas (dict): Dicionário com as coordenadas calibradas
    
    RETORNO:
    Tuple[bool, str]: (sucesso, mensagem)
    """
    try:
        cfg = get_config_automacao()
        if not cfg.get('ENABLE_CLICK_ATIVAR_JANELA', True):
            return True, "Config: pulou clique de ativação"
        if "byte_empresa_posicao" not in coordenadas:
            return False, "Posição do Byte Empresa não calibrada"
        
        posicao = coordenadas["byte_empresa_posicao"]
        x, y = posicao["x"], posicao["y"]
        
        print(f"DEBUG: Ativando Byte Empresa na posição calibrada: ({x}, {y})")
        pyautogui.click(x, y)
        _sleep_cancelable(DELAY_CLICK)
        return True, "Byte Empresa (Coordenada Calibrada)"
            
    except Exception as e:
        print(f"DEBUG: Erro ao ativar Byte Empresa: {e}")
        return False, f"Erro: {e}"


def executar_tela1_mecanico(dados: dict, coordenadas: dict, cancel_event: Optional[object] = None) -> bool:
    """
    🎯 AUTOMAÇÃO DA TELA 1 - DADOS BÁSICOS
    
    Executa a primeira tela do cadastro no Byte Empresa.
    
    FLUXO COMPLETO:
    1. Click no campo Descrição
    2. Digita descrição completa (Nome + Marca + Código)
    3. 3x Tab → categoria
    4. Digita letra da categoria (m/f/i/a)
    5. Enter → confirma categoria
    6. 16x Tab → código do fabricante
    7. Limpa campo e digita código
    8. 3x Tab → botão salvar
    9. Enter → salva e vai para Tela 2
    
    PARÂMETROS:
    dados (dict): Dados do produto
    coordenadas (dict): Coordenadas calibradas
    
    RETORNO:
    bool: True se executou com sucesso
    """
    try:
        cfg = get_config_automacao()
        if not cfg.get('ENABLE_TELA1', True):
            print("DEBUG: TELA 1 desabilitada por configuração, pulando...")
            return True
        print("DEBUG: === INICIANDO TELA 1 - DADOS BÁSICOS ===")
        desc_coord = coordenadas.get("campo_descricao")
        if not desc_coord:
            raise Exception("❌ Coordenada do campo descrição não encontrada")
        
        print(f"DEBUG: Clicando no campo Descrição na posição ({desc_coord['x']}, {desc_coord['y']})")
        _check_cancel(cancel_event)
        pyautogui.click(desc_coord["x"], desc_coord["y"])
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Limpar campo (2 backspaces)
        for _ in range(2):
            pyautogui.press('backspace')
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Digitar descrição completa
        descricao_completa = dados.get("descricao_completa", dados["nome"].strip())
        print(f"DEBUG: Digitando descrição completa: '{descricao_completa}' no Byte Empresa")
        
        try:
            import keyboard
            print(f"DEBUG: Digitando '{descricao_completa}' com keyboard")
            keyboard.write(descricao_completa, delay=DELAY_DIGITACAO)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada. Execute: pip install keyboard")
        _check_cancel(cancel_event)
        _sleep_cancelable(0.2, cancel_event)
        
        # Navegar para categoria
        t_tabs_cat = int(cfg.get('T1_TABS_TO_CATEGORIA', 3))
        print(f"DEBUG: Navegando para categoria ({t_tabs_cat} tabs)")
        try:
            import keyboard
            for _ in range(t_tabs_cat):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Selecionar categoria
        letra_categoria = obter_letra_categoria(dados["categoria"])
        print(f"DEBUG: Selecionando categoria '{dados['categoria']}' com letra '{letra_categoria}'")
        _check_cancel(cancel_event)
        try:
            import keyboard
            keyboard.press_and_release(letra_categoria)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Confirmar categoria
        print("DEBUG: Confirmando categoria com Enter")
        _check_cancel(cancel_event)
        try:
            import keyboard
            keyboard.press_and_release('enter')
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Navegar para Cod.Fabricante
        t_tabs_cod = int(cfg.get('T1_TABS_TO_CODFAB', 16))
        print(f"DEBUG: Navegando para Cod.Fabricante ({t_tabs_cod} tabs)")
        try:
            import keyboard
            for _ in range(t_tabs_cod):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Limpar e digitar código
        print("DEBUG: Limpando campo Cod.Fabricante com keyboard")
        texto_codigo = dados["codigo"]
        _check_cancel(cancel_event)
        try:
            import keyboard
            for _ in range(20):
                keyboard.press_and_release('backspace')
            _sleep_cancelable(DELAY_CLICK, cancel_event)
            
            print(f"DEBUG: Digitando código '{texto_codigo}' com keyboard")
            keyboard.write(texto_codigo, delay=DELAY_DIGITACAO)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Navegar para botão salvar
        t_tabs_salvar = int(cfg.get('T1_TABS_TO_SALVAR', 3))
        print(f"DEBUG: Navegando para botão salvar ({t_tabs_salvar} tabs)")
        try:
            import keyboard
            for _ in range(t_tabs_salvar):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Salvar TELA 1
        print("DEBUG: Salvando TELA 1 (Enter) - Transição para TELA 2")
        _check_cancel(cancel_event)
        try:
            import keyboard
            keyboard.press_and_release('enter')
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_ENTRE_TELAS, cancel_event)
        
        return True
        
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            print("DEBUG: Execução cancelada pelo usuário na TELA 1")
            return False
        messagebox.showerror("Erro TELA 1", f"Falha na automação TELA 1: {e}")
        return False


def executar_tela2_mecanico(dados: dict, coordenadas: dict, cancel_event: Optional[object] = None) -> bool:
    """
    💰 AUTOMAÇÃO DA TELA 2 - PREÇOS E ESTOQUE
    
    Executa a segunda tela do cadastro: preços e estoque.
    
    FLUXO COMPLETO:
    1. 1x Tab → campo preço de compra
    2. Digita preço de custo
    3. 8x Tab → campo quantidade
    4. Digita quantidade
    5. 2x Tab → campo preço de venda
    6. Digita preço final calculado
    7. 2x Tab → botão salvar
    8. Enter → salva produto
    9. Click 3 pontinhos → volta para Tela 1
    
    PARÂMETROS:
    dados (dict): Dados do produto
    coordenadas (dict): Coordenadas calibradas
    
    RETORNO:
    bool: True se executou com sucesso
    """
    try:
        cfg = get_config_automacao()
        if not cfg.get('ENABLE_TELA2', True):
            print("DEBUG: TELA 2 desabilitada por configuração, pulando...")
            return True
        print("DEBUG: === INICIANDO TELA 2 ===")
        
        # Navegar para Preço de Compra
        t2_to_preco = int(cfg.get('T2_TABS_TO_PRECO', 1))
        print(f"DEBUG: TELA 2 - Navegando para Preço de Compra ({t2_to_preco} tab(s))")
        _check_cancel(cancel_event)
        try:
            import keyboard
            for _ in range(t2_to_preco):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Inserir preço de custo
        print(f"DEBUG: TELA 2 - Limpando e inserindo preço '{dados['preco']}'")
        _check_cancel(cancel_event)
        try:
            import keyboard
            for _ in range(15):
                keyboard.press_and_release('backspace')
            _sleep_cancelable(DELAY_CLICK, cancel_event)
            keyboard.write(dados["preco"], delay=DELAY_DIGITACAO)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Navegar para Quantidade
        t2_to_qtd = int(cfg.get('T2_TABS_TO_QTD', 8))
        print(f"DEBUG: TELA 2 - Navegando para Quantidade ({t2_to_qtd} tabs)")
        try:
            import keyboard
            for _ in range(t2_to_qtd):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(0.2, cancel_event)
        
        # Inserir quantidade
        print(f"DEBUG: TELA 2 - Limpando e inserindo quantidade '{dados['quantidade']}'")
        _check_cancel(cancel_event)
        try:
            import keyboard
            for _ in range(10):
                keyboard.press_and_release('backspace')
            _sleep_cancelable(DELAY_CLICK, cancel_event)
            keyboard.write(dados["quantidade"], delay=DELAY_DIGITACAO)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Navegar para Preço de Venda
        t2_to_venda = int(cfg.get('T2_TABS_TO_VENDA', 2))
        print(f"DEBUG: TELA 2 - Navegando para Preço de Venda ({t2_to_venda} tabs)")
        try:
            import keyboard
            for _ in range(t2_to_venda):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Inserir preço final
        preco_final = dados.get("preco_final", dados["preco"])
        print(f"DEBUG: TELA 2 - Limpando e inserindo preço final '{preco_final}'")
        _check_cancel(cancel_event)
        try:
            import keyboard
            for _ in range(15):
                keyboard.press_and_release('backspace')
            _sleep_cancelable(DELAY_CLICK, cancel_event)
            keyboard.write(preco_final, delay=DELAY_DIGITACAO)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Navegar para botão salvar (2 tabs)
        t2_to_salvar = int(cfg.get('T2_TABS_TO_SALVAR', 2))
        print(f"DEBUG: TELA 2 - Navegando para botão salvar ({t2_to_salvar} tabs)")
        try:
            import keyboard
            for _ in range(t2_to_salvar):
                keyboard.press_and_release('tab')
                _sleep_cancelable(DELAY_TAB, cancel_event)
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_CLICK, cancel_event)
        
        # Salvar produto
        print("DEBUG: TELA 2 - Salvando com Enter")
        try:
            import keyboard
            keyboard.press_and_release('enter')
        except ImportError:
            raise Exception("Biblioteca 'keyboard' não está instalada")
        _sleep_cancelable(DELAY_ENTRE_TELAS, cancel_event)
        
        # Clicar nos 3 pontinhos para voltar (opcional)
        if cfg.get('ENABLE_CLICAR_TRES_PONTINHOS', True):
            print("DEBUG: TELA 2 - Clicando nos 3 pontinhos para voltar")
            tres_pontos_coord = coordenadas.get("tres_pontinhos")
            if not tres_pontos_coord:
                raise Exception("Coordenada dos 3 pontinhos não encontrada")
            _check_cancel(cancel_event)
            pyautogui.click(tres_pontos_coord["x"], tres_pontos_coord["y"])
            _sleep_cancelable(1, cancel_event)
        else:
            print("DEBUG: TELA 2 - Pulando clique nos 3 pontinhos por configuração")
        print("DEBUG: === FINALIZOU AUTOMAÇÃO - RETORNOU PARA TELA 1 ===")
        
        return True
        
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            print("DEBUG: Execução cancelada pelo usuário na TELA 2")
            return False
        messagebox.showerror("Erro TELA 2", f"Falha na automação TELA 2: {e}")
        return False


def inserir_produto_mecanico(dados_produto: dict, coordenadas: dict, ativar_janela: bool = True, cancel_event: Optional[object] = None) -> bool:
    """
    🎮 CONTROLE MESTRE DE AUTOMAÇÃO
    
    Executa o cadastro completo de um produto no Byte Empresa.
    
    FLUXO:
    1. Ativa janela ByteEmpresa (se ativar_janela=True)
    2. Executa Tela 1 (dados básicos)
    3. Executa Tela 2 (preços e estoque)
    
    PARÂMETROS:
    dados_produto (dict): Dados completos do produto
    coordenadas (dict): Coordenadas calibradas
    ativar_janela (bool): Se deve ativar janela (True=individual, False=massa)
    
    RETORNO:
    bool: True se executou com sucesso
    """
    try:
        # Ativar janela apenas se solicitado (individual vs massa)
        if ativar_janela:
            janela_ativada, tipo_janela = ativar_janela_byte_empresa(coordenadas)
            if not janela_ativada:
                raise Exception("Falha ao ativar janela do Byte Empresa")
        
        # Executar Tela 1
        if not executar_tela1_mecanico(dados_produto, coordenadas, cancel_event=cancel_event):
            return False
        
        # Executar Tela 2
        if not executar_tela2_mecanico(dados_produto, coordenadas, cancel_event=cancel_event):
            return False
        
        return True
        
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            print("DEBUG: Execução cancelada pelo usuário durante o fluxo principal")
            return False
        messagebox.showerror("Erro na Automação", str(e))
        return False
