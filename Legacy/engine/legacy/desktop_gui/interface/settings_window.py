"""
Janela de Configurações da Automação (PyAutoGUI).
Permite editar delays e resetar para os padrões atuais (constants.py).
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS
from ..config.constants import (
    DELAY_CLICK as DEFAULT_DELAY_CLICK,
    DELAY_TAB as DEFAULT_DELAY_TAB,
    DELAY_DIGITACAO as DEFAULT_DELAY_DIGITACAO,
    DELAY_ENTRE_TELAS as DEFAULT_DELAY_ENTRE_TELAS,
    DELAY_ENTRE_PRODUTOS as DEFAULT_DELAY_ENTRE_PRODUTOS,
)
from ..core.file_manager import get_app_base_dir

# Interação com automação para aplicar imediatamente
try:
    from ..automation.byte_empresa import (
        recarregar_config_automacao,
        get_config_automacao,
        salvar_config_automacao,
    )
except Exception:
    # Fallbacks para evitar crash caso funções ainda não existam
    def recarregar_config_automacao():
        pass
    def get_config_automacao() -> Dict[str, float]:
        return {}
    def salvar_config_automacao(cfg: Dict[str, float]):
        # Persistência direta se automação não expõe helper
        base = get_app_base_dir() / "data"
        base.mkdir(parents=True, exist_ok=True)
        (base / "automacao.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


class SettingsWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title("Configurações de Automação")
        self.win.configure(bg=TELEGRAM_COLORS['white'])
        self.win.geometry("560x520")
        self.win.minsize(520, 420)
        self.win.resizable(True, True)
        self.win.grab_set()

        # Container com rolagem vertical
        container = tk.Frame(self.win, bg=TELEGRAM_COLORS['white'])
        container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, bg=TELEGRAM_COLORS['white'], highlightthickness=0)
        vsb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        frm = tk.Frame(canvas, bg=TELEGRAM_COLORS['white'])
        frm_id = canvas.create_window((0, 0), window=frm, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Ajusta a largura do frame ao canvas
            canvas.itemconfigure(frm_id, width=canvas.winfo_width())

        frm.bind("<Configure>", _on_frame_configure)
        # Suporte a rolagem com roda do mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        tk.Label(frm, text="Ajuste os tempos da automação (segundos):", font=TELEGRAM_FONTS['body_bold'], bg=TELEGRAM_COLORS['white']).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Entradas de delays (float), contadores de TAB (int) e toggles (bool)
        self.vars = {
            # Floats
            'DELAY_CLICK': tk.StringVar(),
            'DELAY_TAB': tk.StringVar(),
            'DELAY_DIGITACAO': tk.StringVar(),
            'DELAY_ENTRE_TELAS': tk.StringVar(),
            'DELAY_ENTRE_PRODUTOS': tk.StringVar(),
            # Ints
            'T1_TABS_TO_CATEGORIA': tk.StringVar(),
            'T1_TABS_TO_CODFAB': tk.StringVar(),
            'T1_TABS_TO_SALVAR': tk.StringVar(),
            'T2_TABS_TO_PRECO': tk.StringVar(),
            'T2_TABS_TO_QTD': tk.StringVar(),
            'T2_TABS_TO_VENDA': tk.StringVar(),
            'T2_TABS_TO_SALVAR': tk.StringVar(),
        }
        self.bools = {
            'ENABLE_TELA1': tk.BooleanVar(value=True),
            'ENABLE_TELA2': tk.BooleanVar(value=True),
            'ENABLE_CLICK_ATIVAR_JANELA': tk.BooleanVar(value=True),
            'ENABLE_CLICAR_TRES_PONTINHOS': tk.BooleanVar(value=True),
        }

        linhas = [
            ("Delay de Click", 'DELAY_CLICK'),
            ("Delay de Tab", 'DELAY_TAB'),
            ("Velocidade de Digitação", 'DELAY_DIGITACAO'),
            ("Delay entre Telas", 'DELAY_ENTRE_TELAS'),
            ("Delay entre Produtos", 'DELAY_ENTRE_PRODUTOS'),
        ]

        for i, (label, key) in enumerate(linhas, start=1):
            tk.Label(frm, text=label+":", bg=TELEGRAM_COLORS['white'], font=TELEGRAM_FONTS['body']).grid(row=i, column=0, sticky="w", pady=4)
            ent = tk.Entry(frm, textvariable=self.vars[key], width=12)
            ent.grid(row=i, column=1, sticky="w", pady=4)

        # Separador
        ttk.Separator(frm, orient='horizontal').grid(row=len(linhas)+1, column=0, columnspan=4, sticky='ew', pady=(12, 6))

        # Tabs entre ações
        tk.Label(frm, text="Quantidade de TABs por etapa:", font=TELEGRAM_FONTS['body_bold'], bg=TELEGRAM_COLORS['white']).grid(row=len(linhas)+2, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tabs_linhas = [
            ("Tela 1 → Categoria", 'T1_TABS_TO_CATEGORIA'),
            ("Tela 1 → Cod.Fabricante", 'T1_TABS_TO_CODFAB'),
            ("Tela 1 → Salvar", 'T1_TABS_TO_SALVAR'),
            ("Tela 2 → Preço Compra", 'T2_TABS_TO_PRECO'),
            ("Tela 2 → Quantidade", 'T2_TABS_TO_QTD'),
            ("Tela 2 → Preço Venda", 'T2_TABS_TO_VENDA'),
            ("Tela 2 → Salvar", 'T2_TABS_TO_SALVAR'),
        ]
        base_row = len(linhas) + 3
        for j, (label, key) in enumerate(tabs_linhas):
            r = base_row + j
            tk.Label(frm, text=label+":", bg=TELEGRAM_COLORS['white'], font=TELEGRAM_FONTS['body']).grid(row=r, column=0, sticky="w", pady=3)
            ent = tk.Entry(frm, textvariable=self.vars[key], width=10)
            ent.grid(row=r, column=1, sticky="w", pady=3)

        # Separador
        sep2_row = base_row + len(tabs_linhas)
        ttk.Separator(frm, orient='horizontal').grid(row=sep2_row, column=0, columnspan=4, sticky='ew', pady=(12, 6))

        # Toggles
        tk.Label(frm, text="Ações habilitadas:", font=TELEGRAM_FONTS['body_bold'], bg=TELEGRAM_COLORS['white']).grid(row=sep2_row+1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        toggles = [
            ("Ativar clique para focar janela", 'ENABLE_CLICK_ATIVAR_JANELA'),
            ("Executar TELA 1 (dados)", 'ENABLE_TELA1'),
            ("Executar TELA 2 (preços/estoque)", 'ENABLE_TELA2'),
            ("Clicar nos 3 pontinhos no fim", 'ENABLE_CLICAR_TRES_PONTINHOS'),
        ]
        for k, (label, key) in enumerate(toggles):
            tk.Checkbutton(frm, text=label, variable=self.bools[key], bg=TELEGRAM_COLORS['white']).grid(row=sep2_row+2+k, column=0, columnspan=2, sticky="w", pady=2)

        # Botões
        btns = tk.Frame(frm, bg=TELEGRAM_COLORS['white'])
        btns.grid(row=sep2_row+2+len(toggles), column=0, columnspan=3, sticky="e", pady=(16,16), padx=(0,16))
        tk.Button(btns, text="Resetar Padrões", command=self._on_reset, bg=TELEGRAM_COLORS['warning'], fg=TELEGRAM_COLORS['white']).pack(side=tk.LEFT, padx=(0,8))
        tk.Button(btns, text="Salvar", command=self._on_save, bg=TELEGRAM_COLORS['success'], fg=TELEGRAM_COLORS['white']).pack(side=tk.LEFT)

        self._carregar_valores()
        # Centraliza janela após construir
        try:
            self.win.update_idletasks()
            self._center_on_screen()
        except Exception:
            pass

    def _center_on_screen(self):
        self.win.update_idletasks()
        w = self.win.winfo_width()
        h = self.win.winfo_height()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        max_w = int(sw * 0.92)
        max_h = int(sh * 0.92)
        w = min(max(w, 520), max_w)
        h = min(max(h, 420), max_h)
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _carregar_valores(self):
        # Carrega valores efetivos atuais (com overrides se houver)
        efetivo = {
            'DELAY_CLICK': DEFAULT_DELAY_CLICK,
            'DELAY_TAB': DEFAULT_DELAY_TAB,
            'DELAY_DIGITACAO': DEFAULT_DELAY_DIGITACAO,
            'DELAY_ENTRE_TELAS': DEFAULT_DELAY_ENTRE_TELAS,
            'DELAY_ENTRE_PRODUTOS': DEFAULT_DELAY_ENTRE_PRODUTOS,
            # Tabs defaults
            'T1_TABS_TO_CATEGORIA': 3,
            'T1_TABS_TO_CODFAB': 16,
            'T1_TABS_TO_SALVAR': 3,
            'T2_TABS_TO_PRECO': 1,
            'T2_TABS_TO_QTD': 8,
            'T2_TABS_TO_VENDA': 2,
            'T2_TABS_TO_SALVAR': 2,
            # Toggles defaults
            'ENABLE_TELA1': True,
            'ENABLE_TELA2': True,
            'ENABLE_CLICK_ATIVAR_JANELA': True,
            'ENABLE_CLICAR_TRES_PONTINHOS': True,
        }
        try:
            cfg = get_config_automacao() or {}
            # Mistura mantendo tipos
            for k in efetivo.keys():
                if k in cfg:
                    efetivo[k] = cfg[k]
        except Exception:
            pass
        # Preencher vars
        for k in list(self.vars.keys()):
            v = efetivo.get(k, '')
            self.vars[k].set(str(v))
        for k in list(self.bools.keys()):
            self.bools[k].set(bool(efetivo.get(k, self.bools[k].get())))

    def _on_reset(self):
        # Reseta arquivo de config e aplica padrões
        try:
            base = get_app_base_dir() / "data"
            arq = base / "automacao.json"
            if arq.exists():
                arq.unlink()
            recarregar_config_automacao()
            self._carregar_valores()
            messagebox.showinfo("Configurações", "Configurações resetadas para os padrões.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao resetar: {e}")

    def _on_save(self):
        try:
            cfg = {}
            # Floats
            for k in ['DELAY_CLICK','DELAY_TAB','DELAY_DIGITACAO','DELAY_ENTRE_TELAS','DELAY_ENTRE_PRODUTOS']:
                cfg[k] = float(self.vars[k].get().replace(',', '.'))
            # Ints
            for k in ['T1_TABS_TO_CATEGORIA','T1_TABS_TO_CODFAB','T1_TABS_TO_SALVAR','T2_TABS_TO_PRECO','T2_TABS_TO_QTD','T2_TABS_TO_VENDA','T2_TABS_TO_SALVAR']:
                cfg[k] = int(self.vars[k].get().strip())
            # Bools
            for k in self.bools:
                cfg[k] = bool(self.bools[k].get())
        except Exception:
            messagebox.showerror("Erro", "Valores inválidos. Verifique números (ex.: 0.15) e inteiros para TABs.")
            return
        try:
            salvar_config_automacao(cfg)
            recarregar_config_automacao()
            messagebox.showinfo("Configurações", "Configurações salvas e aplicadas.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")
