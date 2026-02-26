"""
🎯 JANELA DE CALIBRAÇÃO
=======================

Janela para configurar as coordenadas de automação do ByteEmpresa.
"""

import tkinter as tk
from tkinter import messagebox
import pyautogui
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import CALIBRATION_WINDOW_GEOMETRY, ICON_FILE
from ..core.file_manager import get_app_base_dir, load_targets, save_targets


class CalibrationWindow(tk.Toplevel):
    """Janela de calibração modernizada"""
    
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self._setup_window()
        self._create_interface()
    
    def _setup_window(self):
        """Configura a janela básica"""
        self.title("🎯 Calibração - Super Cadastrador v1")
        self.geometry(CALIBRATION_WINDOW_GEOMETRY)
        self.configure(bg=TELEGRAM_COLORS['light_gray'])
        self.resizable(True, True)
        # Tamanho mínimo para evitar cortes em diferentes DPIs
        self.minsize(720, 460)

        # Ícone
        try:
            icon_path = get_app_base_dir() / ICON_FILE
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
            else:
                self.iconbitmap(ICON_FILE)
        except Exception as e:
            print(f"DEBUG: Erro ao carregar ícone na janela: {e}")
        # Centraliza após criar
        try:
            self.update_idletasks()
            self._center_on_screen()
        except Exception:
            pass
    
    def _create_interface(self):
        """Cria todos os elementos da interface"""
        # Header
        header_frame = tk.Frame(self, bg=TELEGRAM_COLORS['primary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🎯 CALIBRAÇÃO DE COORDENADAS", 
            font=TELEGRAM_FONTS['title'], 
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        title_label.pack(expand=True)

        # Conteúdo
        content_frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        # Grid responsivo
        for c in range(6):
            content_frame.grid_columnconfigure(c, weight=1 if c == 2 else 0)

        existing = load_targets()

        tk.Label(
            content_frame, 
            text="Título da janela alvo:", 
            font=TELEGRAM_FONTS['body_bold'],
            bg=TELEGRAM_COLORS['white']
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        self.title_var = tk.StringVar(value=existing.get("title", ""))
        tk.Entry(
            content_frame, 
            textvariable=self.title_var, 
            width=50,
            font=TELEGRAM_FONTS['body']
        ).grid(row=0, column=1, columnspan=2, sticky="w", padx=10)

        self.coords = {}
        fields = [
            ("byte_empresa_posicao", "Posição Byte Empresa (ativar janela)"),
            ("campo_descricao", "Campo Descrição (TELA 1)"),
            ("tres_pontinhos", "Botão 3 pontinhos (TELA 2)")
        ]

        for i, (key, label) in enumerate(fields, 1):
            tk.Label(
                content_frame, 
                text=f"{label}:", 
                font=TELEGRAM_FONTS['body'],
                bg=TELEGRAM_COLORS['white']
            ).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            
            x_var = tk.StringVar(value=str(existing.get(key, {}).get("x", "")))
            y_var = tk.StringVar(value=str(existing.get(key, {}).get("y", "")))
            
            tk.Label(
                content_frame, 
                text="X:", 
                font=TELEGRAM_FONTS['small'],
                bg=TELEGRAM_COLORS['white']
            ).grid(row=i, column=1, sticky="e", padx=(5,0))
            
            tk.Entry(
                content_frame, 
                textvariable=x_var, 
                width=8,
                font=TELEGRAM_FONTS['body']
            ).grid(row=i, column=2, padx=2)
            
            tk.Label(
                content_frame, 
                text="Y:", 
                font=TELEGRAM_FONTS['small'],
                bg=TELEGRAM_COLORS['white']
            ).grid(row=i, column=3, sticky="e", padx=(5,0))
            
            tk.Entry(
                content_frame, 
                textvariable=y_var, 
                width=8,
                font=TELEGRAM_FONTS['body']
            ).grid(row=i, column=4, padx=2)
            
            tk.Button(
                content_frame, 
                text="📍 Capturar", 
                bg=TELEGRAM_COLORS['info'], 
                fg=TELEGRAM_COLORS['white'],
                font=TELEGRAM_FONTS['button'], 
                relief='flat',
                command=lambda x=x_var, y=y_var: self._obter_coordenadas(x, y)
            ).grid(row=i, column=5, padx=10)
            
            self.coords[key] = (x_var, y_var)

        # Botões
        btn_frame = tk.Frame(content_frame, bg=TELEGRAM_COLORS['white'])
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=6, pady=20)
        
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
            text="💾 Salvar", 
            command=self._save,
            bg=TELEGRAM_COLORS['success'], 
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], 
            relief='flat', 
            padx=20, 
            pady=5
        ).pack(side=tk.RIGHT)

    def _center_on_screen(self):
        """Centraliza a janela na tela atual."""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # Limites com margem
        max_w = int(sw * 0.9)
        max_h = int(sh * 0.9)
        w = min(max(w, 720), max_w)
        h = min(max(h, 460), max_h)
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
    
    def _obter_coordenadas(self, x_var, y_var):
        """Inicia captura de coordenadas com countdown"""
        # Criar janela de countdown
        countdown_window = tk.Toplevel(self)
        countdown_window.title("⏱️ Capturando...")
        countdown_window.geometry("300x150+400+300")
        countdown_window.configure(bg=TELEGRAM_COLORS['primary'])
        countdown_window.resizable(False, False)
        countdown_window.attributes('-topmost', True)
        
        # Label do countdown
        countdown_label = tk.Label(
            countdown_window,
            text="🎯 Posicione o mouse!\n\nCapturando em: 2",
            font=('Segoe UI', 14, 'bold'),
            fg=TELEGRAM_COLORS['white'],
            bg=TELEGRAM_COLORS['primary']
        )
        countdown_label.pack(expand=True)
        
        # Iniciar countdown
        self._countdown_captura(countdown_window, countdown_label, 2, x_var, y_var)
    
    def _countdown_captura(self, countdown_window, countdown_label, segundos, x_var, y_var):
        """Executa countdown visual e captura coordenadas"""
        if segundos > 0:
            # Atualizar texto do countdown
            countdown_label.config(text=f"🎯 Posicione o mouse!\n\nCapturando em: {segundos}")
            # Agendar próximo segundo
            self.after(1000, lambda: self._countdown_captura(countdown_window, countdown_label, segundos-1, x_var, y_var))
        else:
            # Capturar coordenadas
            try:
                x, y = pyautogui.position()
                x_var.set(str(int(x)))
                y_var.set(str(int(y)))
                
                # Mostrar sucesso na janela de countdown
                countdown_label.config(
                    text=f"✅ Capturado!\n\nX: {int(x)}\nY: {int(y)}",
                    fg=TELEGRAM_COLORS['white']
                )
                
                # Fechar janela após 1.5 segundos
                self.after(1500, countdown_window.destroy)
                
            except Exception as e:
                countdown_label.config(
                    text=f"❌ Erro!\n\n{str(e)}",
                    fg=TELEGRAM_COLORS['white']
                )
                self.after(2000, countdown_window.destroy)
    
    def _save(self):
        """Salva as coordenadas configuradas"""
        config = {"title": self.title_var.get().strip()}
        for key, (x_var, y_var) in self.coords.items():
            try:
                x = int(x_var.get().strip())
                y = int(y_var.get().strip())
                config[key] = {"x": x, "y": y}
            except ValueError:
                pass
        path = save_targets(config)
        messagebox.showinfo("Sucesso", f"Coordenadas salvas!\n{path}")
        self.destroy()
