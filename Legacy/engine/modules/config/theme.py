"""
🎨 TEMA VISUAL - CORES E FONTES
===============================

Sistema de cores inspirado no Telegram com tema vermelho carmesim.
Hierarquia tipográfica baseada na Segoe UI para máxima legibilidade.
"""

# ===================================================================
# SISTEMA DE CORES - TEMA CARMESIM
# ===================================================================

TELEGRAM_COLORS = {
    # CORES PRINCIPAIS - Tons profissionais de cinza
    'primary': '#374151',        # Cinza escuro (Gray 700) para header/botões principais
    'primary_dark': '#1F2937',   # Cinza ainda mais escuro (Gray 800)
    'secondary': '#6B7280',      # Cinza médio (Gray 500/600) para botões secundários

    # CORES NEUTRAS - Fundo e texto
    'white': '#FFFFFF',          # Fundo principal dos painéis
    'light_gray': '#F3F4F6',     # Fundo da aplicação (Gray 100)
    'medium_gray': '#9CA3AF',    # Texto/elementos secundários (Gray 400)
    'dark_gray': '#111827',      # Texto principal escuro (Gray 900)

    # CORES DE STATUS - Feedback visual (tons mais suaves)
    'success': '#34D399',        # Verde suave (Emerald 400)
    'error':   '#F87171',        # Vermelho suave (Red 400)
    'warning': '#FBBF24',        # Amarelo suave (Amber 400)
    'info':    '#60A5FA',        # Azul suave (Blue 400)

    # CORES DE TEXTO - Hierarquia tipográfica
    'text': '#111827',           # Texto principal (Gray 900)
    'text_light': '#6B7280'      # Texto secundário (Gray 500)
}

# ===================================================================
# SISTEMA DE FONTES - HIERARQUIA TIPOGRÁFICA
# ===================================================================

TELEGRAM_FONTS = {
    'title': ('Segoe UI', 14, 'bold'),      # Títulos principais dos painéis
    'subtitle': ('Segoe UI', 12, 'bold'),   # Subtítulos e seções
    'body': ('Segoe UI', 10),               # Texto normal dos formulários
    'body_bold': ('Segoe UI', 10, 'bold'),  # Labels dos campos
    'small': ('Segoe UI', 9),               # Texto secundário e ajuda
    'button': ('Segoe UI', 10, 'bold')      # Texto dos botões
}
