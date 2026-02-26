"""
🏷️ JANELA DE MARCAS
===================

Janela para adicionar novas marcas ao sistema.
"""

import tkinter as tk
from tkinter import messagebox
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import MARCA_WINDOW_GEOMETRY, ICON_FILE
from ..core.file_manager import get_app_base_dir, adicionar_nova_marca, adicionar_marca_para_tipagem


class MarcaWindow(tk.Toplevel):
    """Janela de marcas modernizada"""
    
    def __init__(self, master: tk.Tk, callback_atualizar=None, tipagem_atual="padrao"):
        super().__init__(master)
        self.callback_atualizar = callback_atualizar
        self.tipagem_atual = tipagem_atual
        self._setup_window()
        self._create_interface()
    
    def _setup_window(self):
        """Configura a janela básica"""
        self.title("➕ Nova Marca - Super Cadastrador v1")
        self.geometry(MARCA_WINDOW_GEOMETRY)
        self.configure(bg=TELEGRAM_COLORS['light_gray'])
        self.resizable(False, False)
        
        # Ícone
        try:
            icon_path = get_app_base_dir() / ICON_FILE
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
            else:
                self.iconbitmap(ICON_FILE)
        except Exception as e:
            print(f"DEBUG: Erro ao carregar ícone na janela: {e}")
    
    def _create_interface(self):
        """Cria todos os elementos da interface"""
        # Header
        header_frame = tk.Frame(self, bg=TELEGRAM_COLORS['primary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="➕ ADICIONAR NOVA MARCA", 
            font=TELEGRAM_FONTS['title'], 
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        title_label.pack(expand=True)
        
        # Conteúdo
        main_frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        tk.Label(
            main_frame, 
            text="Nome da Marca:", 
            font=TELEGRAM_FONTS['body_bold'],
            bg=TELEGRAM_COLORS['white']
        ).pack(anchor="w", pady=(0, 10))
        
        self.ent_marca = tk.Entry(main_frame, width=40, font=TELEGRAM_FONTS['body'])
        self.ent_marca.pack(fill=tk.X, pady=(0, 20))
        self.ent_marca.focus()
        
        # Botões
        btn_frame = tk.Frame(main_frame, bg=TELEGRAM_COLORS['white'])
        btn_frame.pack(fill=tk.X, pady=20)
        
        tk.Button(
            btn_frame, 
            text="❌ Cancelar", 
            command=self.destroy,
            bg=TELEGRAM_COLORS['error'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat', 
            padx=20, 
            pady=5
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame, 
            text="✅ Adicionar", 
            command=self.adicionar_marca,
            bg=TELEGRAM_COLORS['success'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat', 
            padx=20, 
            pady=5
        ).pack(side=tk.RIGHT)
        
        self.bind("<Return>", lambda e: self.adicionar_marca())
    
    def adicionar_marca(self):
        """Adiciona a nova marca na tipagem atual"""
        nova_marca = self.ent_marca.get().strip()
        if not nova_marca:
            messagebox.showwarning("Atenção", "Digite o nome da marca!")
            return
        
        # Adicionar marca para a tipagem específica
        if adicionar_marca_para_tipagem(self.tipagem_atual, nova_marca):
            tipagem_nome = self.tipagem_atual.title() if self.tipagem_atual != "padrao" else "Padrão"
            messagebox.showinfo("Sucesso", f"Marca '{nova_marca}' adicionada para tipagem {tipagem_nome}!")
            if self.callback_atualizar:
                self.callback_atualizar()
            self.destroy()
        else:
            messagebox.showerror("Erro", "Falha ao adicionar marca ou marca já existe!")
