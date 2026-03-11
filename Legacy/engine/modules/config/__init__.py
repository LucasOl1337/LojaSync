"""
🎨 MÓDULO DE CONFIGURAÇÕES
=========================

Contém todas as configurações globais do sistema:
- Cores e tema visual
- Fontes e tipografia
- Constantes do sistema
"""

from .theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from .constants import APP_NAME, APP_VERSION, DEFAULT_GEOMETRY

__all__ = [
    'TELEGRAM_COLORS', 
    'TELEGRAM_FONTS',
    'APP_NAME',
    'APP_VERSION', 
    'DEFAULT_GEOMETRY'
]
