"""
📊 JANELA DE LOG DE PRODUTOS
============================

Janela modernizada para visualizar o histórico completo de produtos enviados.
"""

import json
import tkinter as tk
from tkinter import messagebox, ttk
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import LOG_WINDOW_GEOMETRY, ICON_FILE
from ..core.file_manager import get_app_base_dir


class LogWindow(tk.Toplevel):
    """Janela de log modernizada estilo Telegram"""
    
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self._setup_window()
        self._create_interface()
        self.refresh_log()
    
    def _setup_window(self):
        """Configura a janela básica"""
        self.title("📊 Itens Enviados - Super Cadastrador v1")
        self.geometry(LOG_WINDOW_GEOMETRY)
        self.configure(bg=TELEGRAM_COLORS['light_gray'])
        self.resizable(True, True)
        
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
        # Header moderno
        header_frame = tk.Frame(self, bg=TELEGRAM_COLORS['primary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="📊 HISTÓRICO DE ITENS ENVIADOS", 
            font=TELEGRAM_FONTS['title'], 
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        title_label.pack(expand=True)

        # Frame para os botões
        btn_frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'], height=50)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        btn_frame.pack_propagate(False)

        btn_refresh = tk.Button(
            btn_frame, 
            text="🔄 Atualizar", 
            command=self.refresh_log,
            bg=TELEGRAM_COLORS['info'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat', 
            padx=15, 
            pady=5
        )
        btn_refresh.pack(side=tk.LEFT, padx=5)
        
        btn_clear = tk.Button(
            btn_frame, 
            text="🗑️ Limpar Lista", 
            command=self.clear_log,
            bg=TELEGRAM_COLORS['error'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat', 
            padx=15, 
            pady=5
        )
        btn_clear.pack(side=tk.LEFT, padx=5)

        # Frame para a tabela
        frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        columns = ("hora", "nome", "codigo", "quantidade", "preco", "categoria")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("hora", text="Hora")
        self.tree.heading("nome", text="Nome do Produto")
        self.tree.heading("codigo", text="Código")
        self.tree.heading("quantidade", text="Qtd")
        self.tree.heading("preco", text="Preço")
        self.tree.heading("categoria", text="Categoria")
        
        self.tree.column("hora", width=80, minwidth=60)
        self.tree.column("nome", width=200, minwidth=150)
        self.tree.column("codigo", width=100, minwidth=80)
        self.tree.column("quantidade", width=60, minwidth=50)
        self.tree.column("preco", width=80, minwidth=60)
        self.tree.column("categoria", width=100, minwidth=80)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def refresh_log(self) -> None:
        """Atualiza a tabela lendo o arquivo enviados.jsonl."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        data_dir = get_app_base_dir() / "data"
        sent = data_dir / "enviados.jsonl"
        
        if sent.exists():
            for line in sent.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                    hora = item.get("timestamp", "")[11:19]
                    nome = item.get("nome", "-")
                    codigo = item.get("codigo", "-")
                    quantidade = item.get("quantidade", "-")
                    preco = item.get("preco", "-")
                    categoria = item.get("categoria", "-")
                    
                    self.tree.insert("", "end", values=(hora, nome, codigo, quantidade, preco, categoria))
                except Exception:
                    continue
    
    def clear_log(self) -> None:
        """Limpa o arquivo de enviados após confirmação."""
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja limpar toda a lista?\n\nEsta ação não pode ser desfeita."):
            try:
                data_dir = get_app_base_dir() / "data"
                sent = data_dir / "enviados.jsonl"
                if sent.exists():
                    sent.unlink()
                self.refresh_log()
                messagebox.showinfo("Sucesso", "Lista limpa com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao limpar: {e}")
