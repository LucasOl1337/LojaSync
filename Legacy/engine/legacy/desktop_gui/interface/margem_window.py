"""
💰 JANELA DE MARGEM
===================

Janela para configurar margem de lucro do sistema.
"""

import tkinter as tk
from tkinter import messagebox
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import MARGEM_WINDOW_GEOMETRY, ICON_FILE
from ..core.file_manager import get_app_base_dir, carregar_margem_padrao, salvar_margem_padrao
from ..core.calculator import calcular_preco_final


class MargemWindow(tk.Toplevel):
    """Janela de margem modernizada"""
    
    def __init__(self, master: tk.Tk, callback_atualizar=None):
        super().__init__(master)
        self.callback_atualizar = callback_atualizar
        self._setup_window()
        self._create_interface()
    
    def _format_num_for_persist(self, value):
        """Remove casas decimais se forem zero (ex.: 5,0000/5.0000 -> 5). Mantém demais como estão.
        Retorna string para manter consistência com a interface principal.
        """
        try:
            if value is None:
                return ""
            s = str(value).strip()
            if not s:
                return s
            s_norm = s.replace(',', '.')
            f = float(s_norm)
            if abs(f - round(f)) < 1e-9:
                return str(int(round(f)))
            return s
        except Exception:
            return str(value) if value is not None else ""
    
    def _setup_window(self):
        """Configura a janela básica"""
        self.title("💰 Margem - Super Cadastrador v1")
        self.geometry(MARGEM_WINDOW_GEOMETRY)
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
            text="💰 CONFIGURAR MARGEM DE LUCRO", 
            font=TELEGRAM_FONTS['title'], 
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        title_label.pack(expand=True)
        
        # Conteúdo
        main_frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Margem atual
        margem_atual = carregar_margem_padrao()
        percentual_atual = int((margem_atual - 1) * 100)
        
        tk.Label(
            main_frame, 
            text=f"Margem Atual: {percentual_atual}%", 
            font=TELEGRAM_FONTS['subtitle'], 
            fg=TELEGRAM_COLORS['success'],
            bg=TELEGRAM_COLORS['white']
        ).pack(pady=(0, 20))
        
        # Margens predefinidas
        frame_pred = tk.LabelFrame(
            main_frame, 
            text="Margens Predefinidas", 
            font=TELEGRAM_FONTS['body_bold'], 
            bg=TELEGRAM_COLORS['white']
        )
        frame_pred.pack(fill=tk.X, pady=(0, 20))
        
        margens = [("106% (Padrão)", 2.06), ("120%", 2.20), ("150%", 2.50)]
        
        for texto, valor in margens:
            tk.Button(
                frame_pred, 
                text=texto, 
                command=lambda v=valor: self.definir_margem(v),
                bg=TELEGRAM_COLORS['info'], 
                fg=TELEGRAM_COLORS['white'],
                font=TELEGRAM_FONTS['button'], 
                relief='flat',
                padx=15, 
                pady=5
            ).pack(side=tk.LEFT, padx=5, pady=10)
        
        # Margem personalizada
        frame_pers = tk.LabelFrame(
            main_frame, 
            text="Margem Personalizada", 
            font=TELEGRAM_FONTS['body_bold'], 
            bg=TELEGRAM_COLORS['white']
        )
        frame_pers.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            frame_pers, 
            text="Percentual (%):", 
            font=TELEGRAM_FONTS['body'],
            bg=TELEGRAM_COLORS['white']
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.ent_margem = tk.Entry(frame_pers, width=20, font=TELEGRAM_FONTS['body'])
        self.ent_margem.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.ent_margem.focus()
        
        tk.Button(
            frame_pers, 
            text="✅ Aplicar Margem", 
            command=self.aplicar_margem_personalizada,
            bg=TELEGRAM_COLORS['success'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat',
            padx=15, 
            pady=5
        ).pack(pady=10)

        # Atualização em massa dos preços de venda
        frame_mass = tk.LabelFrame(
            main_frame,
            text="Atualização em Massa",
            font=TELEGRAM_FONTS['body_bold'],
            bg=TELEGRAM_COLORS['white']
        )
        frame_mass.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            frame_mass,
            text=(
                "Recalcular o preço de venda (preco_final) de TODOS os produtos\n"
                "usando a margem ATUAL. Um backup será criado antes da atualização."
            ),
            font=TELEGRAM_FONTS['small'],
            fg=TELEGRAM_COLORS['text_light'],
            bg=TELEGRAM_COLORS['white']
        ).pack(anchor="w", padx=10, pady=(8, 6))

        tk.Button(
            frame_mass,
            text="🔄 ATUALIZAR VALORES DE VENDA DE TODOS OS PRODUTOS PARA A MARGEM ATUAL",
            command=self.atualizar_valores_venda_todos,
            bg=TELEGRAM_COLORS['info'],
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'],
            relief='flat',
            padx=15,
            pady=6,
            wraplength=520
        ).pack(padx=10, pady=(0, 10))
        
        # Botão cancelar
        tk.Button(
            main_frame, 
            text="❌ Fechar", 
            command=self.destroy,
            bg=TELEGRAM_COLORS['error'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat',
            padx=20, 
            pady=5
        ).pack(pady=20)
        
        self.bind("<Return>", lambda e: self.aplicar_margem_personalizada())
    
    def definir_margem(self, margem: float):
        """Define uma margem predefinida"""
        percentual = int((margem - 1) * 100)
        if messagebox.askyesno("Confirmar", f"Definir margem de {percentual}%?"):
            salvar_margem_padrao(margem)
            messagebox.showinfo("Sucesso", f"Margem: {percentual}%!")
            if self.callback_atualizar:
                self.callback_atualizar()
            self.destroy()
    
    def aplicar_margem_personalizada(self):
        """Aplica margem personalizada digitada"""
        try:
            percentual = float(self.ent_margem.get().strip())
            if percentual <= 0:
                messagebox.showwarning("Atenção", "Percentual deve ser > 0!")
                return
            
            margem = 1 + (percentual / 100)
            
            if messagebox.askyesno("Confirmar", f"Margem de {percentual}%?"):
                salvar_margem_padrao(margem)
                messagebox.showinfo("Sucesso", f"Margem: {percentual}%!")
                if self.callback_atualizar:
                    self.callback_atualizar()
                self.destroy()
        except ValueError:
            messagebox.showerror("Erro", "Digite um número válido!")

    def atualizar_valores_venda_todos(self):
        """Recalcula silenciosamente o campo 'preco_final' de todas as linhas do
        arquivo enviados.jsonl usando a margem atual. Sem backup e sem popups.
        """
        try:
            path = get_app_base_dir() / "data" / "enviados.jsonl"
            if not path.exists():
                # Silencioso: nada a fazer
                return

            with open(path, "r", encoding="utf-8") as f:
                linhas = f.readlines()

            if not linhas:
                return

            novos = []
            for linha in linhas:
                try:
                    linha_strip = linha.strip()
                    if not linha_strip:
                        continue
                    dado = __import__('json').loads(linha_strip)
                    preco_custo = str(dado.get("preco", "")).strip()
                    if preco_custo:
                        pf = calcular_preco_final(preco_custo)
                        dado["preco_final"] = self._format_num_for_persist(pf)
                    novos.append(__import__('json').dumps(dado, ensure_ascii=False) + "\n")
                except Exception:
                    # Mantém a linha original se der erro ao parsear
                    novos.append(linha)

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(novos)

            if self.callback_atualizar:
                self.callback_atualizar()
        except Exception:
            # Silencioso em caso de erro
            pass
