"""
✅ VALIDADOR E CONVERSORES
==========================

Responsável por validações e conversões de dados:
- Conversão automática para CAPS
- Mapeamento de categorias
- Validações de formulário
"""

import tkinter as tk
from ..config.constants import CATEGORIA_PARA_LETRA


def converter_para_caps(entry_widget: tk.Entry) -> None:
    """
    🔤 CONVERSÃO AUTOMÁTICA PARA MAIÚSCULAS
    
    Converte automaticamente o texto digitado para MAIÚSCULAS.
    Usado nos campos de entrada para padronizar dados.
    
    PARÂMETROS:
    entry_widget (tk.Entry): Widget de entrada de texto
    """
    try:
        texto_atual = entry_widget.get()
        texto_caps = texto_atual.upper()
        if texto_atual != texto_caps:
            cursor_pos = entry_widget.index(tk.INSERT)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, texto_caps)
            entry_widget.icursor(cursor_pos)
    except Exception:
        pass


def obter_letra_categoria(categoria: str) -> str:
    """
    🗂️ MAPEADOR DE CATEGORIA PARA LETRA
    
    Mapeia categoria para a letra inicial usada no sistema ByteEmpresa.
    
    MAPEAMENTO:
    - "Masculino" → "m"
    - "Feminino" → "f"
    - "Infantil" → "i"  
    - "Acessorios" → "a"
    
    PARÂMETROS:
    categoria (str): Nome da categoria
    
    RETORNO:
    str: Letra correspondente (padrão: "m")
    """
    return CATEGORIA_PARA_LETRA.get(categoria, "m")


def validar_campos_obrigatorios(nome: str, codigo: str, quantidade: str, 
                               preco: str, categoria: str) -> bool:
    """
    ✅ VALIDADOR DE CAMPOS OBRIGATÓRIOS
    
    Verifica se todos os campos obrigatórios foram preenchidos.
    
    PARÂMETROS:
    nome, codigo, quantidade, preco, categoria (str): Campos do formulário
    
    RETORNO:
    bool: True se todos os campos estão preenchidos
    """
    return all([nome.strip(), codigo.strip(), quantidade.strip(), 
                preco.strip(), categoria.strip()])


def limpar_nome_produto(nome: str) -> str:
    """
    🧹 LIMPADOR DE NOME DE PRODUTO - VERSÃO RIGOROSA

    Limpa o nome do produto removendo TODOS os caracteres especiais,
    mantendo apenas letras, números e acentos.

    Remove:
    - TODOS os caracteres especiais: . - + = * / \ | @ # $ % & ( ) [ ] { } < > ~
    - Códigos entre asteriscos: *DP*, *BF-P*, etc.
    - Observações: OBS: ...
    - Indicadores AD, GG no final
    - Hífen inicial e final
    - Espaços extras e duplicados

    Mantém:
    - Letras (a-z, A-Z)
    - Números (0-9)
    - Acentos e cedilhas (á, é, ã, ç, etc.)
    - Espaços simples entre palavras
    """
    import re

    # Remove observações
    nome_limpo = re.sub(r'\s*OBS:.*$', '', nome, flags=re.IGNORECASE)

    # Remove códigos entre asteriscos
    nome_limpo = re.sub(r'\*[A-Z\-]+\*', '', nome_limpo)

    # Remove indicadores AD, GG no final
    nome_limpo = re.sub(r'\s+(AD|GG)\s*$', '', nome_limpo)

    # REMOÇÃO RIGOROSA: Mantém apenas letras, números, acentos e espaços
    # Permite: a-z, A-Z, 0-9, espaços, e caracteres acentuados
    nome_limpo = re.sub(r'[^a-zA-ZÀ-ÿ0-9\s]', '', nome_limpo)

    # Remove espaços extras e limpa
    nome_limpo = ' '.join(nome_limpo.split())
    nome_limpo = nome_limpo.strip()

    return nome_limpo


def detectar_e_remover_prefixo_comum_codigos(produtos: list) -> list:
    """
    🔍 DETECTOR DE PREFIXO COMUM EM CÓDIGOS
    
    Detecta se 3 ou mais produtos têm o mesmo prefixo no código
    e remove esse prefixo comum de todos os códigos.
    
    Exemplo:
    - Entrada: ["1458718", "1458748", "1458756", "1458193"]
    - Prefixo comum: "1458" (4 produtos começam com isso)
    - Saída: ["718", "748", "756", "193"]
    
    PARÂMETROS:
    produtos (list): Lista de dicionários com produtos
    
    RETORNO:
    list: Lista de produtos com códigos limpos
    """
    if len(produtos) < 3:
        return produtos
    
    # Extrair códigos
    codigos = []
    for produto in produtos:
        codigo = produto.get('codigo', '').strip()
        if codigo:
            codigos.append(codigo)
    
    if len(codigos) < 3:
        return produtos
    
    # Encontrar prefixo comum
    prefixo_comum = encontrar_prefixo_comum(codigos)
    
    # Se prefixo tem pelo menos 3 caracteres e pelo menos 3 produtos o usam
    if len(prefixo_comum) >= 3:
        produtos_com_prefixo = sum(1 for codigo in codigos if codigo.startswith(prefixo_comum))
        
        if produtos_com_prefixo >= 3:
            print(f"🔍 PREFIXO COMUM DETECTADO: '{prefixo_comum}' em {produtos_com_prefixo} produtos")
            
            # Remover prefixo de todos os produtos
            for produto in produtos:
                codigo_atual = produto.get('codigo', '').strip()
                if codigo_atual.startswith(prefixo_comum):
                    codigo_novo = codigo_atual[len(prefixo_comum):]
                    if codigo_novo:  # Só altera se sobrar algo
                        produto['codigo'] = codigo_novo
                        print(f"📝 Código '{codigo_atual}' → '{codigo_novo}'")
    
    return produtos


def encontrar_prefixo_comum(codigos: list) -> str:
    """
    🔍 ENCONTRAR PREFIXO COMUM
    
    Encontra o maior prefixo comum entre uma lista de códigos.
    
    PARÂMETROS:
    codigos (list): Lista de strings com códigos
    
    RETORNO:
    str: Prefixo comum encontrado
    """
    if not codigos:
        return ""
    
    # Começar com o primeiro código
    prefixo = codigos[0]
    
    # Comparar com todos os outros
    for codigo in codigos[1:]:
        # Reduzir prefixo até encontrar comum
        while prefixo and not codigo.startswith(prefixo):
            prefixo = prefixo[:-1]
        
        if not prefixo:
            break
    
    return prefixo
