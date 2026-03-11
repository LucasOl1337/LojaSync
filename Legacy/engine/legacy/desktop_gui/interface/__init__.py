"""
🖼️ MÓDULO DE INTERFACE
======================

Contém todas as janelas e componentes de interface:
- Janela de log de produtos
- Janela de calibração
- Janela de marcas
- Janela de margem
- Interface principal
"""

from .log_window import LogWindow
from .calibration_window import CalibrationWindow
from .marca_window import MarcaWindow
from .margem_window import MargemWindow

__all__ = [
    'LogWindow',
    'CalibrationWindow', 
    'MarcaWindow',
    'MargemWindow'
]
