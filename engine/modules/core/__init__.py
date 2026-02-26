"""
🔧 MÓDULO CORE - FUNCIONALIDADES CENTRAIS  
==========================================

Contém as funções fundamentais do sistema:
- Gerenciamento de arquivos e diretórios
- Cálculos financeiros e preços
- Validações e conversões
- Utilitários diversos
"""

from .file_manager import (
    get_app_base_dir,
    save_targets, load_targets,
    save_entry,
    carregar_marcas_salvas, salvar_marcas, adicionar_nova_marca,
    carregar_margem_padrao, salvar_margem_padrao
)

from .calculator import (
    calcular_preco_final,
    gerar_descricao_completa
)

from .validator import (
    converter_para_caps,
    obter_letra_categoria,
    limpar_nome_produto,
    detectar_e_remover_prefixo_comum_codigos
)

__all__ = [
    # File Manager
    'get_app_base_dir', 'save_targets', 'load_targets', 'save_entry',
    'carregar_marcas_salvas', 'salvar_marcas', 'adicionar_nova_marca',
    'carregar_margem_padrao', 'salvar_margem_padrao',
    
    # Calculator  
    'calcular_preco_final', 'gerar_descricao_completa',
    
    # Validator
    'converter_para_caps', 'obter_letra_categoria',
    'limpar_nome_produto', 'detectar_e_remover_prefixo_comum_codigos'
]
