"""
🤖 MÓDULO DE AUTOMAÇÃO
======================

Contém toda a lógica de automação do ByteEmpresa:
- Ativação de janela e posicionamento
- Automação da Tela 1 (dados básicos)
- Automação da Tela 2 (preços e estoque)
- Controle de fluxo completo
"""

from .byte_empresa import (
    ativar_janela_byte_empresa,
    executar_tela1_mecanico,
    executar_tela2_mecanico,
    inserir_produto_mecanico
)

__all__ = [
    'ativar_janela_byte_empresa',
    'executar_tela1_mecanico', 
    'executar_tela2_mecanico',
    'inserir_produto_mecanico'
]
