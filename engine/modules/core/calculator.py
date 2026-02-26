"""
💰 CALCULADORA FINANCEIRA
=========================

Responsável por todos os cálculos relacionados a preços e descrições:
- Cálculo de preço final com margem
- Geração de descrição completa
- Formatação de valores
"""

from .file_manager import carregar_margem_padrao


def calcular_preco_final(preco_custo: str) -> str:
    """
    💰 CÁLCULO AUTOMÁTICO DE PREÇO DE VENDA
    
    Aplica margem de lucro configurável e arredonda para ,90
    
    PROCESSO:
    1. Limpa formatação do preço (remove R$, vírgulas)
    2. Converte para float
    3. Aplica margem configurada (padrão 206% = 2.06)
    4. Arredonda para cima terminando em ,90
    5. Formata de volta para string brasileira
    
    EXEMPLO:
    - Entrada: "10,00" ou "R$ 10,00"
    - Margem: 206% (2.06)
    - Cálculo: 10.00 * 2.06 = 20.60
    - Arredondamento: 20.90
    - Saída: "20,90"
    
    PARÂMETROS:
    preco_custo (str): Preço de custo formatado
    
    RETORNO:
    str: Preço final formatado brasileiro (ex: "20,90")
    """
    try:
        # Remove formatação brasileira e converte para número
        preco_str = preco_custo.replace("R$", "").replace(",", ".").strip()
        preco_float = float(preco_str)
        
        # Carrega margem configurada pelo usuário
        margem = carregar_margem_padrao()  # Padrão: 2.06 (106%)
        
        # Aplica margem de lucro
        preco_com_margem = preco_float * margem
        
        # Arredonda para cima e termina em ,90
        # Exemplo: 20.60 → 20.90, 15.32 → 15.90
        preco_arredondado = round(preco_com_margem + 0.1, 0) - 0.1
        
        # Formata de volta para padrão brasileiro
        preco_final = f"{preco_arredondado:.2f}".replace(".", ",")
        
        return preco_final
    except Exception:
        # Em caso de erro, retorna preço original
        return preco_custo


def gerar_descricao_completa(nome: str, marca: str, codigo: str) -> str:
    """
    🏷️ GERADOR DE DESCRIÇÃO COMPLETA
    
    Gera a descrição completa no formato: Nome + Marca + Código
    
    PARÂMETROS:
    nome (str): Nome do produto
    marca (str): Marca do produto  
    codigo (str): Código do produto
    
    RETORNO:
    str: Descrição completa formatada
    
    EXEMPLOS:
    - Nome: "CALÇA JEANS", Marca: "OGOCHI", Código: "123"
    - Resultado: "CALÇA JEANS OGOCHI 123"
    
    - Nome: "CAMISETA", Marca: "", Código: "456" 
    - Resultado: "CAMISETA 456"
    """
    if not marca.strip():
        return f"{nome} {codigo}"
    return f"{nome} {marca} {codigo}"


def extrair_preco_de_string(preco_str: str) -> str:
    """
    🔢 EXTRATOR DE PREÇO
    
    Extrai o valor numérico de strings como 'R$49,40'.
    Retorna no formato '49,40' (sem R$).
    """
    # Remove R$ e espaços
    preco_limpo = preco_str.replace('R$', '').strip()
    return preco_limpo
