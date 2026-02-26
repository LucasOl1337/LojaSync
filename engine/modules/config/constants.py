"""
🔧 CONSTANTES DO SISTEMA
========================

Todas as constantes globais usadas no Super Cadastrador.
"""

# Informações da aplicação
APP_NAME = "LojaSync"
APP_VERSION = "1.0 - Carmesim Edition"
APP_DESCRIPTION = "Sistema avançado de automação para cadastro de produtos no ByteEmpresa"

# Geometria padrão das janelas
DEFAULT_GEOMETRY = "1600x720"
LOG_WINDOW_GEOMETRY = "900x500+400+150"
CALIBRATION_WINDOW_GEOMETRY = "800x400+400+200"
MARCA_WINDOW_GEOMETRY = "500x300+500+250"
MARGEM_WINDOW_GEOMETRY = "600x600+600+200"

# Configurações de ícone
# Importante: no executável (Release), os Assets ficam em Release/Assets/
# Portanto usamos caminho relativo à base da aplicação (get_app_base_dir())
# sem subir pastas. Veja main_gui._setup_window para a resolução.
ICON_FILE = "Assets/katarina_icon.ico"

# Categorias disponíveis
CATEGORIAS_DISPONIVEIS = ["Masculino", "Feminino", "Infantil", "Acessorios"]

# Mapeamento de categorias para letras do sistema
CATEGORIA_PARA_LETRA = {
    "Masculino": "m",
    "Feminino": "f", 
    "Infantil": "i",
    "Acessorios": "a"
}

# Marcas padrão
MARCAS_PADRAO = ["OGOCHI", "MALWEE", "BLACK ", "REVANCHE", "COQ"]

# Margem padrão (206% = 2.06)
MARGEM_PADRAO = 2.06

# Delays para automação (em segundos)
DELAY_CLICK = 0.1
DELAY_TAB = 0.05
DELAY_DIGITACAO = 0.01
DELAY_ENTRE_TELAS = 0
DELAY_ENTRE_PRODUTOS = 0

# Encodings para leitura de arquivos
ENCODINGS_SUPORTADOS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

# Extensões de arquivo suportadas
EXTENSOES_ROMANEIO = [
    ("Arquivos de Romaneio", "*.txt;*.pdf"),
    ("Arquivos de Texto", "*.txt"),
    ("Arquivos PDF", "*.pdf"),
    ("Todos os Arquivos", "*.*")
]

# Sistema de Tipagem
TIPAGENS_DISPONIVEIS = {
    "padrao": {"nome": "Padrão", "cor": "#6C757D", "cor_hover": "#5A6268"},
    "masculino": {"nome": "Masculino", "cor": "#007BFF", "cor_hover": "#0056B3"},
    "feminino": {"nome": "Feminino", "cor": "#E91E63", "cor_hover": "#C2185B"},
    "infantil": {"nome": "Infantil", "cor": "#28A745", "cor_hover": "#1E7E34"},
    "acessorios": {"nome": "Acessórios", "cor": "#FFC107", "cor_hover": "#E0A800"}
}

TIPAGEM_PADRAO = "padrao"

# Marcas específicas por tipagem
MARCAS_POR_TIPAGEM = {
    'masculino': ['OGOCHI', 'REVANCHE'],
    'feminino': ['MALWEE', 'BLACK', 'REVANCHE', 'COQ', 'DF', 'DETOX'],
    'infantil': ['MALWEE', 'OGOCHI'],
    'acessorios': ['PIUKA', 'RAFITTY'],
    'padrao': ['OGOCHI', 'MALWEE', 'BLACK', 'REVANCHE', 'COQ', 'DF', 'DETOX', 'PIUKA', 'RAFITTY']
}
