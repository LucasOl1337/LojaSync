"""
🧾 MÓDULO DE PARSERS
====================

Contém os processadores de romaneio e importação:
- Parser de PDF
- Parser de TXT universal
- Parser de TXT padrão
"""

try:
    from .romaneio_pdf import processar_romaneio_completo as processar_pdf
except ImportError:
    processar_pdf = None

try:
    from .romaneio_universal import processar_romaneio_completo as processar_universal
except ImportError:
    processar_universal = None

try:
    from .romaneio_padrao import processar_romaneio_completo as processar_padrao
except ImportError:
    processar_padrao = None

__all__ = [
    'processar_pdf',
    'processar_universal', 
    'processar_padrao'
]
