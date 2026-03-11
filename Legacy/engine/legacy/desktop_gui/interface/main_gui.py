"""
🚀 INTERFACE PRINCIPAL - SUPER CADASTRADOR v1
==============================================

Interface principal modularizada com toda a funcionalidade do sistema.
"""

import json
import re
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime
from pathlib import Path
import threading
import time

# Importações dos módulos
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import (
    APP_NAME, DEFAULT_GEOMETRY, ICON_FILE, 
    CATEGORIAS_DISPONIVEIS, MARGEM_PADRAO,
    TIPAGENS_DISPONIVEIS, TIPAGEM_PADRAO
)
from ..core.file_manager import (
    get_app_base_dir, load_targets, save_entry,
    carregar_marcas_salvas, carregar_margem_padrao, carregar_grades,
    obter_marcas_para_tipagem, adicionar_marca_para_tipagem,
    restore_enviados_last_backup, list_enviados_backups,
    create_enviados_snapshot, undo_enviados_step, redo_enviados_step,
    seed_undo_if_empty
)
from ..core.calculator import calcular_preco_final, gerar_descricao_completa
from ..core.validator import converter_para_caps, validar_campos_obrigatorios
from ..automation.byte_empresa import inserir_produto_mecanico
from .log_window import LogWindow
from .calibration_window import CalibrationWindow
from .marca_window import MarcaWindow
from .margem_window import MargemWindow
from .grade_window import GradeWindow
from .grades_window import GradesWindow
from .settings_window import SettingsWindow
# Qualidade do romaneio
from ..quality.qualidadeNota import avaliar_romaneio
# Parser Manager (SongBird-first)
from ..core.parser_manager import parser_manager


class SuperCadastradorApp:
    """Aplicação principal do Super Cadastrador v1"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.executando_massa = False
        self.produtos_pendentes = []
        # Controle de fluxo de grade sequencial
        self._grade_seq_mode = False
        self._grade_seq_index = None  # type: ignore
        # Modo de ordenação sequencial
        self._ordering_mode = False
        self._pin_next_index = 0
        # Pilha de itens fixados: lista de dicts com iid, original_index, nome_original, badge_num
        self._pinned_stack = []
        # Map para restaurar Código ao desativar ordenação (remove ícone 📌)
        self._orig_codigo_map = {}
        # Cache da LINHA BRUTA do JSONL por iid da Treeview (para persistir ordem com fidelidade)
        self._linhas_json_cache = {}
        # Estado de drag and drop na Treeview
        self._drag_item = None
        self._drag_last_y = 0
        self._drag_target = None
        self._drag_indicator = None  # Frame fino como linha de drop
        self._settings_window = None
        
        # Sistema de Tipagem
        self.tipagem_atual = TIPAGEM_PADRAO
        self.tipagem_buttons = {}  # Dicionário para armazenar os botões de tipagem
        
        self._setup_window()
        self._create_interface()
        self._bind_events()
        self._load_initial_data()
        # Estado do verificador de qualidade (default carrega de config)
        try:
            self.quality_active = bool(self._quality_load_enabled())
        except Exception:
            self.quality_active = True

    # ====== Qualidade: persistência do toggle ======
    def _quality_config_path(self) -> Path:
        try:
            return get_app_base_dir() / "data" / "config_quality.json"
        except Exception:
            return Path("data") / "config_quality.json"

    def _quality_load_enabled(self) -> bool:
        try:
            cfg_path = self._quality_config_path()
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
                return bool(data.get("enabled", True))
        except Exception:
            pass
        return True

    def _quality_save_enabled(self, enabled: bool) -> None:
        try:
            cfg_path = self._quality_config_path()
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if cfg_path.exists():
                try:
                    data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
                except Exception:
                    data = {}
            data["enabled"] = bool(enabled)
            cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _format_num_for_ui(self, value):
        """Formata números para UI: remove decimais se forem zero (ex.: 5,0000 -> 5).
        Mantém outros valores como estão (ex.: 5,699999 permanece como digitado).
        Aceita valores com vírgula ou ponto como separador decimal.
        """
        try:
            if value is None:
                return ""
            s = str(value).strip()
            if not s:
                return s
            # Normalizar para float usando ponto como separador decimal
            s_norm = s.replace(',', '.')
            f = float(s_norm)
            if abs(f - round(f)) < 1e-9:
                # Inteiro: exibir sem casas decimais
                return str(int(round(f)))
            # Não-inteiro: manter texto original
            return s
        except Exception:
            return str(value) if value is not None else ""
    
    def _setup_window(self):
        """Configuração da janela principal"""
        self.root.title(APP_NAME)
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.configure(bg=TELEGRAM_COLORS['light_gray'])

        # Centralizar janela na tela com base na geometria padrão
        try:
            self.root.update_idletasks()
            # Extrai largura e altura da string DEFAULT_GEOMETRY (ex.: "1600x720")
            geo = DEFAULT_GEOMETRY.split("+")[0]
            width_str, height_str = geo.split("x")
            width = int(width_str)
            height = int(height_str)
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            pos_x = max((screen_w // 2) - (width // 2), 0)
            pos_y = max((screen_h // 2) - (height // 2), 0)
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except Exception:
            # Em caso de falha, mantém apenas DEFAULT_GEOMETRY
            pass
        
        # Configurar ícone
        try:
            icon_path = get_app_base_dir() / ICON_FILE
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                print("DEBUG: Ícone não encontrado, tentando caminho relativo...")
                self.root.iconbitmap(ICON_FILE)
        except Exception as e:
            print(f"DEBUG: Erro ao carregar ícone: {e}")
        
        # Configurar grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
    
    def _create_interface(self):
        """Cria toda a interface do usuário"""
        self._create_header()
        self._create_left_panel()
        self._create_right_panel()
    
    def _bind_events(self):
        """Registra bindings globais e de campos.
        Mantém a lógica de normalização e atalhos de teclado.
        """
        try:
            # Normalização de entradas numéricas
            if hasattr(self, 'ent_quantidade'):
                self.ent_quantidade.bind('<KeyRelease>', lambda e: converter_para_caps(self.ent_quantidade))
            if hasattr(self, 'ent_preco'):
                self.ent_preco.bind('<KeyRelease>', lambda e: converter_para_caps(self.ent_preco))
            # Ctrl+Z: desfazer (restaurar último backup de enviados)
            self.root.bind('<Control-z>', self._on_ctrl_z_undo)
            # Ctrl+Y: refazer (restaurar próximo snapshot)
            self.root.bind('<Control-y>', self._on_ctrl_y_redo)
        except Exception:
            pass
    
    def _create_header(self):
        """Cria o header principal"""
        header_frame = tk.Frame(self.root, bg=TELEGRAM_COLORS['primary'], height=70)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_propagate(False)
        
        header_title = tk.Label(
            header_frame, 
            text=APP_NAME,
            font=('Segoe UI', 18, 'bold'), 
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        header_title.pack(side=tk.LEFT, padx=12)
        
        # Botão de configurações (engrenagem)
        try:
            btn_cfg = tk.Button(
                header_frame,
                text="⚙️",
                command=self.abrir_configuracoes,
                bg=TELEGRAM_COLORS['primary'],
                fg=TELEGRAM_COLORS['white'],
                relief='flat',
                font=('Segoe UI', 14, 'bold'),
                padx=10, pady=6,
                cursor='hand2'
            )
            btn_cfg.pack(side=tk.RIGHT, padx=12)
        except Exception:
            pass
    
    def _create_left_panel(self):
        """Cria o painel esquerdo - formulário"""
        left_frame = tk.Frame(self.root, bg=TELEGRAM_COLORS['white'], relief="flat", bd=0)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 7), pady=15)
        left_frame.grid_columnconfigure(0, weight=0)
        left_frame.grid_columnconfigure(1, weight=1)
        left_frame.grid_columnconfigure(2, weight=0)
        left_frame.grid_columnconfigure(3, weight=0)
        left_frame.grid_columnconfigure(4, weight=0)
        
        # Título do painel
        titulo_esquerdo = tk.Label(
            left_frame, 
            text="📝 CADASTRO DE PRODUTOS", 
            font=TELEGRAM_FONTS['title'], 
            fg=TELEGRAM_COLORS['primary'],
            bg=TELEGRAM_COLORS['white']
        )
        titulo_esquerdo.grid(row=0, column=0, columnspan=5, pady=(15, 25))
        
        # Campos do formulário
        self._create_form_fields(left_frame)
        
        # Botões principais
        self._create_main_buttons(left_frame)
        
        # Status e controles
        self._create_status_controls(left_frame)

        # Rodapé de totais (canto inferior esquerdo)
        self._create_totais_footer(left_frame)
        
        # Seletor de tipagem (abaixo dos totais)
        self._create_tipagem_selector(left_frame)
    
    def _create_form_fields(self, parent):
        """Cria os campos do formulário"""
        # Nome
        tk.Label(parent, text="Nome:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=1, column=0, sticky="w", padx=(15, 10), pady=5)
        self.ent_nome = tk.Entry(parent, width=35, font=TELEGRAM_FONTS['body'],
                               bg=TELEGRAM_COLORS['white'], relief='solid', bd=1)
        self.ent_nome.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Código
        tk.Label(parent, text="Código:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=2, column=0, sticky="w", padx=(15, 10), pady=5)
        self.ent_codigo = tk.Entry(parent, width=35, font=TELEGRAM_FONTS['body'],
                                 bg=TELEGRAM_COLORS['white'], relief='solid', bd=1)
        self.ent_codigo.grid(row=2, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Quantidade
        tk.Label(parent, text="Quantidade:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=3, column=0, sticky="w", padx=(15, 10), pady=5)
        self.ent_quantidade = tk.Entry(parent, width=35, font=TELEGRAM_FONTS['body'],
                                     bg=TELEGRAM_COLORS['white'], relief='solid', bd=1)
        self.ent_quantidade.grid(row=3, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Preço
        tk.Label(parent, text="Preço:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=4, column=0, sticky="w", padx=(15, 10), pady=5)
        self.ent_preco = tk.Entry(parent, width=35, font=TELEGRAM_FONTS['body'],
                                bg=TELEGRAM_COLORS['white'], relief='solid', bd=1)
        self.ent_preco.grid(row=4, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Categoria
        tk.Label(parent, text="Categoria:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=5, column=0, sticky="w", padx=(15, 10), pady=5)
        self.categoria_var = tk.StringVar(value="Masculino")
        self.categoria_cb = ttk.Combobox(
            parent, textvariable=self.categoria_var,
            values=CATEGORIAS_DISPONIVEIS,
            state="readonly", width=32, font=TELEGRAM_FONTS['body']
        )
        self.categoria_cb.grid(row=5, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Marca
        tk.Label(parent, text="Marca:", font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']).grid(
                row=6, column=0, sticky="w", padx=(15, 10), pady=5)
        self.marca_var = tk.StringVar(value="OGOCHI")
        self.marca_cb = ttk.Combobox(
            parent, textvariable=self.marca_var,
            values=carregar_marcas_salvas(),
            state="readonly", width=32, font=TELEGRAM_FONTS['body']
        )
        self.marca_cb.grid(row=6, column=1, sticky="ew", padx=(0, 20), pady=5)
        
        # Botões marca e margem
        self._create_marca_margem_buttons(parent)
    
    def _create_marca_margem_buttons(self, parent):
        """Cria botões de marca e margem"""
        # Usar um frame dedicado na coluna 1 para manter os botões lado a lado
        botoes_frame = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
        botoes_frame.grid(row=7, column=1, columnspan=3, sticky="w", pady=5)

        btn_nova_marca = tk.Button(
            botoes_frame, text="➕ Nova Marca",
            command=self.abrir_janela_nova_marca,
            bg=TELEGRAM_COLORS['secondary'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat',
            width=12, height=1, padx=5, pady=2
        )
        btn_nova_marca.pack(side=tk.LEFT, padx=(0, 6))

        btn_margem = tk.Button(
            botoes_frame, text="💰 Margem",
            command=self.abrir_janela_margem,
            bg=TELEGRAM_COLORS['warning'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat',
            width=12, height=1, padx=5, pady=2
        )
        btn_margem.pack(side=tk.LEFT, padx=(0, 6))

        margem_atual = carregar_margem_padrao()
        percentual_atual = int((margem_atual - 1) * 100)
        self.label_margem = tk.Label(
            botoes_frame, text=f"Margem: {percentual_atual}%",
            font=TELEGRAM_FONTS['small'], fg=TELEGRAM_COLORS['warning'],
            bg=TELEGRAM_COLORS['white']
        )
        self.label_margem.pack(side=tk.LEFT, padx=(0, 6))

        # Botão aplicar categoria atual para todos
        btn_aplicar_categoria = tk.Button(
            botoes_frame, text="📂 Aplicar Categoria",
            command=self.aplicar_categoria_todos,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat',
            width=15, height=1, padx=5, pady=2
        )
        btn_aplicar_categoria.pack(side=tk.LEFT, padx=(0, 6))

        # Botão aplicar marca atual para todos
        btn_aplicar_marca = tk.Button(
            botoes_frame, text="🏷️ Aplicar Marca",
            command=self.aplicar_marca_todos,
            bg=TELEGRAM_COLORS['secondary'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat',
            width=15, height=1, padx=5, pady=2
        )
        btn_aplicar_marca.pack(side=tk.LEFT, padx=(0, 6))
    
    def _create_main_buttons(self, parent):
        """Cria os botões principais"""
        btn_frame = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
        # Empurra o bloco de botões principais para baixo (linha 8) para abrir espaço aos botões de marca/margem na linha 7
        btn_frame.grid(row=8, column=0, columnspan=5, pady=25)
        
        btn_salvar = tk.Button(
            btn_frame, text="💾 Salvar Dados", command=self.salvar_dados, 
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat',
            width=15, height=2, padx=10, pady=5
        )
        btn_salvar.pack(side=tk.LEFT, padx=5)
        
        # Removido: botão "Enviar p/ Sistema" (não utilizado)
        
        btn_calibrar = tk.Button(
            btn_frame, text="🎯 Calibrar Sistema", 
            command=self.abrir_janela_calibracao,
            bg=TELEGRAM_COLORS['warning'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat',
            width=15, height=2, padx=10, pady=5
        )
        btn_calibrar.pack(side=tk.LEFT, padx=5)
        
        btn_romaneio = tk.Button(
            btn_frame, text="🧾 Importar Romaneio", 
            command=self.importar_romaneio,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat',
            width=18, height=2, padx=10, pady=5, wraplength=200
        )
        btn_romaneio.pack(side=tk.LEFT, padx=5)
    
    def _create_status_controls(self, parent):
        """Cria controles de status"""
        # Removido: Checkbox "Envio automático após salvar" (não utilizado)
        # Mantém a variável para compatibilidade com a lógica existente
        self.auto_send_var = tk.BooleanVar(value=False)

        # Status
        self.status_var = tk.StringVar(value="✅ Pronto para cadastrar produtos")
        self.status_label = tk.Label(
            parent, textvariable=self.status_var, fg=TELEGRAM_COLORS['success'], 
            font=TELEGRAM_FONTS['body'], bg=TELEGRAM_COLORS['white']
        )
        # Ajusta a linha do status para compensar a remoção do checkbox
        self.status_label.grid(row=9, column=0, columnspan=3, sticky="w", padx=15, pady=10)
    
    def _create_right_panel(self):
        """Cria o painel direito - lista e execução"""
        right_frame = tk.Frame(self.root, bg=TELEGRAM_COLORS['white'], relief="flat", bd=0)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(7, 15), pady=15)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)
        
        # Título do painel
        titulo_direito = tk.Label(
            right_frame, text="📊 PRODUTOS CADASTRADOS", 
            font=TELEGRAM_FONTS['title'], fg=TELEGRAM_COLORS['primary'],
            bg=TELEGRAM_COLORS['white']
        )
        titulo_direito.grid(row=0, column=0, pady=(15, 20))
        
        # Controles de execução em massa
        self._create_mass_execution_controls(right_frame)
        
        # Lista de produtos
        self._create_product_list(right_frame)
        
        # Botões de controle da lista
        self._create_list_controls(right_frame)
        
        # Status execução massa
        self.status_massa_var = tk.StringVar(value="⏳ Aguardando produtos para execução em massa")
        status_massa_label = tk.Label(
            right_frame, textvariable=self.status_massa_var, 
            fg=TELEGRAM_COLORS['info'], font=TELEGRAM_FONTS['body'],
            bg=TELEGRAM_COLORS['white']
        )
        status_massa_label.grid(row=4, column=0, pady=10)

    def _create_totais_footer(self, parent):
        """Cria o painel de totais (qtd peças, custo total, venda total) no canto inferior esquerdo."""
        try:
            footer = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
            # Posicionar após a linha de status (que está em row=9). Usamos row=10.
            footer.grid(row=10, column=0, columnspan=5, sticky="w", padx=15, pady=(10, 0))

            self.tot_qtd_var = tk.StringVar(value="Quantidade de peças: 0")
            self.tot_custo_var = tk.StringVar(value="Custo total: 0")
            self.tot_venda_var = tk.StringVar(value="Venda total: 0")

            lbl_qtd = tk.Label(footer, textvariable=self.tot_qtd_var, font=TELEGRAM_FONTS['body'],
                               fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white'])
            lbl_qtd.pack(side=tk.LEFT)

            sep1 = tk.Label(footer, text="  |  ", font=TELEGRAM_FONTS['body'],
                            fg=TELEGRAM_COLORS['text_light'], bg=TELEGRAM_COLORS['white'])
            sep1.pack(side=tk.LEFT)

            lbl_custo = tk.Label(footer, textvariable=self.tot_custo_var, font=TELEGRAM_FONTS['body'],
                                 fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white'])
            lbl_custo.pack(side=tk.LEFT)

            sep2 = tk.Label(footer, text="  |  ", font=TELEGRAM_FONTS['body'],
                            fg=TELEGRAM_COLORS['text_light'], bg=TELEGRAM_COLORS['white'])
            sep2.pack(side=tk.LEFT)

            lbl_venda = tk.Label(footer, textvariable=self.tot_venda_var, font=TELEGRAM_FONTS['body'],
                                 fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white'])
            lbl_venda.pack(side=tk.LEFT)

            # Inicializar com os totais atuais (se a lista já estiver carregada)
            self.atualizar_totais()
        except Exception as e:
            print(f"Erro ao criar rodape de totais: {e}")

    def _parse_num(self, s):
        """Converte string numérica com vírgula ou ponto para float. Retorna 0.0 se inválido."""
        try:
            if s is None:
                return 0.0
            txt = str(s).strip()
            if not txt:
                return 0.0
            return float(txt.replace(',', '.'))
        except Exception:
            return 0.0

    def atualizar_totais(self):
        """Recalcula e atualiza os totais com base na Treeview atual."""
        try:
            if not hasattr(self, 'tree'):
                return
            soma_qtd = 0.0
            soma_custo = 0.0
            soma_venda = 0.0
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, 'values')
                if not vals:
                    continue
                qtd = self._parse_num(vals[4]) if len(vals) > 4 else 0.0
                custo_unit = self._parse_num(vals[5]) if len(vals) > 5 else 0.0
                venda_unit = self._parse_num(vals[6]) if len(vals) > 6 else 0.0
                soma_qtd += qtd
                soma_custo += qtd * custo_unit
                soma_venda += qtd * venda_unit

            if hasattr(self, 'tot_qtd_var'):
                self.tot_qtd_var.set(f"Quantidade de peças: {self._format_num_for_ui(soma_qtd)}")
            if hasattr(self, 'tot_custo_var'):
                self.tot_custo_var.set(f"Custo total: {self._format_num_for_ui(soma_custo)}")
            if hasattr(self, 'tot_venda_var'):
                self.tot_venda_var.set(f"Venda total: {self._format_num_for_ui(soma_venda)}")
        except Exception as e:
            print(f"Erro ao atualizar totais: {e}")
    
    def _create_tipagem_selector(self, parent):
        """Cria o seletor de tipagem no canto inferior esquerdo."""
        try:
            tipagem_frame = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
            # Posicionar após o rodapé de totais (que está em row=10). Usamos row=11.
            tipagem_frame.grid(row=11, column=0, columnspan=5, sticky="w", padx=15, pady=(15, 0))

            # Título do seletor
            titulo_tipagem = tk.Label(
                tipagem_frame, 
                text="🎯 TIPAGEM:", 
                font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'], 
                bg=TELEGRAM_COLORS['white']
            )
            titulo_tipagem.pack(side=tk.LEFT, padx=(0, 10))

            # Container para os botões
            botoes_container = tk.Frame(tipagem_frame, bg=TELEGRAM_COLORS['white'])
            botoes_container.pack(side=tk.LEFT)

            # Criar botões para cada tipagem
            for tipagem_key, tipagem_info in TIPAGENS_DISPONIVEIS.items():
                btn = tk.Button(
                    botoes_container,
                    text=tipagem_info['nome'],
                    command=lambda t=tipagem_key: self._on_tipagem_changed(t),
                    font=TELEGRAM_FONTS['small'],
                    relief='flat',
                    width=10,
                    height=1,
                    padx=8,
                    pady=4
                )
                btn.pack(side=tk.LEFT, padx=2)
                
                # Armazenar referência do botão
                self.tipagem_buttons[tipagem_key] = btn
            
            # Aplicar estilo inicial (destacar tipagem padrão)
            self._update_tipagem_buttons_style()
            
        except Exception as e:
            print(f"Erro ao criar seletor de tipagem: {e}")
    
    def _on_tipagem_changed(self, nova_tipagem):
        """Callback executado quando uma tipagem é selecionada."""
        try:
            print(f"Tipagem alterada: {self.tipagem_atual} -> {nova_tipagem}")
            
            # Atualizar estado interno
            self.tipagem_atual = nova_tipagem
            
            # Atualizar visual dos botões
            self._update_tipagem_buttons_style()
            
            # Aplicar efeitos da tipagem (placeholder para futura implementação)
            self._aplicar_efeitos_tipagem()
            
            # Feedback visual no status
            tipagem_nome = TIPAGENS_DISPONIVEIS[nova_tipagem]['nome']
            self.status_var.set(f"🎯 Tipagem alterada para: {tipagem_nome}")
            self.status_label.config(fg=TELEGRAM_COLORS['info'])
            
        except Exception as e:
            print(f"Erro ao alterar tipagem: {e}")
    
    def _update_tipagem_buttons_style(self):
        """Atualiza o estilo visual dos botões de tipagem."""
        try:
            for tipagem_key, btn in self.tipagem_buttons.items():
                tipagem_info = TIPAGENS_DISPONIVEIS[tipagem_key]
                
                if tipagem_key == self.tipagem_atual:
                    # Botão ativo - cor da tipagem
                    btn.config(
                        bg=tipagem_info['cor'],
                        fg=TELEGRAM_COLORS['white'],
                        relief='solid',
                        bd=2
                    )
                else:
                    # Botão inativo - cor neutra
                    btn.config(
                        bg=TELEGRAM_COLORS['light_gray'],
                        fg=TELEGRAM_COLORS['text'],
                        relief='flat',
                        bd=1
                    )
        except Exception as e:
            print(f"Erro ao atualizar estilo dos botoes: {e}")
    
    def _aplicar_efeitos_tipagem(self):
        """Aplica os efeitos específicos da tipagem selecionada."""
        try:
            tipagem_nome = TIPAGENS_DISPONIVEIS[self.tipagem_atual]['nome']
            print(f"Aplicando efeitos da tipagem: {tipagem_nome}")
            
            # Atualizar marcas disponíveis baseado na tipagem
            self._atualizar_marcas_por_tipagem()
            
            # TODO: Implementar outros comportamentos específicos por tipagem
            # - Alterar categoria padrão
            # - Aplicar margem específica
            # - Modificar validações de campos
            
        except Exception as e:
            print(f"Erro ao aplicar efeitos da tipagem: {e}")
    
    def _atualizar_marcas_por_tipagem(self):
        """Atualiza o combobox de marcas baseado na tipagem selecionada."""
        try:
            # Obter marcas para a tipagem atual
            marcas_tipagem = obter_marcas_para_tipagem(self.tipagem_atual)
            
            # Atualizar valores do combobox
            if hasattr(self, 'marca_cb'):
                valor_atual = self.marca_cb.get()
                self.marca_cb['values'] = marcas_tipagem
                
                # Manter seleção atual se ainda estiver disponível
                if valor_atual in marcas_tipagem:
                    self.marca_cb.set(valor_atual)
                else:
                    # Limpar seleção se marca não estiver disponível na nova tipagem
                    self.marca_cb.set('')
                
                print(f"Marcas atualizadas para tipagem {self.tipagem_atual}: {len(marcas_tipagem)} marcas disponiveis")
            
        except Exception as e:
            print(f"Erro ao atualizar marcas por tipagem: {e}")
    
    def _create_mass_execution_controls(self, parent):
        """Cria controles de execução em massa"""
        controle_frame = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
        controle_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Botão executar massa
        self.btn_executar_massa = tk.Button(
            controle_frame, text="🔄 EXECUTAR CADASTRO EM MASSA", 
            command=self.executar_cadastro_em_massa,
            bg=TELEGRAM_COLORS['primary'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat',
            width=30, height=2, padx=10, pady=5
        )
        self.btn_executar_massa.pack(side=tk.LEFT, padx=5)
        
        # Botão parar
        self.btn_parar = tk.Button(
            controle_frame, text="⏹️ PARAR", 
            command=self.parar_execucao_massa,
            bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat',
            width=10, height=2, state=tk.DISABLED, padx=5, pady=5
        )
        self.btn_parar.pack(side=tk.LEFT, padx=5)
        
        # Barra de progresso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            controle_frame, variable=self.progress_var, 
            maximum=100, length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=10)
        
        # Label progresso
        self.progress_label = tk.Label(
            controle_frame, text="0/0", font=TELEGRAM_FONTS['body'],
            fg=TELEGRAM_COLORS['text'], bg=TELEGRAM_COLORS['white']
        )
        self.progress_label.pack(side=tk.LEFT)

    def executar_cadastro_em_massa(self):
        """Executa cadastro em massa delegando ao módulo executarCadastro."""
        if getattr(self, 'executando_massa', False):
            return
        # Import lazy para tolerar caminhos de pacote distintos
        try:
            # Tentativa 1: import absoluto pelo nome do módulo na raiz do projeto
            from executarCadastro import (
                executar_em_massa, carregar_produtos_enviados
            )
        except Exception:
            try:
                # Tentativa 2: import relativo (pode falhar se 'Engine' não for pacote)
                from ...executarCadastro import (
                    executar_em_massa, carregar_produtos_enviados
                )  # type: ignore
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível carregar o executor de cadastro: {e}")
                return

        # Carregar produtos do arquivo padrão
        try:
            produtos = carregar_produtos_enviados()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler produtos: {e}")
            return

        if not produtos:
            messagebox.showwarning("Atenção", "Nenhum produto encontrado!")
            return

        total = len(produtos)
        # Preparar UI
        self.executando_massa = True
        try:
            self._cancel_event_massa = threading.Event()
        except Exception:
            self._cancel_event_massa = None  # type: ignore
        self.btn_executar_massa.config(state=tk.DISABLED)
        self.btn_parar.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text=f"0/{total}")
        self.status_massa_var.set("🚀 Iniciando execução em massa...")

        # Callbacks thread-safe (usar after para tocar na UI)
        def cb_status(msg: str):
            try:
                self.root.after(0, lambda: self.status_massa_var.set(msg))
            except Exception:
                pass

        def cb_progress(atual: int, tot: int):
            try:
                pct = 0 if tot == 0 else (atual / tot) * 100.0
                self.root.after(0, lambda: (
                    self.progress_var.set(pct),
                    self.progress_label.config(text=f"{atual}/{tot}")
                ))
            except Exception:
                pass

        def cb_item_result(prod: dict, ok: bool, err: object):
            # Pode-se estender para marcar visualmente itens no futuro
            pass

        def cb_finish(sucessos: int, falhas: int, tot: int):
            def _done():
                self.executando_massa = False
                self.btn_executar_massa.config(state=tk.NORMAL)
                self.btn_parar.config(state=tk.DISABLED)
                try:
                    self._cancel_event_massa = None  # type: ignore
                except Exception:
                    pass
                if sucessos > 0 or tot == 0:
                    self.status_massa_var.set(f"🎉 Concluído! Sucessos: {sucessos}, Falhas: {falhas}")
                    messagebox.showinfo(
                        "Execução Concluída",
                        f"Processamento finalizado!\n\n✅ Sucessos: {sucessos}\n❌ Falhas: {falhas}\n📊 Total: {tot}"
                    )
                else:
                    self.status_massa_var.set("❌ Execução falhou completamente")
            self.root.after(0, _done)

        # Worker thread
        def worker():
            try:
                executar_em_massa(
                    produtos,
                    ativar_janela_primeiro=True,
                    cancel_event=getattr(self, '_cancel_event_massa', None),
                    on_status=cb_status,
                    on_progress=cb_progress,
                    on_item_result=cb_item_result,
                    on_finish=cb_finish,
                )
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro na execução: {e}"))
                self.root.after(0, lambda: cb_finish(0, 0, total))

        th = threading.Thread(target=worker, daemon=True)
        th.start()

    def _create_product_list(self, parent):
        """Cria a lista de produtos com dica de Ctrl+arrastar para reordenar."""
        container = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
        container.grid(row=2, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        # Barra superior com dica e botão de formatação
        topbar = tk.Frame(container, bg=TELEGRAM_COLORS['white'])
        topbar.grid(row=0, column=0, sticky="ew")

        hint = tk.Label(
            topbar,
            text="💡 Dica: segure Ctrl e arraste uma linha para reordenar a lista (ordem define a execução).",
            font=TELEGRAM_FONTS['small'],
            fg=TELEGRAM_COLORS['info'],
            bg=TELEGRAM_COLORS['white']
        )
        hint.pack(side=tk.LEFT, pady=(0, 6))

        btn_formatar_codigos = tk.Button(
            topbar,
            text="🛠 Formatar Códigos",
            command=self.abrir_janela_formatar_codigos,
            bg=TELEGRAM_COLORS['secondary'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat', padx=8, pady=2
        )
        btn_formatar_codigos.pack(side=tk.RIGHT)

        # Único botão: ativar/desativar ordenação, ao lado de "Formatar Códigos"
        ordenar_frame = tk.Frame(topbar, bg=TELEGRAM_COLORS['white'])
        ordenar_frame.pack(side=tk.RIGHT, padx=6)

        self.btn_toggle_ordering = tk.Button(
            ordenar_frame,
            text="🧭 Ativar Ordenação",
            command=self._toggle_ordering_mode_click,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat', padx=10, pady=2
        )
        self.btn_toggle_ordering.pack(side=tk.RIGHT, padx=(0,6))

        # Pequeno indicador de progresso n/N
        self.ordering_progress_var = tk.StringVar(value="0/0")
        self.lbl_ordering_prog = tk.Label(
            ordenar_frame,
            textvariable=self.ordering_progress_var,
            font=TELEGRAM_FONTS['small'],
            fg=TELEGRAM_COLORS['text_light'],
            bg=TELEGRAM_COLORS['white']
        )
        self.lbl_ordering_prog.pack(side=tk.RIGHT)

        # Qualidade: Toggle Ativo/Inativo e contadores
        qual_frame = tk.Frame(topbar, bg=TELEGRAM_COLORS['white'])
        qual_frame.pack(side=tk.RIGHT, padx=6)
        self._quality_counts_var = tk.StringVar(value="Qualidade: --")
        self.btn_quality_toggle = tk.Button(
            qual_frame,
            text="Qualidade: Ativo" if getattr(self, 'quality_active', False) else "Qualidade: Inativo",
            command=self._on_quality_toggle_click,
            bg=TELEGRAM_COLORS['primary'] if getattr(self, 'quality_active', False) else TELEGRAM_COLORS['light_gray'],
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['small'], relief='flat', padx=10, pady=2
        )
        self.btn_quality_toggle.pack(side=tk.LEFT, padx=(0,6))
        self.lbl_quality_counts = tk.Label(
            qual_frame,
            textvariable=self._quality_counts_var,
            font=TELEGRAM_FONTS['small'],
            fg=TELEGRAM_COLORS['text_light'],
            bg=TELEGRAM_COLORS['white']
        )
        self.lbl_quality_counts.pack(side=tk.LEFT)

        # Treeview
        columns = ("Hora", "Nome", "Marca", "Código", "Quantidade", "Custo", "Venda", "Categoria")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        # Cabeçalhos
        self.tree.heading("Hora", text="Hora")
        self.tree.heading("Nome", text="Nome")
        self.tree.heading("Marca", text="Marca")
        self.tree.heading("Código", text="Código")
        self.tree.heading("Quantidade", text="Qtd")
        self.tree.heading("Custo", text="Custo")
        self.tree.heading("Venda", text="Venda")
        self.tree.heading("Categoria", text="Categoria")

        # Larguras
        self.tree.column("Hora", width=70, anchor="center")
        self.tree.column("Nome", width=200)
        self.tree.column("Marca", width=120)
        self.tree.column("Código", width=100, minwidth=90, anchor="center", stretch=False)
        self.tree.column("Quantidade", width=55, minwidth=45, anchor="center", stretch=False)
        self.tree.column("Custo", width=90, anchor="e")
        self.tree.column("Venda", width=90, anchor="e")
        self.tree.column("Categoria", width=120)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        # Tags para destaque de arraste
        try:
            self.tree.tag_configure("drag_target", background="#E8F0FE")  # azul claro
            self.tree.tag_configure("drag_source", background="#FFF5E5")  # laranja claro
        except Exception:
            pass

        # Bindings principais
        self.tree.bind("<Delete>", self.deletar_produto_selecionado)
        self.tree.bind("<KeyPress-Delete>", self.deletar_produto_selecionado)
        self.tree.bind("<Double-1>", self.editar_campo_produto)

        # Drag-and-drop (reordenar com Ctrl)
        self.tree.bind("<ButtonPress-1>", self._on_tree_button_press)
        self.tree.bind("<B1-Motion>", self._on_tree_mouse_move)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_button_release)
        # Clique no ícone 📌 da coluna Código
        self.tree.bind("<Button-1>", self._on_tree_click_pin, add="+")

    def _set_ordering_mode(self, enabled: bool):
        """Configura o modo de ordenação sequencial (on/off)."""
        self._ordering_mode = bool(enabled)
        # Resetar estado ao desligar
        if not self._ordering_mode:
            self._clear_all_badges()
            self._pinned_stack.clear()
            self._pin_next_index = 0
            self.ordering_progress_var.set("0/0")
            # Restaurar coluna Código (remover ícone 📌)
            try:
                if isinstance(self._orig_codigo_map, dict) and self._orig_codigo_map:
                    for iid, codigo in self._orig_codigo_map.items():
                        vals = list(self.tree.item(iid, 'values'))
                        if vals and len(vals) > 3:
                            vals[3] = codigo
                            self.tree.item(iid, values=tuple(vals))
                # Restaurar largura/âncora da coluna Código, se salvo
                if hasattr(self, '_codigo_prev_conf') and isinstance(self._codigo_prev_conf, dict):
                    prev_w = self._codigo_prev_conf.get('width')
                    prev_anchor = self._codigo_prev_conf.get('anchor', 'center')
                    if prev_w:
                        self.tree.column("Código", width=prev_w, anchor=prev_anchor)
            except Exception:
                pass
            self._orig_codigo_map = {}
            # Desabilitar botões e atalhos
            if hasattr(self, 'btn_undo_pin'):
                self.btn_undo_pin.config(state=tk.DISABLED)
            if hasattr(self, 'btn_pin_next'):
                self.btn_pin_next.config(state=tk.DISABLED)
            if hasattr(self, 'btn_reset_pin'):
                self.btn_reset_pin.config(state=tk.DISABLED)
            try:
                self.root.unbind_all('<Control-Return>')
                self.root.unbind_all('<Control-KP_Enter>')
                self.root.unbind_all('<Control-BackSpace>')
                self.root.unbind_all('<Control-r>')
                self.root.unbind_all('<Control-R>')
            except Exception:
                pass
            # Atualizar visual do botão
            if hasattr(self, 'btn_toggle_ordering'):
                self.btn_toggle_ordering.config(text="🧭 Ativar Ordenação", bg=TELEGRAM_COLORS['info'])
            return

        # Ativando
        try:
            total = len(self.tree.get_children())
        except Exception:
            total = 0
        self._pin_next_index = 0
        self._pinned_stack.clear()
        self.ordering_progress_var.set(f"0/{total}")
        if hasattr(self, 'btn_pin_next'):
            self.btn_pin_next.config(state=tk.NORMAL)
        if hasattr(self, 'btn_undo_pin'):
            self.btn_undo_pin.config(state=tk.DISABLED)
        if hasattr(self, 'btn_reset_pin'):
            self.btn_reset_pin.config(state=tk.NORMAL)
        # Atualizar visual do botão (sem atalhos)
        if hasattr(self, 'btn_toggle_ordering'):
            self.btn_toggle_ordering.config(text="✅ Ordenação Ativa", bg=TELEGRAM_COLORS['primary'])
        # Adicionar ícone 📌 na coluna Código para todos
        try:
            self._orig_codigo_map = {}
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, 'values'))
                if not vals or len(vals) < 4:
                    continue
                codigo = str(vals[3])
                self._orig_codigo_map[iid] = codigo
                if not codigo.startswith('📌'):
                    # ícone + padding para alinhar visual e clique
                    vals[3] = f"📌  {codigo}"
                    self.tree.item(iid, values=tuple(vals))
            # Ajustar coluna Código: +30% largura e alinhamento à esquerda
            try:
                cur_w = self.tree.column("Código", option='width')
            except Exception:
                cur_w = 80
            new_w = int(cur_w * 1.3) if isinstance(cur_w, int) else 120
            self._codigo_prev_conf = {
                'width': cur_w,
                'anchor': self.tree.column("Código", option='anchor')
            }
            self.tree.column("Código", width=new_w, minwidth=int(new_w*0.9), anchor='w')
        except Exception:
            pass

    def _toggle_ordering_mode_click(self):
        """Clique do botão único: alterna ON/OFF do modo de ordenação."""
        self._set_ordering_mode(not self._ordering_mode)

    def _pin_next_selected(self):
        """Move o item selecionado para a próxima posição fixa no topo e atualiza badges."""
        if not self._ordering_mode:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Ordenação", "Selecione um item para fixar.")
            return
        iid = sel[0]
        children = list(self.tree.get_children())
        total = len(children)
        # Índice original antes de mover
        try:
            original_index = children.index(iid)
        except ValueError:
            return
        # Mover para a posição _pin_next_index
        try:
            self.tree.move(iid, "", self._pin_next_index)
        except Exception:
            return
        # Registrar na pilha
        valores = list(self.tree.item(iid, 'values'))
        nome_antigo = valores[1] if len(valores) > 1 else ""
        badge_num = self._pin_next_index + 1
        self._pinned_stack.append({
            'iid': iid,
            'original_index': original_index,
            'nome_original': nome_antigo,
            'badge_num': badge_num,
        })
        # Atualizar badge no Nome
        self._apply_badge_to_iid(iid, badge_num)
        # Avançar ponteiro
        self._pin_next_index += 1
        # Atualizar progresso
        self.ordering_progress_var.set(f"{self._pin_next_index}/{total}")
        # Habilitar desfazer
        self.btn_undo_pin.config(state=tk.NORMAL)
        # Persistir ordem
        try:
            self._persist_tree_order_to_file()
        except Exception:
            pass

    def _pin_next_iid(self, iid: str):
        """Pin de um iid específico (usado ao clicar no ícone 📌 da coluna Código)."""
        if not self._ordering_mode:
            return
        children = list(self.tree.get_children())
        total = len(children)
        try:
            original_index = children.index(iid)
        except ValueError:
            return
        try:
            self.tree.move(iid, "", self._pin_next_index)
        except Exception:
            return
        valores = list(self.tree.item(iid, 'values'))
        nome_antigo = valores[1] if len(valores) > 1 else ""
        badge_num = self._pin_next_index + 1
        self._pinned_stack.append({
            'iid': iid,
            'original_index': original_index,
            'nome_original': nome_antigo,
            'badge_num': badge_num,
        })
        self._apply_badge_to_iid(iid, badge_num)
        self._pin_next_index += 1
        self.ordering_progress_var.set(f"{self._pin_next_index}/{total}")
        try:
            self._persist_tree_order_to_file()
        except Exception:
            pass

    def _on_tree_click_pin(self, event):
        """Interpreta clique na coluna Código: se modo ordenação estiver ativo e clicar no início da célula, faz pin do item."""
        if not self._ordering_mode:
            return
        # Qual linha/coluna foi clicada
        rowid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not rowid or col != '#4':  # '#4' é a coluna Código no layout atual
            return
        # Verificar se clicou na área do ícone (esquerda da célula)
        try:
            x, y, w, h = self.tree.bbox(rowid, column=col)
            if event.x - x <= 40:  # área clicável maior (~40px) para facilitar o clique
                self._pin_next_iid(rowid)
                return 'break'
        except Exception:
            # Se não conseguir bbox, considerar clique em qualquer área da coluna
            self._pin_next_iid(rowid)
            return 'break'

    def _undo_last_pin(self):
        """Desfaz o último 'fixar próximo': remove badge e tenta restaurar posição original."""
        if not self._ordering_mode or not self._pinned_stack:
            return
        last = self._pinned_stack.pop()
        iid = last['iid']
        original_index = last.get('original_index', 0)
        nome_original = last.get('nome_original', '')
        # Remover badge (restaurar nome)
        self._set_nome_for_iid(iid, nome_original)
        # Reposicionar próximo ponteiro
        self._pin_next_index = max(self._pin_next_index - 1, 0)
        # Tentar mover de volta para o índice original (ajustado pelo tamanho atual)
        children = list(self.tree.get_children())
        target_index = min(original_index, len(children) - 1)
        try:
            self.tree.move(iid, "", target_index)
        except Exception:
            pass
        # Atualizar progresso
        total = len(self.tree.get_children())
        self.ordering_progress_var.set(f"{self._pin_next_index}/{total}")
        # Desabilitar desfazer se vazio
        if not self._pinned_stack:
            self.btn_undo_pin.config(state=tk.DISABLED)
        # Persistir ordem
        try:
            self._persist_tree_order_to_file()
        except Exception:
            pass

    def _reset_pins(self):
        """Reseta a sequência: remove badges e tenta restaurar posições originais. Se falhar, recarrega lista."""
        if not self._ordering_mode:
            return
        # Remover badges
        for rec in self._pinned_stack:
            self._set_nome_for_iid(rec['iid'], rec.get('nome_original', ''))
        # Restaurar posição aproximada pela ordem original_index
        try:
            # Ordenar por original_index crescente e mover cada um
            for rec in sorted(self._pinned_stack, key=lambda r: r.get('original_index', 0)):
                iid = rec['iid']
                idx = rec.get('original_index', 0)
                children = list(self.tree.get_children())
                target_index = min(idx, len(children) - 1)
                try:
                    self.tree.move(iid, "", target_index)
                except Exception:
                    pass
        except Exception:
            # Fallback: recarregar lista do arquivo
            try:
                self.refresh_lista_produtos()
            except Exception:
                pass
        # Resetar estado
        self._pinned_stack.clear()
        self._pin_next_index = 0
        total = len(self.tree.get_children())
        self.ordering_progress_var.set(f"0/{total}")
        self.btn_undo_pin.config(state=tk.DISABLED)
        # Persistir ordem
        try:
            self._persist_tree_order_to_file()
        except Exception:
            pass

    def _apply_badge_to_iid(self, iid: str, n: int):
        """Prefixa o Nome com '#n ' apenas visualmente."""
        try:
            valores = list(self.tree.item(iid, 'values'))
            if not valores or len(valores) < 2:
                return
            nome = str(valores[1])
            # Remover badge existente e aplicar o novo
            nome = self._remove_badge_prefix(nome)
            nome_novo = f"#{n} {nome}" if n > 0 else nome
            valores[1] = nome_novo
            self.tree.item(iid, values=valores)
        except Exception:
            pass

    def _set_nome_for_iid(self, iid: str, novo_nome: str):
        try:
            valores = list(self.tree.item(iid, 'values'))
            if not valores or len(valores) < 2:
                return
            valores[1] = novo_nome
            self.tree.item(iid, values=valores)
        except Exception:
            pass

    def _remove_badge_prefix(self, nome: str) -> str:
        try:
            s = str(nome)
            # Formato esperado: "#<num> <resto>"
            if s.startswith('#'):
                parts = s.split(' ', 1)
                if len(parts) == 2 and parts[0][1:].isdigit():
                    return parts[1]
            return s
        except Exception:
            return str(nome)

    def _clear_all_badges(self):
        try:
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, 'values'))
                if vals and len(vals) > 1:
                    vals[1] = self._remove_badge_prefix(vals[1])
                    self.tree.item(iid, values=tuple(vals))
        except Exception:
            pass

    def abrir_janela_formatar_codigos(self):
        """Abre a janela de formatação de códigos com opções inteligentes."""
        win = tk.Toplevel(self.root)
        win.title("Formatar Códigos")
        win.configure(bg=TELEGRAM_COLORS['white'])
        win.geometry("480x280")
        win.grab_set()

        frm = tk.Frame(win, bg=TELEGRAM_COLORS['white'])
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        # Opções (apenas as solicitadas)
        tk.Label(frm, text="Opções de formatação (aplicadas a TODOS os itens):", bg=TELEGRAM_COLORS['white'], font=TELEGRAM_FONTS['body_bold']).pack(anchor="w")

        opt_rm_prefixo5 = tk.BooleanVar(value=True)
        tk.Checkbutton(frm, text="Remover prefixo de 5 dígitos repetido (quando ≥5 itens)", variable=opt_rm_prefixo5, bg=TELEGRAM_COLORS['white']).pack(anchor="w")

        opt_trim_zeros = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="Remover zeros à esquerda", variable=opt_trim_zeros, bg=TELEGRAM_COLORS['white']).pack(anchor="w")

        # Últimos N dígitos
        last_frame = tk.Frame(frm, bg=TELEGRAM_COLORS['white'])
        last_frame.pack(anchor="w", pady=(6, 0))
        opt_ultimos = tk.BooleanVar(value=False)
        tk.Checkbutton(last_frame, text="Manter somente os últimos N dígitos:", variable=opt_ultimos, bg=TELEGRAM_COLORS['white']).pack(side=tk.LEFT)
        ent_ultimos_n = tk.Entry(last_frame, width=5)
        ent_ultimos_n.pack(side=tk.LEFT, padx=6)

        # Botões
        btns = tk.Frame(frm, bg=TELEGRAM_COLORS['white'])
        btns.pack(fill=tk.X, pady=12)
        def on_aplicar():
            try:
                ops = {
                    'rm_prefixo5': opt_rm_prefixo5.get(),
                    'trim_zeros': opt_trim_zeros.get(),
                    'ultimos': opt_ultimos.get(),
                    'ultimos_n': int(ent_ultimos_n.get()) if ent_ultimos_n.get().strip().isdigit() else None,
                }
                # Sempre aplicar em TODOS os itens
                self._aplicar_formatacao_codigos(ops)
                win.destroy()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao aplicar formatação: {e}")
        tk.Button(btns, text="Aplicar", command=on_aplicar, bg=TELEGRAM_COLORS['success'], fg=TELEGRAM_COLORS['white']).pack(side=tk.RIGHT)
        tk.Button(btns, text="Cancelar", command=win.destroy, bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white']).pack(side=tk.RIGHT, padx=6)

    def _aplicar_formatacao_codigos(self, ops: dict, only_selection: bool = False):
        """Aplica as regras de formatação de código conforme 'ops' em TODOS os itens e persiste no arquivo."""
        # Sempre aplicar a todos os itens
        itens = list(self.tree.get_children())
        if not itens:
            messagebox.showinfo("Atenção", "Lista vazia.")
            return

        # Funções auxiliares
        def rm_prefixo5(codigos_lista, codigo):
            # Detecta prefixo 5 dígitos repetido em >=5 itens e remove somente esses 5
            try:
                vals = [self.tree.item(i, 'values') for i in itens]
                cods = [str(v[3]).strip() for v in vals if v and len(v) > 3]
                pref5 = [c[:5] for c in cods if len(c) >= 5 and c[:5].isdigit()]
                if not pref5:
                    return codigo
                from collections import Counter
                p, q = Counter(pref5).most_common(1)[0]
                if q >= 5 and codigo.startswith(p):
                    return codigo[5:] or codigo
                return codigo
            except Exception:
                return codigo

        def trim_zeros_left(s):
            return s.lstrip('0') or '0'

        def last_n_digits(s, n):
            if not n or n <= 0:
                return s
            dig = re.sub(r"\D+", "", s)
            return dig[-n:] if len(dig) >= n else dig

        # Aplicar item a item
        for item in itens:
            valores = list(self.tree.item(item, 'values'))
            if not valores or len(valores) < 4:
                continue
            codigo_old = str(valores[3])
            codigo_new = codigo_old

            # Sequência de operações (apenas as solicitadas)
            if ops.get('rm_prefixo5'):
                codigo_new = rm_prefixo5(itens, codigo_new)
            if ops.get('trim_zeros'):
                codigo_new = trim_zeros_left(codigo_new)
            if ops.get('ultimos') and ops.get('ultimos_n'):
                codigo_new = last_n_digits(codigo_new, ops.get('ultimos_n'))

            if codigo_new != codigo_old and codigo_new:
                # Atualizar UI
                valores[3] = codigo_new
                self.tree.item(item, values=valores)
                # Persistir (campo índice 3 = código)
                try:
                    self.atualizar_campo_no_arquivo(codigo_old, 3, codigo_new, valores)
                except Exception:
                    pass
        # Feedback
        self.status_var.set("✅ Formatação de códigos aplicada")
        try:
            self.status_label.config(fg=TELEGRAM_COLORS['success'])
        except Exception:
            pass
    
    def _create_list_controls(self, parent):
        """Cria botões de controle da lista"""
        lista_btn_frame = tk.Frame(parent, bg=TELEGRAM_COLORS['white'])
        lista_btn_frame.grid(row=3, column=0, pady=10)
        
        btn_limpar = tk.Button(
            lista_btn_frame, text="🗑️ Limpar Lista", 
            command=self.limpar_lista_produtos_de_verdade,
            bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5
        )
        btn_limpar.pack(side=tk.LEFT, padx=5)
        
        # Botão Juntar Repetidos
        btn_juntar = tk.Button(
            lista_btn_frame, text="🔗 Juntar Repetidos", 
            command=self.juntar_produtos_repetidos,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5
        )
        btn_juntar.pack(side=tk.LEFT, padx=5)
        
        # Inverter posição: primeiro Importar Romaneio, depois Inserir Grade
        btn_importar_romaneio = tk.Button(
            lista_btn_frame, text="🧾 Importar Romaneio",
            command=self.importar_romaneio,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5, wraplength=180
        )
        btn_importar_romaneio.pack(side=tk.LEFT, padx=5)
        
        btn_grade = tk.Button(
            lista_btn_frame, text="👕 Inserir Grade", 
            command=self.abrir_janela_grade,
            bg=TELEGRAM_COLORS['secondary'], fg=TELEGRAM_COLORS['white'], 
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5
        )
        btn_grade.pack(side=tk.LEFT, padx=5)
        
        # Novo: Ver Grades (abre editor) e Limpar Grades (apaga todas)
        btn_ver_grades = tk.Button(
            lista_btn_frame, text="📋 Ver Grades",
            command=self.abrir_janela_grades,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5
        )
        btn_ver_grades.pack(side=tk.LEFT, padx=5)

        btn_limpar_grades = tk.Button(
            lista_btn_frame, text="🧹 Limpar Grades",
            command=self.limpar_todas_grades,
            bg=TELEGRAM_COLORS['warning'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=5
        )
        btn_limpar_grades.pack(side=tk.LEFT, padx=5)
        
        # Enter para salvar (ignora quando houver Toplevel aberto, ex.: GradeWindow)
        self.root.bind("<Return>", self._on_root_return)
        
        # Configurar foco inicial
        self.ent_nome.focus()
    
    def _load_initial_data(self):
        """Carrega dados iniciais"""
        self.refresh_lista_produtos()
        # Garante um snapshot inicial para permitir Ctrl+Z imediatamente
        try:
            seed_undo_if_empty(tag='init')
        except Exception:
            pass
        # Aplicar efeitos da tipagem inicial (carrega marcas corretas)
        self._aplicar_efeitos_tipagem()
    
    def refresh_lista_produtos(self):
        """Recarrega a lista de produtos a partir de data/enviados.jsonl."""
        try:
            # Limpar Treeview atual
            if hasattr(self, 'tree'):
                for item in self.tree.get_children():
                    self.tree.delete(item)
            # Resetar cache de linhas brutas
            self._linhas_json_cache = {}

            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            linhas = []
            if arquivo_log.exists():
                with open(arquivo_log, "r", encoding="utf-8") as f:
                    linhas = f.readlines()

            total = 0
            for idx, linha in enumerate(linhas):
                if not linha.strip():
                    continue
                try:
                    dados = json.loads(linha)
                except json.JSONDecodeError:
                    # Ignorar linhas inválidas
                    continue

                # Extrair campos com defaults
                timestamp = dados.get("timestamp", "")
                try:
                    hora = datetime.fromisoformat(timestamp).strftime("%H:%M") if timestamp else ""
                except Exception:
                    hora = ""
                nome = dados.get("nome", "")
                marca = dados.get("marca", "")
                codigo = dados.get("codigo", "")
                quantidade = dados.get("quantidade", "")
                preco = dados.get("preco", "")
                preco_final = dados.get("preco_final")
                if preco_final in (None, ""):
                    try:
                        preco_final = calcular_preco_final(preco)
                    except Exception:
                        preco_final = ""
                categoria = dados.get("categoria", "")

                # Formatar para UI
                qtd_ui = self._format_num_for_ui(quantidade)
                custo_ui = self._format_num_for_ui(preco)
                venda_ui = self._format_num_for_ui(preco_final)

                # Inserir na Treeview
                iid = f"row_{idx}"
                if hasattr(self, 'tree'):
                    self.tree.insert("", "end", iid=iid,
                                     values=(hora, nome, marca, codigo, qtd_ui, custo_ui, venda_ui, categoria))
                # Guardar linha bruta no cache para eventual persistência de ordem
                self._linhas_json_cache[iid] = linha.rstrip("\n")
                total += 1

            # Atualizar UI de status/contadores
            try:
                self.atualizar_contador_produtos()
            except Exception:
                pass
            try:
                self.atualizar_totais()
            except Exception:
                pass
            if hasattr(self, 'status_massa_var'):
                self.status_massa_var.set(f"📊 Total de produtos: {total}")
            if hasattr(self, 'status_var') and total >= 0:
                self.status_var.set("🔄 Lista de produtos atualizada")
                try:
                    self.status_label.config(fg=TELEGRAM_COLORS['info'])
                except Exception:
                    pass
            # Se verificação de qualidade estiver ativa, reexecutar para aplicar marcadores
            try:
                if getattr(self, 'quality_active', False):
                    self._quality_run_and_mark()
                else:
                    self._quality_clear_markers()
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar lista: {e}")


    # ====== Undo / Ctrl+Z e Redo / Ctrl+Y ======
    def _on_ctrl_z_undo(self, event=None):
        """Ctrl+Z: volta um snapshot (multi-nível)."""
        try:
            ok = undo_enviados_step()
            if not ok:
                messagebox.showinfo("Desfazer", "Nenhum passo anterior disponível.")
                return
            # Recarregar lista
            self.refresh_lista_produtos()
            # Feedback de status
            self.status_var.set("↩️ Desfeito (Ctrl+Z)")
            try:
                self.status_label.config(fg=TELEGRAM_COLORS['info'])
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao desfazer: {e}")

    def _on_ctrl_y_redo(self, event=None):
        """Ctrl+Y: avança um snapshot (multi-nível)."""
        try:
            ok = redo_enviados_step()
            if not ok:
                messagebox.showinfo("Refazer", "Nenhum passo à frente disponível.")
                return
            self.refresh_lista_produtos()
            self.status_var.set("↪️ Refeito (Ctrl+Y)")
            try:
                self.status_label.config(fg=TELEGRAM_COLORS['info'])
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao refazer: {e}")


    # ================= Qualidade: lógica de UI e marcadores =================
    def _on_quality_toggle_click(self):
        try:
            self.quality_active = not getattr(self, 'quality_active', False)
            # Persistir estado
            try:
                self._quality_save_enabled(self.quality_active)
            except Exception:
                pass
            # Atualizar visual do botão
            if hasattr(self, 'btn_quality_toggle'):
                self.btn_quality_toggle.config(
                    text="Qualidade: Ativo" if self.quality_active else "Qualidade: Inativo",
                    bg=TELEGRAM_COLORS['primary'] if self.quality_active else TELEGRAM_COLORS['light_gray']
                )
            # Rodar ou limpar marcadores
            if self.quality_active:
                self._quality_run_and_mark()
            else:
                self._quality_clear_markers()
                self._quality_counts_var.set("Qualidade: --")
        except Exception as e:
            print(f"[QUALITY] toggle erro: {e}")

    def _quality_read_produtos(self):
        try:
            arq = get_app_base_dir() / "data" / "enviados.jsonl"
            produtos = []
            if arq.exists():
                with open(arq, "r", encoding="utf-8") as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln:
                            continue
                        try:
                            produtos.append(json.loads(ln))
                        except Exception:
                            pass
            return produtos
        except Exception:
            return []

    def _quality_issue_to_col(self, issue_tipo: str) -> int:
        # Mapeia tipo de issue -> índice da coluna na Treeview
        mapa = {
            'nome_invalido': 1,
            'nome_pobre': 1,
            'nome_ruido_cor': 1,
            'nome_codigo_numerico': 1,
            'nome_codigo_final': 1,
            'nome_muitos_numeros': 1,
            'quantidade_nao_unitaria': 4,
            'nome_generico': 1,
            'nome_muito_longo': 1,
            'codigo_invalido': 3,
            'codigo_formato': 3,
            'codigo_duplicado': 3,
            'quantidade_invalida': 4,
            'quantidade_alta': 4,
            'custo_invalido': 5,
            'custo_muito_baixo': 5,
            'custo_muito_alto': 5,
            'margem_negativa': 6,
            'margem_atipica': 6,
            'margem_muito_baixa': 6,
            'margem_muito_alta': 6,
            'marca_ausente': 2,
            'categoria_ausente': 7,
        }
        return mapa.get(issue_tipo, -1)

    def _quality_strip_dot(self, s: str) -> str:
        try:
            s = str(s)
            if s.startswith('[ERRO] '):
                return s[len('[ERRO] '):]
            return s
        except Exception:
            return s

    def _quality_clear_markers(self):
        try:
            if not hasattr(self, 'tree'):
                return
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, 'values'))
                if not vals:
                    continue
                # limpar possíveis marcadores nas colunas relevantes
                for idx in (1,2,3,4,5,6):
                    if idx < len(vals):
                        vals[idx] = self._quality_strip_dot(vals[idx])
                self.tree.item(iid, values=tuple(vals))
        except Exception:
            pass

    def _quality_run_and_mark(self):
        try:
            produtos = self._quality_read_produtos()
            if not produtos or not hasattr(self, 'tree'):
                self._quality_counts_var.set("Qualidade: --")
                return
            rep = avaliar_romaneio(produtos)
            # Limpar marcadores antigos
            self._quality_clear_markers()
            # Aplicar marcadores por issue
            for issue in rep.issues:
                # Marcar apenas ERROS, ignorar alertas para evitar ruído visual
                if getattr(issue, 'severidade', '') != 'erro':
                    continue
                iid = f"row_{issue.idx}"
                if not self.tree.exists(iid):
                    continue
                col_idx = self._quality_issue_to_col(issue.tipo)
                if col_idx < 0:
                    continue
                vals = list(self.tree.item(iid, "values"))
                if col_idx < len(vals):
                    prefix = '[ERRO] '
                    cur = str(vals[col_idx])
                    if not cur.startswith(prefix):
                        vals[col_idx] = f"{prefix}{cur}"
                    self.tree.item(iid, values=tuple(vals))
            # Atualizar contadores
            self._quality_counts_var.set(
                f"Score {rep.score_geral} | OK {rep.itens_ok} • Alertas {rep.itens_com_alerta} • Erros {rep.itens_com_erro}"
            )
        except Exception as e:
            print(f"[QUALITY] avaliação erro: {e}")
    
    def _on_root_return(self, event):
        # Se houver qualquer Toplevel (ex.: GradeWindow) visível, ignorar Enter aqui
        try:
            for w in self.root.winfo_children():
                if isinstance(w, tk.Toplevel) and w.winfo_exists():
                    # Se a janela não está escondida/withdrawn e está visível
                    try:
                        if w.state() != 'withdrawn' and w.winfo_viewable():
                            return "break"
                    except Exception:
                        # Se não conseguir checar estado, por segurança, bloquear
                        return "break"
        except Exception:
            pass
        # Nenhuma janela modal aberta: permitir salvar
        self.salvar_dados()
        return "break"
    
    # ===================================================================
    # MÉTODOS DE AÇÃO - FUNCIONALIDADES PRINCIPAIS
    # ===================================================================
    
    def salvar_dados(self):
        """Salva os dados do formulário"""
        nome = self.ent_nome.get().strip()
        codigo = self.ent_codigo.get().strip()
        quantidade = self.ent_quantidade.get().strip()
        preco = self.ent_preco.get().strip()
        categoria = self.categoria_var.get().strip()
        marca = self.marca_var.get().strip()
        
        if not validar_campos_obrigatorios(nome, codigo, quantidade, preco, categoria):
            messagebox.showwarning("Atenção", "Todos os campos são obrigatórios!")
            return
        
        descricao_completa = gerar_descricao_completa(nome, marca, codigo)
        preco_final = calcular_preco_final(preco)
        
        dados_produto = {
            "nome": nome, "marca": marca, "codigo": codigo,
            "quantidade": quantidade, "preco": preco, "preco_final": preco_final,
            "descricao_completa": descricao_completa, "categoria": categoria,
            "timestamp": datetime.now().isoformat()
        }
        
        # Salvar no histórico
        arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
        with open(arquivo_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(dados_produto, ensure_ascii=False) + "\n")
        
        # Limpar campos
        self.ent_nome.delete(0, tk.END)
        self.ent_codigo.delete(0, tk.END)
        self.ent_quantidade.delete(0, tk.END)
        self.ent_preco.delete(0, tk.END)
        
        self.status_var.set(f"✅ Produto '{descricao_completa}' salvo com sucesso!")
        self.status_label.config(fg=TELEGRAM_COLORS['success'])
        self.ent_nome.focus()
        self.refresh_lista_produtos()
        
        if self.auto_send_var.get():
            self.enviar_para_sistema_mecanico()
    
    def enviar_para_sistema_mecanico(self):
        """Envia produto individual para o sistema"""
        nome = self.ent_nome.get().strip()
        codigo = self.ent_codigo.get().strip()
        quantidade = self.ent_quantidade.get().strip()
        preco = self.ent_preco.get().strip()
        categoria = self.categoria_var.get().strip()
        marca = self.marca_var.get().strip()
        
        if not validar_campos_obrigatorios(nome, codigo, quantidade, preco, categoria):
            messagebox.showwarning("Atenção", "Todos os campos são obrigatórios!")
            return
        
        descricao_completa = gerar_descricao_completa(nome, marca, codigo)
        preco_final = calcular_preco_final(preco)
        
        dados_produto = {
            "nome": nome, "marca": marca, "codigo": codigo,
            "quantidade": quantidade, "preco": preco, "preco_final": preco_final,
            "descricao_completa": descricao_completa, "categoria": categoria
        }
        
        self.status_var.set("🔄 Executando automação...")
        self.status_label.config(fg=TELEGRAM_COLORS['warning'])
        self.root.update()
        
        try:
            coordenadas = load_targets()
            if not coordenadas:
                messagebox.showerror("Erro", "Coordenadas não encontradas! Execute a calibração primeiro!")
                self.status_var.set("❌ Calibração necessária")
                self.status_label.config(fg=TELEGRAM_COLORS['error'])
                return
            
            sucesso = inserir_produto_mecanico(dados_produto, coordenadas)
            
            if sucesso:
                self.status_var.set(f"✅ Produto '{descricao_completa}' enviado com sucesso!")
                self.status_label.config(fg=TELEGRAM_COLORS['success'])
                
                # Salvar no histórico
                dados_produto["timestamp"] = datetime.now().isoformat()
                arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
                with open(arquivo_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(dados_produto, ensure_ascii=False) + "\n")
                
                # Limpar campos
                self.ent_nome.delete(0, tk.END)
                self.ent_codigo.delete(0, tk.END)
                self.ent_quantidade.delete(0, tk.END)
                self.ent_preco.delete(0, tk.END)
                self.ent_nome.focus()
                self.refresh_lista_produtos()
            else:
                self.status_var.set("❌ Falha na automação")
                self.status_label.config(fg=TELEGRAM_COLORS['error'])
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na automação: {e}")
            self.status_var.set("❌ Erro na automação")
            self.status_label.config(fg=TELEGRAM_COLORS['error'])
    
    def executar_cadastro_em_massa(self):
        """Executa cadastro em massa de todos os produtos da lista"""
        if self.executando_massa:
            return
        
        arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
        if not arquivo_log.exists():
            messagebox.showwarning("Atenção", "Nenhum produto encontrado!")
            return
        
        try:
            with open(arquivo_log, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            
            if not linhas:
                messagebox.showwarning("Atenção", "Nenhum produto encontrado!")
                return
            
            produtos = []
            for linha in linhas:
                if linha.strip():
                    dados = json.loads(linha)
                    # Garantir descricao_completa no formato Nome + Marca + Código
                    try:
                        nome_p = dados.get("nome", "").strip()
                        marca_p = dados.get("marca", "").strip()
                        codigo_p = dados.get("codigo", "").strip()
                        if nome_p and codigo_p:
                            dados["descricao_completa"] = gerar_descricao_completa(nome_p, marca_p, codigo_p)
                    except Exception:
                        pass
                    produtos.append(dados)
            
            if not produtos:
                messagebox.showwarning("Atenção", "Nenhum produto válido encontrado!")
                return
            
            total = len(produtos)
            if not messagebox.askyesno("Confirmar Execução em Massa", 
                                      f"Executar cadastro de {total} produtos?\n\n"
                                      "⚠️ Certifique-se de que o Byte Empresa está aberto e calibrado!"):
                return
            
            self.executando_massa = True
            # Evento de cancelamento para interrupção imediata
            try:
                import threading as _thr
                self._cancel_event_massa = _thr.Event()
            except Exception:
                self._cancel_event_massa = None
            self.btn_executar_massa.config(state=tk.DISABLED)
            self.btn_parar.config(state=tk.NORMAL)
            self.progress_var.set(0)
            self.progress_label.config(text=f"0/{total}")
            self.status_massa_var.set("🚀 Iniciando execução em massa...")
            
            # Executar em thread separada
            thread = threading.Thread(target=self._executar_produtos_em_massa, args=(produtos,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao preparar execução: {e}")
    
    def _executar_produtos_em_massa(self, produtos):
        """Executa produtos em massa (em thread separada)"""
        try:
            coordenadas = load_targets()
            if not coordenadas:
                raise Exception("Arquivo de coordenadas não encontrado!")
            
            # Ativar ByteEmpresa uma vez só
            from ..automation.byte_empresa import ativar_janela_byte_empresa
            janela_ativada, _ = ativar_janela_byte_empresa(coordenadas)
            if not janela_ativada:
                raise Exception("Falha ao ativar janela do Byte Empresa")
            
            total = len(produtos)
            sucessos = 0
            falhas = 0
            
            for i, produto in enumerate(produtos):
                # Checagem de cancelamento rápida
                if not self.executando_massa:
                    break
                if getattr(self, '_cancel_event_massa', None) is not None and self._cancel_event_massa.is_set():
                    break
                
                try:
                    progresso = ((i + 1) / total) * 100
                    self.root.after(0, lambda p=progresso, idx=i+1, tot=total: 
                                  self._atualizar_progresso(p, idx, tot))
                    
                    self.root.after(0, lambda p=produto: 
                                  self.status_massa_var.set(f"🔄 Processando: {p['nome']}"))
                    
                    # Executar sem ativar janela (já foi ativada)
                    cancel_evt = getattr(self, '_cancel_event_massa', None)
                    sucesso = inserir_produto_mecanico(produto, coordenadas, ativar_janela=False, cancel_event=cancel_evt)
                    
                    if sucesso:
                        sucessos += 1
                    else:
                        falhas += 1
                    
                    # Delay entre produtos, cancelável
                    evt = getattr(self, '_cancel_event_massa', None)
                    if evt is not None:
                        if evt.wait(2):  # retornará True se cancelado durante a espera
                            break
                    else:
                        time.sleep(2)
                    
                except Exception as e:
                    falhas += 1
                    print(f"Erro no produto {produto['nome']}: {e}")
                    # pequena espera cancelável antes de seguir para próximo
                    evt = getattr(self, '_cancel_event_massa', None)
                    if evt is not None:
                        if evt.wait(1):
                            break
                    else:
                        time.sleep(1)
            
            self.root.after(0, lambda: self._finalizar_execucao_massa(sucessos, falhas, total))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro na execução: {e}"))
            self.root.after(0, lambda: self._finalizar_execucao_massa(0, 0, total))

    def _atualizar_progresso(self, progresso, atual, total):
        """Atualiza barra de progresso (thread-safe)"""
        self.progress_var.set(progresso)
        self.progress_label.config(text=f"{atual}/{total}")
    
    def _finalizar_execucao_massa(self, sucessos, falhas, total):
        """Finaliza execução em massa (thread-safe)"""
        self.executando_massa = False
        self.btn_executar_massa.config(state=tk.NORMAL)
        self.btn_parar.config(state=tk.DISABLED)
        # Limpar evento de cancelamento
        try:
            self._cancel_event_massa = None
        except Exception:
            pass
        
        if sucessos > 0:
            self.status_massa_var.set(f"🎉 Concluído! Sucessos: {sucessos}, Falhas: {falhas}")
            messagebox.showinfo("Execução Concluída", 
                               f"Processamento finalizado!\n\n"
                               f"✅ Sucessos: {sucessos}\n"
                               f"❌ Falhas: {falhas}\n"
                               f"📊 Total: {total}")
        else:
            self.status_massa_var.set("❌ Execução falhou completamente")
    
    def parar_execucao_massa(self):
        """Para a execução em massa (somente sinaliza e atualiza status)."""
        self.executando_massa = False
        # Dispara evento de cancelamento para interromper imediatamente qualquer espera/ação
        try:
            if getattr(self, '_cancel_event_massa', None) is not None:
                self._cancel_event_massa.set()
        except Exception:
            pass
        try:
            if hasattr(self, 'btn_executar_massa'):
                self.btn_executar_massa.config(state=tk.NORMAL)
            if hasattr(self, 'btn_parar'):
                self.btn_parar.config(state=tk.DISABLED)
            if hasattr(self, 'status_massa_var'):
                self.status_massa_var.set("⏹️ Execução em massa interrompida")
        except Exception:
            pass

    def limpar_lista_produtos_de_verdade(self):
        """Limpa a lista de produtos e zera o arquivo enviados.jsonl."""
        try:
            # Limpar UI
            if hasattr(self, 'tree'):
                for item in self.tree.get_children():
                    self.tree.delete(item)
            # Resetar cache
            self._linhas_json_cache = {}

            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            arquivo_log.parent.mkdir(parents=True, exist_ok=True)
            with open(arquivo_log, "w", encoding="utf-8") as f:
                f.write("")
            # Atualizar contador e totais
            try:
                self.atualizar_contador_produtos()
            except Exception:
                pass
            try:
                self.atualizar_totais()
            except Exception:
                pass
            if hasattr(self, 'status_massa_var'):
                self.status_massa_var.set("📊 Total de produtos: 0")
            if hasattr(self, 'status_var'):
                self.status_var.set("🧹 Lista de produtos limpa")
            if hasattr(self, 'status_label'):
                try:
                    self.status_label.config(fg=TELEGRAM_COLORS['warning'])
                except Exception:
                    pass
            # Snapshot APÓS limpar
            try:
                create_enviados_snapshot(tag="ui-clear")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar lista: {e}")

    def _on_tree_button_press(self, event):
        """Início do drag: marca item origem quando Ctrl está pressionado."""
        try:
            # Só inicia drag quando Ctrl estiver pressionado
            if not (event.state & 0x0004):
                self._drag_item = None
                self._drag_last_y = 0
                self._clear_drag_visuals()
                return
            rowid = self.tree.identify_row(event.y)
            if not rowid:
                self._drag_item = None
                self._drag_last_y = 0
                self._clear_drag_visuals()
                return
            # Marcar origem visualmente
            try:
                for iid in self.tree.get_children():
                    if "drag_source" in self.tree.item(iid, "tags"):
                        self.tree.item(iid, tags=())
                self.tree.item(rowid, tags=("drag_source",))
            except Exception:
                pass
            # Limpar indicador anterior
            self._clear_drop_indicator()
            self._drag_target = None
        except Exception:
            # Em caso de qualquer erro, cancelar drag suavemente
            self._drag_item = None
            self._drag_last_y = 0
            self._clear_drag_visuals()

    def _clear_drag_visuals(self):
        """Remove destaques e indicador de drop."""
        try:
            # Limpar tags de todos os itens
            for iid in self.tree.get_children():
                self.tree.item(iid, tags=())
        except Exception:
            pass
        self._clear_drop_indicator()
        self._drag_target = None

    def _clear_drop_indicator(self):
        """Remove a linha indicadora de drop, se existir."""
        try:
            if self._drag_indicator is not None:
                try:
                    self._drag_indicator.destroy()
                except Exception:
                    pass
                self._drag_indicator = None
        except Exception:
            self._drag_indicator = None

    def _update_drop_indicator(self, target, mouse_y):
        """Atualiza a posição da linha indicadora (acima/abaixo do alvo)."""
        try:
            x, y0, w, h = self.tree.bbox(target)
        except Exception:
            self._clear_drop_indicator()
            return
        # Determinar se acima ou abaixo do centro da linha
        above = mouse_y < (y0 + h / 2)
        y_line = y0 if above else (y0 + h - 1)

        # Criar indicador caso não exista
        if self._drag_indicator is None:
            self._drag_indicator = tk.Frame(self.tree, height=2, bg=TELEGRAM_COLORS['primary'])
        try:
            self._drag_indicator.place(x=0, y=y_line, relwidth=1.0)
        except Exception:
            pass

    def _on_tree_mouse_move(self, event):
        """Atualiza destaques e indicador de drop durante o drag."""
        if not self._drag_item:
            return
        # Exigir Ctrl durante o movimento
        if not (event.state & 0x0004):
            return
        y = event.y
        if abs(y - self._drag_last_y) < 2:
            return
        self._drag_last_y = y
        # Identificar alvo sob o cursor
        target = self.tree.identify_row(event.y)
        if not target or target == self._drag_item:
            self._clear_drop_indicator()
            return
        # Atualizar destaque do alvo
        try:
            if self._drag_target and self._drag_target != target:
                self.tree.item(self._drag_target, tags=())
            self.tree.item(target, tags=("drag_target",))
            self._drag_target = target
        except Exception:
            pass
        # Atualizar linha indicadora de drop
        self._update_drop_indicator(target, event.y)
    def _on_tree_button_release(self, event):
        """Final do drag: persiste a nova ordem no arquivo JSONL"""
        if not self._drag_item:
            self._clear_drag_visuals()
            return
        # Determinar alvo final
        target = self.tree.identify_row(event.y)
        placed = False
        if target and target != self._drag_item:
            # Posição relativa (acima/abaixo)
            try:
                x, y0, w, h = self.tree.bbox(target)
                above = event.y < (y0 + h / 2)
            except Exception:
                above = True
            idx = self.tree.index(target)
            if not above:
                idx += 1
            try:
                self.tree.move(self._drag_item, "", idx)
                placed = True
            except Exception:
                pass
        self._drag_item = None
        self._clear_drag_visuals()
        if placed:
            self._persist_tree_order_to_file()

    def _persist_tree_order_to_file(self):
        """Escreve data/enviados.jsonl respeitando a ordem atual da Treeview"""
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            children = self.tree.get_children()
            linhas_ordenadas = []
            for iid in children:
                linha_bruta = self._linhas_json_cache.get(iid)
                if linha_bruta is not None:
                    linhas_ordenadas.append(linha_bruta + "\n")
            if linhas_ordenadas:
                with open(arquivo_log, "w", encoding="utf-8") as f:
                    f.writelines(linhas_ordenadas)
                # Atualizar status
                self.status_massa_var.set(" Ordem atualizada para execução")
                # Snapshot APÓS persistir, para que Ctrl+Z volte ao estado anterior imediato
                try:
                    create_enviados_snapshot(tag="ui-order")
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar nova ordem: {e}")

    def _update_drop_indicator(self, target, cursor_y):
        """Mostra/atualiza a linha indicadora de drop acima/abaixo do alvo"""
        try:
            x, y, w, h = self.tree.bbox(target)
        except Exception:
            self._clear_drop_indicator()
            return
        above = cursor_y < (y + h / 2)
        line_y = y if above else y + h
        if self._drag_indicator is None:
            self._drag_indicator = tk.Frame(self.tree, height=2, bg="#FF9900")
        # posiciona a linha ocupando a largura toda
        self._drag_indicator.place(x=0, y=line_y, relwidth=1.0, height=2)

    def _clear_drop_indicator(self):
        if self._drag_indicator is not None:
            try:
                self._drag_indicator.place_forget()
            except Exception:
                pass
        # Remover destaque do alvo
        try:
            if self._drag_target:
                self.tree.item(self._drag_target, tags=())
        except Exception:
            pass
        self._drag_target = None

    def _clear_drag_visuals(self):
        """Remove todos os efeitos visuais de drag"""
        self._clear_drop_indicator()
        try:
            # Limpa destaque da origem
            if self._drag_item:
                self.tree.item(self._drag_item, tags=())
        except Exception:
            pass
    
    def limpar_lista_produtos(self):
        """Limpa a lista de produtos"""
        arquivo_romaneio = filedialog.askopenfilename(
            title="Selecionar Romaneio",
            filetypes=[
                ("Todos os arquivos suportados", "*.txt;*.pdf"),
                ("Arquivos de texto", "*.txt"),
                ("Arquivos PDF", "*.pdf"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not arquivo_romaneio:
            return
        
        # Atualizar status
        self.status_var.set(" Processando romaneio...")
        self.status_label.config(fg=TELEGRAM_COLORS['info'])
        self.root.update()
        
        try:
            # Usar o ParserManager para processamento inteligente
            from modules.core.parser_manager import parser_manager
            
            marca_selecionada = self.marca_var.get() if hasattr(self, 'marca_var') else "OGOCHI"
            categoria_selecionada = self.tipagem_atual if hasattr(self, 'tipagem_atual') else "Feminino"
            
            self.status_var.set(f" Processando com marca: {marca_selecionada}...")
            self.status_label.config(fg=TELEGRAM_COLORS['info'])
            self.root.update()
            
            # Processar usando o gerenciador inteligente
            resultado, parser_usado = parser_manager.processar_romaneio(
                arquivo_romaneio,
                marca=marca_selecionada,
                categoria=categoria_selecionada
            )
            
            if resultado:
                # Mostrar resultado em popup
                messagebox.showinfo(
                    "Romaneio Processado", 
                    f" Romaneio processado com sucesso!\n\n"
                    f"Parser usado: {parser_usado}\n"
                    f"Resultado:\n{resultado[:500]}{'...' if len(resultado) > 500 else ''}"
                )
                
                # Atualizar lista de produtos
                self.refresh_lista_produtos()
                
                self.status_var.set(f" Romaneio importado com parser {parser_usado}")
                self.status_label.config(fg=TELEGRAM_COLORS['success'])
            else:
                messagebox.showerror("Erro", "Falha ao processar o romaneio.\n\nVerifique se o arquivo está no formato correto.")
                self.status_var.set(" Erro ao processar romaneio")
                self.status_label.config(fg=TELEGRAM_COLORS['error'])
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao processar romaneio: {e}")
    def abrir_janela_margem(self):
        """Abre janela de margem"""
        # Atualiza label da margem e também a lista de produtos (coluna Venda)
        MargemWindow(
            self.root,
            callback_atualizar=lambda: (
                self.atualizar_margem_display(),
                self.refresh_lista_produtos()
            )
        )
    
    def abrir_janela_nova_marca(self):
        """Abre a janela de adicionar nova marca (com reuso de instância)."""
        try:
            # Reutilizar janela existente se ainda estiver aberta
            marca_win = getattr(self, '_marca_window', None)
            if marca_win is not None and isinstance(marca_win, MarcaWindow):
                try:
                    if marca_win.winfo_exists():
                        marca_win.lift()
                        return
                except Exception:
                    pass
        except Exception:
            # Se algo der errado no reuso, seguimos para criar uma nova instância
            pass

        # Criar nova janela
        try:
            self._marca_window = MarcaWindow(
                self.root,
                callback_atualizar=lambda: (
                    # Atualiza combobox/valores após adicionar a marca
                    self._atualizar_marcas_por_tipagem(),
                    self.atualizar_combobox_marcas()
                ),
                tipagem_atual=getattr(self, 'tipagem_atual', 'padrao')
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir Nova Marca: {e}")
    
    def abrir_configuracoes(self):
        """Abre a janela de configurações (delays da automação)."""
        try:
            if getattr(self, '_settings_window', None) and isinstance(self._settings_window, SettingsWindow):
                # Se a janela interna existir e estiver viva, apenas trazer para frente
                win = getattr(self._settings_window, 'win', None)
                if win is not None and hasattr(win, 'winfo_exists') and win.winfo_exists():
                    try:
                        win.lift()
                        return
                    except Exception:
                        pass
        except Exception:
            pass
        # Criar uma nova instância
        try:
            self._settings_window = SettingsWindow(self.root)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir Configurações: {e}")

    def abrir_janela_calibracao(self):
        """Abre a janela de calibração de coordenadas."""
        try:
            win = getattr(self, '_calibration_window', None)
            if win is not None and isinstance(win, CalibrationWindow):
                try:
                    if win.winfo_exists():
                        win.lift()
                        return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._calibration_window = CalibrationWindow(self.root)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir Calibração: {e}")
    
    def abrir_janela_grade(self):
        """Inicia a inserção de grade (sequencial).
        Se houver seleção, começa nela; caso contrário, começa do primeiro item.
        """
        children = self.tree.get_children()
        if not children:
            messagebox.showwarning("Atenção", "A lista de produtos está vazia.")
            return

        selecionados = self.tree.selection()
        if selecionados:
            try:
                start_index = list(children).index(selecionados[0])
            except ValueError:
                start_index = 0
        else:
            start_index = 0

        # Ativar modo sequencial
        self._grade_seq_mode = True
        self._grade_seq_index = start_index
        self._abrir_grade_por_index(start_index)

    def abrir_janela_grades(self):
        """Abre a janela de visualização/edição de grades (planilha)."""
        try:
            # Montar mapa index->nome baseado no estado atual da tree
            nomes_map = {}
            children = self.tree.get_children()
            for i, item in enumerate(children):
                vals = self.tree.item(item, "values")
                if vals:
                    nomes_map[str(i)] = str(vals[1])
            GradesWindow(self.root, nomes_map=nomes_map)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir grades: {e}")

    def limpar_todas_grades(self):
        """Apaga todas as grades salvas (grades.json)."""
        from ..core.file_manager import limpar_grades
        if not messagebox.askyesno("Confirmar", "Apagar TODAS as grades cadastradas? Esta ação não pode ser desfeita."):
            return
        try:
            limpar_grades()
            self.status_var.set(" Grades apagadas com sucesso")
            self.status_label.config(fg=TELEGRAM_COLORS['warning'])
            # Snapshot APÓS limpar grades
            try:
                create_enviados_snapshot(tag="ui-clear-grades")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar grades: {e}")

    def _abrir_grade_por_index(self, produto_index: int):
        """Abre a GradeWindow para um item pelo índice na Treeview."""
        children = self.tree.get_children()
        if not (0 <= produto_index < len(children)):
            # Fim da sequência
            self._grade_seq_mode = False
            self._grade_seq_index = None  # type: ignore
            self.status_var.set(" Inserção de grades finalizada")
            self.status_label.config(fg=TELEGRAM_COLORS['success'])
            return

        item_id = children[produto_index]
        valores = self.tree.item(item_id, "values")
        if not valores:
            messagebox.showwarning("Atenção", "Não foi possível ler os dados do produto.")
            return

        produto_nome = valores[1]
        try:
            quantidade_total = int(float(str(valores[4]).replace(',', '.')))
        except Exception:
            quantidade_total = 0
        
        # Categoria do produto (coluna 7 da tree)
        try:
            categoria_produto = str(valores[7]) if len(valores) > 7 else ""
        except Exception:
            categoria_produto = ""

        # Carregar grade salva (se houver)
        grades_salvas = carregar_grades()
        registro = grades_salvas.get(str(produto_index), {})
        grade_inicial = registro.get("sizes", {}) if isinstance(registro, dict) else {}

        GradeWindow(
            self.root,
            produto_nome=produto_nome,
            quantidade=quantidade_total,
            produto_index=produto_index,
            grade_inicial=grade_inicial,
            on_saved=self._on_grade_saved,
            categoria=categoria_produto,
        )

    def _on_grade_saved(self, produto_index: int, grade: dict):
        """Callback após salvar uma grade: feedback e auto-avançar se em modo sequencial."""
        total = sum(int(v) for v in grade.values()) if grade else 0
        self.status_var.set(f" Grade salva para item #{produto_index} (total {total}).")
        self.status_label.config(fg=TELEGRAM_COLORS['success'])

        # Marcar visualmente com ícone
        try:
            children = self.tree.get_children()
            if 0 <= produto_index < len(children):
                item_id = children[produto_index]
                valores = list(self.tree.item(item_id, "values"))
                if valores:
                    nome = valores[1]
                    if not str(nome).strip().startswith(""):
                        valores[1] = f" {nome}"
                        self.tree.item(item_id, values=valores)
        except Exception:
            pass

        # Avançar automaticamente para o próximo item sem grade, se em modo sequencial
        if self._grade_seq_mode:
            try:
                children = self.tree.get_children()
                grades_salvas = carregar_grades()
                proximo = None
                for i in range(produto_index + 1, len(children)):
                    if str(i) not in grades_salvas or not grades_salvas.get(str(i), {}).get("sizes"):
                        proximo = i
                        break
                if proximo is None:
                    # Se todos à frente já possuem grade, finalizar
                    self._grade_seq_mode = False
                    self._grade_seq_index = None  # type: ignore
                    self.status_var.set(" Todas as grades foram percorridas")
                    self.status_label.config(fg=TELEGRAM_COLORS['success'])
                else:
                    self._grade_seq_index = proximo
                    # Abrir próxima grade no próximo ciclo do loop de eventos
                    self.root.after(0, lambda idx=proximo: self._abrir_grade_por_index(idx))
            except Exception:
                self._grade_seq_mode = False
                self._grade_seq_index = None  # type: ignore
    
    def atualizar_combobox_marcas(self):
        """Atualiza o combobox de marcas baseado na tipagem atual"""
        # Usar marcas filtradas por tipagem em vez de todas as marcas
        marcas = obter_marcas_para_tipagem(self.tipagem_atual)
        self.marca_cb['values'] = marcas
        if marcas and not self.marca_var.get():
            self.marca_var.set("OGOCHI")
    
    def atualizar_margem_display(self):
        """Atualiza o display da margem atual"""
        margem_atual = carregar_margem_padrao()
        percentual_atual = int((margem_atual - 1) * 100)
        self.label_margem.config(text=f"Margem: {percentual_atual}%")
    
    def importar_romaneio(self):
        """Compat: botão 'Importar Romaneio' delega para o fluxo existente."""
        try:
            # Selecionar arquivo
            from ..config.constants import EXTENSOES_ROMANEIO
            caminho = filedialog.askopenfilename(
                title="Selecionar Romaneio",
                filetypes=EXTENSOES_ROMANEIO
            )
            if not caminho:
                return

            # Obter overrides da UI
            marca = self.marca_var.get().strip() if hasattr(self, 'marca_var') else None
            categoria = self.categoria_var.get().strip() if hasattr(self, 'categoria_var') else None

            # Processar com ParserManager (SongBird primeiro)
            self.status_var.set(" Processando romaneio...")
            self.status_label.config(fg=TELEGRAM_COLORS['info'])

            resultado, parser_usado = parser_manager.processar_romaneio(caminho, marca or None, categoria or None)

            # Atualizar interface (lista lê do enviados.jsonl)
            self.refresh_lista_produtos()
            self.atualizar_totais()

            # Feedback ao usuário
            if isinstance(parser_usado, str) and parser_usado.lower().startswith("erro"):
                messagebox.showerror("Erro", resultado or "Erro ao processar romaneio")
                self.status_var.set(" Falha ao importar romaneio")
                self.status_label.config(fg=TELEGRAM_COLORS['error'])
            else:
                # Mostrar resumo curto
                resumo = resultado.splitlines()[0] if isinstance(resultado, str) and resultado else f"Importado com {parser_usado}"
                messagebox.showinfo("Importação Concluída", f"Parser: {parser_usado}\n\n{resumo}")
                self.status_var.set(f" Romaneio importado com {parser_usado}")
                self.status_label.config(fg=TELEGRAM_COLORS['success'])
                # Snapshot APÓS importar romaneio
                try:
                    create_enviados_snapshot(tag="ui-import")
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao importar romaneio: {e}")

    def editar_campo_produto(self, event):
        """Permite editar qualquer campo do produto clicando duplo na lista."""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        
        # Identificar qual coluna foi clicada
        column = self.tree.identify_column(event.x)
        
        # Mapeamento de colunas para índices e nomes
        colunas_info = {
            "#1": {"index": 0, "nome": "Hora", "editavel": False},
            "#2": {"index": 1, "nome": "Nome", "editavel": True, "tipo": "texto"},
            "#3": {"index": 2, "nome": "Marca", "editavel": True, "tipo": "combo_marca"},
            "#4": {"index": 3, "nome": "Código", "editavel": True, "tipo": "texto"},
            "#5": {"index": 4, "nome": "Quantidade", "editavel": True, "tipo": "numero"},
            "#6": {"index": 5, "nome": "Custo", "editavel": True, "tipo": "preco"},
            "#7": {"index": 6, "nome": "Venda", "editavel": True, "tipo": "preco"},
            "#8": {"index": 7, "nome": "Categoria", "editavel": True, "tipo": "combo_categoria"},
        }
        
        # Verificar se a coluna é editável
        if column not in colunas_info or not colunas_info[column]["editavel"]:
            return
        
        # Obter informações da coluna
        col_info = colunas_info[column]
        valores = self.tree.item(item, "values")
        if not valores:
            return
        
        valor_atual = valores[col_info["index"]]
        campo_nome = col_info["nome"]
        tipo_campo = col_info["tipo"]
        
        # Criar janela de edição
        janela_edit = tk.Toplevel(self.root)
        janela_edit.title(f" Editar {campo_nome}")
        janela_edit.geometry("600x250+600+300")
        janela_edit.resizable(False, False)
        janela_edit.configure(bg=TELEGRAM_COLORS['white'])
        
        # Header
        header_frame = tk.Frame(janela_edit, bg=TELEGRAM_COLORS['primary'], height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f" Editar {campo_nome.upper()}", 
                font=TELEGRAM_FONTS['subtitle'], fg=TELEGRAM_COLORS['white'],
                bg=TELEGRAM_COLORS['primary']).pack(expand=True)
        
        # Conteúdo
        main_frame = tk.Frame(janela_edit, bg=TELEGRAM_COLORS['white'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Label do campo
        tk.Label(main_frame, text=f"{campo_nome}:", 
                font=TELEGRAM_FONTS['body_bold'], bg=TELEGRAM_COLORS['white']).pack(anchor="w", pady=(0, 10))
        
        # Campo de entrada baseado no tipo
        entry_widget = None
        
        if tipo_campo == "combo_marca":
            # ComboBox para marcas
            entry_widget = ttk.Combobox(main_frame, values=carregar_marcas_salvas(), 
                                       font=TELEGRAM_FONTS['body'], width=60)
            entry_widget.set(valor_atual)
        elif tipo_campo == "combo_categoria":
            # ComboBox para categorias
            entry_widget = ttk.Combobox(main_frame, values=["Masculino", "Feminino", "Infantil", "Acessorios"],
                                       font=TELEGRAM_FONTS['body'], width=60, state="readonly")
            entry_widget.set(valor_atual)
        else:
            # Entry normal para outros tipos
            entry_widget = tk.Entry(main_frame, width=60, font=TELEGRAM_FONTS['body'])
            entry_widget.insert(0, valor_atual)
            entry_widget.select_range(0, tk.END)
        
        entry_widget.pack(fill=tk.X, pady=(0, 20))
        entry_widget.focus()
        
        # Adicionar dicas baseadas no tipo
        if tipo_campo == "preco":
            tk.Label(main_frame, text=" Formato: 50,00 (use vírgula para decimais)", 
                    font=TELEGRAM_FONTS['small'], fg=TELEGRAM_COLORS['text_light'],
                    bg=TELEGRAM_COLORS['white']).pack(anchor="w")
        elif tipo_campo == "numero":
            tk.Label(main_frame, text=" Digite apenas números", 
                    font=TELEGRAM_FONTS['small'], fg=TELEGRAM_COLORS['text_light'],
                    bg=TELEGRAM_COLORS['white']).pack(anchor="w")
        
        # Botões
        btn_frame = tk.Frame(main_frame, bg=TELEGRAM_COLORS['white'])
        btn_frame.pack(pady=20)
        
        def salvar_edicao():
            novo_valor = entry_widget.get().strip()
            
            # Validações específicas por tipo
            if tipo_campo == "numero" and novo_valor:
                try:
                    float(novo_valor.replace(",", "."))
                except ValueError:
                    messagebox.showerror("Erro", "Digite apenas números!")
                    return
            
            if novo_valor and novo_valor != valor_atual:
                # Atualizar na lista
                novos_valores = list(valores)
                # Formatar visualmente se campo numérico relevante
                if col_info["index"] in (4, 5, 6):
                    novos_valores[col_info["index"]] = self._format_num_for_ui(novo_valor)
                else:
                    novos_valores[col_info["index"]] = novo_valor
                
                # Se foi alterado o preço de custo, recalcular preço final
                if col_info["index"] == 5:  # Preço de custo
                    try:
                        novo_preco_final = calcular_preco_final(novo_valor)
                        novos_valores[6] = self._format_num_for_ui(novo_preco_final)  # Atualizar preço final
                    except:
                        pass
                
                self.tree.item(item, values=novos_valores)
                
                # Atualizar no arquivo JSON
                self.atualizar_campo_no_arquivo(valores[3], col_info["index"], novo_valor, novos_valores)
                
                self.status_var.set(f" {campo_nome} atualizado: {novo_valor}")
                self.status_label.config(fg=TELEGRAM_COLORS['success'])
                # Atualizar totais do rodapé
                self.atualizar_totais()
                # Snapshot APÓS editar campo
                try:
                    create_enviados_snapshot(tag="ui-edit")
                except Exception:
                    pass
            
            janela_edit.destroy()
        
        def cancelar_edicao():
            janela_edit.destroy()
        
        tk.Button(btn_frame, text=" Salvar", command=salvar_edicao,
                 bg=TELEGRAM_COLORS['success'], fg=TELEGRAM_COLORS['white']).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text=" Cancelar", command=cancelar_edicao,
                 bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white']).pack(side=tk.LEFT, padx=10)
        
        # Binding para Enter e Escape
        janela_edit.bind("<Return>", lambda e: salvar_edicao())
        janela_edit.bind("<Escape>", lambda e: cancelar_edicao())
    
    def atualizar_campo_no_arquivo(self, codigo, campo_index, novo_valor, novos_valores):
        """Atualiza qualquer campo do produto no arquivo enviados.jsonl."""
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            if arquivo_log.exists():
                # Ler todas as linhas
                with open(arquivo_log, "r", encoding="utf-8") as f:
                    linhas = f.readlines()

                # Mapeamento de índices para campos JSON
                campos_json = {
                    1: "nome",
                    2: "marca", 
                    3: "codigo",
                    4: "quantidade",
                    5: "preco",
                    6: "preco_final",
                    7: "categoria"
                }
                
                # Atualizar linha correspondente
                linhas_atualizadas = []
                total_linhas = len(linhas)
                matches = 0
                atualizou_um = False
                for linha in linhas:
                    if not linha.strip():
                        # Preservar linhas vazias
                        linhas_atualizadas.append(linha)
                        continue
                    try:
                        produto = json.loads(linha)
                    except json.JSONDecodeError:
                        # Preservar linhas inválidas como estão
                        linhas_atualizadas.append(linha)
                        continue

                    if produto.get("codigo") == codigo:
                        matches += 1
                        if not atualizou_um:
                            # Atualizar o campo específico SOMENTE no primeiro match
                            if campo_index in campos_json:
                                campo_nome = campos_json[campo_index]
                                # Persistir valor formatado para campos numéricos
                                if campo_index in (4, 5, 6):  # quantidade, preco, preco_final
                                    produto[campo_nome] = self._format_num_for_ui(novo_valor)
                                else:
                                    produto[campo_nome] = novo_valor

                                # Se alterou o preço de custo, atualizar também o preço final
                                if campo_index == 5:  # Preço de custo
                                    try:
                                        produto["preco_final"] = self._format_num_for_ui(novos_valores[6])
                                    except Exception:
                                        pass

                                # Atualizar descrição completa se mudou nome, marca ou código
                                if campo_index in [1, 2, 3]:  # nome, marca, código
                                    try:
                                        nome = produto.get("nome", "")
                                        marca = produto.get("marca", "")
                                        codigo_prod = produto.get("codigo", "")
                                        produto["descricao_completa"] = gerar_descricao_completa(nome, marca, codigo_prod)
                                    except Exception:
                                        pass
                            atualizou_um = True

                    linhas_atualizadas.append(json.dumps(produto, ensure_ascii=False) + "\n")

                # Reescrever arquivo
                with open(arquivo_log, "w", encoding="utf-8") as f:
                    f.writelines(linhas_atualizadas)

                # Logs e avisos de segurança
                try:
                    campo_nome_dbg = campos_json.get(campo_index, str(campo_index))
                    print(f"[EDIT] codigo={codigo} campo={campo_nome_dbg} novo_valor={novo_valor} matches={matches} total_linhas={total_linhas}")
                    if matches == 0:
                        messagebox.showwarning("Aviso", f"Nenhum produto com código '{codigo}' foi encontrado para atualização.")
                    elif matches > 1:
                        messagebox.showwarning(
                            "Aviso",
                            f"Foram encontrados {matches} registros com o mesmo código '{codigo}'.\n"
                            f"A atualização foi aplicada somente ao primeiro registro para evitar alterações em massa."
                        )
                except Exception:
                    pass
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar arquivo: {e}")

    def deletar_produto_selecionado(self, event):
        """Deleta o produto selecionado ao pressionar DELETE"""
        # Verificar se há item selecionado
        item_selecionado = self.tree.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um produto para deletar")
            return
        
        # Obter dados do item selecionado
        item = item_selecionado[0]
        valores = self.tree.item(item, "values")
        
        if not valores:
            return
        
        codigo_produto = valores[3]  # Coluna código
        nome_produto = valores[1]    # Coluna nome
        
        # Confirmar exclusão
        resultado = messagebox.askyesno(
            "Confirmar Exclusão",
            f" Tem certeza que deseja deletar o produto?\n\n"
            f" Código: {codigo_produto}\n"
            f" Nome: {nome_produto}\n\n"
            f" Esta ação não pode ser desfeita!"
        )
        
        if not resultado:
            return
        
        try:
            # Remover da TreeView
            self.tree.delete(item)
            
            # Remover do arquivo JSON
            self.remover_produto_do_arquivo(codigo_produto)
            
            # Atualizar status
            self.status_var.set(f"🗑️ Produto deletado: {nome_produto}")
            self.status_label.config(fg=TELEGRAM_COLORS['error'])
            # Snapshot APÓS persistir remoção
            try:
                create_enviados_snapshot(tag="ui-delete")
            except Exception:
                pass
            
            # Atualizar contador
            self.atualizar_contador_produtos()
            # Atualizar totais
            self.atualizar_totais()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao deletar produto: {e}")
    
    def remover_produto_do_arquivo(self, codigo):
        """Remove produto do arquivo enviados.jsonl"""
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            if not arquivo_log.exists():
                return
            
            # Ler todas as linhas
            with open(arquivo_log, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            
            # Filtrar linhas (manter apenas os que NÃO são o código deletado)
            linhas_filtradas = []
            produtos_removidos = 0
            
            for linha in linhas:
                if linha.strip():
                    try:
                        produto = json.loads(linha)
                        if produto.get("codigo") != codigo:
                            linhas_filtradas.append(linha)
                        else:
                            produtos_removidos += 1
                    except json.JSONDecodeError:
                        # Manter linhas que não são JSON válido
                        linhas_filtradas.append(linha)
            
            # Reescrever arquivo sem o produto deletado
            with open(arquivo_log, "w", encoding="utf-8") as f:
                f.writelines(linhas_filtradas)
            
            print(f"✅ {produtos_removidos} produto(s) removido(s) do arquivo")
            
        except Exception as e:
            print(f"❌ Erro ao remover produto do arquivo: {e}")
            raise
    
    def atualizar_contador_produtos(self):
        """Atualiza o contador de produtos na interface"""
        try:
            total_produtos = len(self.tree.get_children())
            # Se houver label de contador, atualizar
            if hasattr(self, 'contador_label'):
                self.contador_label.config(text=f"Total: {total_produtos}")
        except Exception as e:
            print(f"⚠️ Erro ao atualizar contador: {e}")

    def _converter_quantidade_para_int(self, quantidade_str):
        """Converte string de quantidade para inteiro, tratando diferentes formatos"""
        try:
            # Remove espaços e converte para string se não for
            quantidade_str = str(quantidade_str).strip()
            
            # Se estiver vazio, retorna 1
            if not quantidade_str:
                return 1
            
            # Remove vírgulas e pontos decimais se existirem
            quantidade_str = quantidade_str.replace(',', '').replace('.', '')
            
            # Converte para inteiro
            return int(quantidade_str) if quantidade_str.isdigit() else 1
        except:
            return 1

    def juntar_produtos_repetidos(self):
        """Junta produtos repetidos somando suas quantidades"""
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            if not arquivo_log.exists():
                messagebox.showwarning("Atenção", "Nenhum produto encontrado para juntar!")
                return
            
            # Carregar produtos do arquivo
            produtos = []
            with open(arquivo_log, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if linha:
                        try:
                            produto = json.loads(linha)
                            produtos.append(produto)
                        except json.JSONDecodeError:
                            continue
            
            if not produtos:
                messagebox.showwarning("Atenção", "Nenhum produto válido encontrado!")
                return
            
            # Agrupar produtos por chave única (nome|codigo|preco)
            grupos = {}
            produtos_originais = len(produtos)
            
            for produto in produtos:
                nome = produto.get("nome", "").strip().upper()
                codigo = produto.get("codigo", "").strip()
                preco = produto.get("preco", "").strip()
                
                # Criar chave única
                chave = f"{nome}|{codigo}|{preco}"
                
                if chave not in grupos:
                    # Primeiro produto com essa chave
                    grupos[chave] = produto.copy()
                    grupos[chave]["quantidade_original"] = produto.get("quantidade", "1")
                else:
                    # Somar quantidade ao produto existente
                    qtd_atual = self._converter_quantidade_para_int(grupos[chave].get("quantidade", "1"))
                    qtd_adicional = self._converter_quantidade_para_int(produto.get("quantidade", "1"))
                    nova_quantidade = qtd_atual + qtd_adicional
                    grupos[chave]["quantidade"] = str(nova_quantidade)
            
            produtos_finais = list(grupos.values())
            produtos_removidos = produtos_originais - len(produtos_finais)
            
            if produtos_removidos == 0:
                messagebox.showinfo("Juntar Repetidos", "Nenhum produto repetido foi encontrado!")
                return
            
            # Confirmar operação com o usuário
            resposta = messagebox.askyesno(
                "Juntar Repetidos",
                f"Foram encontrados {produtos_removidos} produtos repetidos.\n\nProdutos originais: {produtos_originais}\nProdutos após junção: {len(produtos_finais)}\n\nDeseja continuar com a junção?"
            )
            
            if not resposta:
                return
            
            # Atualizar timestamps para manter ordem
            from datetime import datetime
            for i, produto in enumerate(produtos_finais):
                timestamp_base = datetime.now()
                timestamp_incremental = timestamp_base.replace(microsecond=i * 1000)
                produto["timestamp"] = timestamp_incremental.isoformat()
            
            # Salvar produtos unidos de volta ao arquivo
            with open(arquivo_log, "w", encoding="utf-8") as f:
                for produto in produtos_finais:
                    f.write(json.dumps(produto, ensure_ascii=False) + "\n")
            
            # Atualizar interface
            self.refresh_lista_produtos()
            
            # Atualizar status
            self.status_var.set(f"🔗 {produtos_removidos} produtos repetidos foram unidos!")
            self.status_label.config(fg=TELEGRAM_COLORS['success'])
            # Snapshot APÓS persistir junção
            try:
                create_enviados_snapshot(tag="ui-juntar")
            except Exception:
                pass
            
            # Mostrar resultado final
            messagebox.showinfo(
                "Junção Concluída",
                f"✅ Operação concluída com sucesso!\n\n• {produtos_removidos} produtos repetidos foram unidos\n• Lista reduzida de {produtos_originais} para {len(produtos_finais)} produtos\n• Quantidades foram somadas automaticamente"
            )
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao juntar produtos repetidos: {e}")
            self.status_var.set("❌ Erro ao juntar produtos repetidos")
            self.status_label.config(fg=TELEGRAM_COLORS['error'])
    
    def aplicar_categoria_todos(self):
        """Aplica a categoria atual a todos os produtos"""
        categoria_atual = self.categoria_var.get()
        if not categoria_atual:
            messagebox.showwarning("Atenção", "Selecione uma categoria primeiro!")
            return
        
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            if not arquivo_log.exists():
                messagebox.showwarning("Atenção", "Nenhum produto encontrado para aplicar categoria!")
                return
            
            # Carregar produtos do arquivo
            produtos = []
            with open(arquivo_log, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if linha:
                        try:
                            produto = json.loads(linha)
                            produtos.append(produto)
                        except json.JSONDecodeError:
                            continue
            
            if not produtos:
                messagebox.showwarning("Atenção", "Nenhum produto válido encontrado!")
                return
            
            # Aplicar categoria a todos os produtos
            for produto in produtos:
                produto["categoria"] = categoria_atual
            
            # Salvar produtos com categoria aplicada de volta ao arquivo
            with open(arquivo_log, "w", encoding="utf-8") as f:
                for produto in produtos:
                    f.write(json.dumps(produto, ensure_ascii=False) + "\n")
            
            # Atualizar interface
            self.refresh_lista_produtos()
            
            # Atualizar status
            self.status_var.set(f"✅ Categoria '{categoria_atual}' aplicada a todos os produtos!")
            self.status_label.config(fg=TELEGRAM_COLORS['success'])
            # Snapshot APÓS persistir
            try:
                create_enviados_snapshot(tag="ui-categoria")
            except Exception:
                pass
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aplicar categoria: {e}")
            self.status_var.set("❌ Erro ao aplicar categoria")
            self.status_label.config(fg=TELEGRAM_COLORS['error'])
    
    def aplicar_marca_todos(self):
        """Aplica a marca atual a todos os produtos"""
        marca_atual = self.marca_var.get()
        if not marca_atual:
            messagebox.showwarning("Atenção", "Selecione uma marca primeiro!")
            return
        
        try:
            arquivo_log = get_app_base_dir() / "data" / "enviados.jsonl"
            if not arquivo_log.exists():
                messagebox.showwarning("Atenção", "Nenhum produto encontrado para aplicar marca!")
                return
            
            # Carregar produtos do arquivo
            produtos = []
            with open(arquivo_log, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if linha:
                        try:
                            produto = json.loads(linha)
                            produtos.append(produto)
                        except json.JSONDecodeError:
                            continue
            
            if not produtos:
                messagebox.showwarning("Atenção", "Nenhum produto válido encontrado!")
                return
            
            # Aplicar marca a todos os produtos
            for produto in produtos:
                produto["marca"] = marca_atual
            
            # Salvar produtos com marca aplicada de volta ao arquivo
            with open(arquivo_log, "w", encoding="utf-8") as f:
                for produto in produtos:
                    f.write(json.dumps(produto, ensure_ascii=False) + "\n")
            
            # Atualizar interface
            self.refresh_lista_produtos()
            
            # Atualizar status
            self.status_var.set(f"✅ Marca '{marca_atual}' aplicada a todos os produtos!")
            self.status_label.config(fg=TELEGRAM_COLORS['success'])
            # Snapshot APÓS persistir
            try:
                create_enviados_snapshot(tag="ui-marca")
            except Exception:
                pass
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aplicar marca: {e}")
            self.status_var.set("❌ Erro ao aplicar marca")
            self.status_label.config(fg=TELEGRAM_COLORS['error'])

def main():
    """Função principal da aplicação"""
    root = tk.Tk()
    app = SuperCadastradorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
