"""
🧩 JANELA DE GRADE DE TAMANHOS
===============================

Permite definir a grade (quantidade por tamanho) para um produto específico.
Valida que a soma das quantidades por tamanho é igual à quantidade do produto.

Persistência feita via file_manager.salvar_grade(index, grade).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional

from ..core.file_manager import salvar_grade
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS


# Ordem global (completa) definida anteriormente para referência geral
# PP, P, M, G, GG, XG, EXG, U, 1..18, 34..58, G1..G6, 6M, 9M, 12M, 18M
TAMANHOS_PADRAO = [
    "PP", "P", "M", "G", "GG", "XG", "EXG", "U",
    *[str(i) for i in range(1, 19)],
    *[str(i) for i in range(34, 59)],
    *[f"G{i}" for i in range(1, 7)],
    "6M", "9M", "12M", "18M",
]

# Listas específicas por categoria
# Infantil: PP, P, M, G, GG, U, 1,2,3,4,6,8,10,12,14,16,18, 6M,9M,12M,18M
TAMANHOS_INFANTIL = [
    "PP", "P", "M", "G", "GG", "U",
    "1", "2", "3", "4", "6", "8", "10", "12", "14", "16", "18",
    "6M", "9M", "12M", "18M",
]

# Adulto: PP, P, M, G, GG, XG, EXG, U, 34..58, G1..G6
TAMANHOS_ADULTO = [
    "PP", "P", "M", "G", "GG", "XG", "EXG", "U",
    *[str(i) for i in range(34, 59, 2)],
    *[f"G{i}" for i in range(1, 7)],
]


class GradeWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        produto_nome: str,
        quantidade: int,
        produto_index: int,
        grade_inicial: Optional[Dict[str, int]] = None,
        on_saved=None,
        categoria: Optional[str] = None,
    ) -> None:
        super().__init__(master)
        self.title(f"Inserir Grade - {produto_nome}")
        self.configure(bg=TELEGRAM_COLORS['white'])
        self.resizable(False, False)

        self.quantidade_total = int(quantidade)
        self.produto_index = int(produto_index)
        self.on_saved = on_saved
        self.categoria = (categoria or "").strip()

        self.vars: Dict[str, tk.IntVar] = {}

        self._build_ui(grade_inicial or {})
        self.grab_set()  # Modal

    def _build_ui(self, grade_inicial: Dict[str, int]):
        header = tk.Label(
            self,
            text=f"Defina a grade (Total deve ser {self.quantidade_total})\n↩️ Enter: salvar se total bater | ⇥ Tab: próximo campo",
            font=TELEGRAM_FONTS['title'],
            fg=TELEGRAM_COLORS['primary'],
            bg=TELEGRAM_COLORS['white']
        )
        header.grid(row=0, column=0, columnspan=2, pady=(12, 6), padx=12)

        container = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        container.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 6))

        # Coluna lateral esquerda para presets (uma única coluna)
        presets_col = tk.Frame(container, bg=TELEGRAM_COLORS['white'])
        presets_col.grid(row=0, column=0, rowspan=999, sticky="nsw", padx=(0, 12))

        # Botões de presets (adulto) empilhados verticalmente
        btn_pmg_gg = tk.Button(
            presets_col,
            text="Preset: P/M/G/GG (1-1-1-1)",
            command=lambda: self._preset_pmg_gg(1),
            bg=TELEGRAM_COLORS['light_gray'], fg=TELEGRAM_COLORS['text'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        )
        btn_pmg_gg.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        btn_pmg = tk.Button(
            presets_col,
            text="Preset: P/M/G (1-1-1)",
            command=lambda: self._preset_pmg(1),
            bg=TELEGRAM_COLORS['light_gray'], fg=TELEGRAM_COLORS['text'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        )
        btn_pmg.grid(row=1, column=0, sticky="ew")

        # Ordem por categoria: se infantil, usa lista infantil; caso contrário, adulto
        cat = (self.categoria or "").lower()
        if "infantil" in cat:
            ordem_exibicao = TAMANHOS_INFANTIL
        else:
            ordem_exibicao = TAMANHOS_ADULTO
        self._ordem = ordem_exibicao

        # Duas colunas para tamanhos (label/entry) após a coluna de presets
        self._inputs = []  # guarda widgets de entrada na ordem
        for i, tam in enumerate(ordem_exibicao):
            tk.Label(
                container,
                text=tam,
                font=TELEGRAM_FONTS['body_bold'],
                fg=TELEGRAM_COLORS['text'],
                bg=TELEGRAM_COLORS['white']
            ).grid(row=i, column=1, sticky="w", pady=3)

            var = tk.IntVar(value=int(grade_inicial.get(tam, 0)))
            self.vars[tam] = var
            # Entry sem setas, com validação numérica
            vcmd = (self.register(self._validate_int), '%P', tam)
            ent = tk.Entry(
                container,
                textvariable=var,
                width=6,
                font=TELEGRAM_FONTS['body'],
                validate='key',
                validatecommand=vcmd
            )
            ent.grid(row=i, column=2, padx=(8, 0), pady=3, sticky="w")
            self._inputs.append(ent)

            # Atualiza ao digitar manualmente
            var.trace_add('write', lambda *args, t=tam: self._on_var_change(t))

            # Mouse wheel: incrementa/decrementa respeitando limites
            def _mw_up(e, t=tam):
                self._inc_dec(t, +1)
                return "break"
            def _mw_down(e, t=tam):
                self._inc_dec(t, -1)
                return "break"
            ent.bind('<MouseWheel>', lambda e, t=tam: (_mw_up(e, t) if e.delta > 0 else _mw_down(e, t)))
            ent.bind('<Button-4>', _mw_up)
            ent.bind('<Button-5>', _mw_down)

        # Presets e ações rápidas
        actions = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        actions.grid(row=2, column=0, columnspan=2, pady=(4, 2))

        tk.Button(
            actions, text="1-1-1 (P/M/G)", command=lambda: self._preset_pmg(1),
            bg=TELEGRAM_COLORS['light_gray'], fg=TELEGRAM_COLORS['text'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            actions, text="2-2-2 (P/M/G)", command=lambda: self._preset_pmg(2),
            bg=TELEGRAM_COLORS['light_gray'], fg=TELEGRAM_COLORS['text'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            actions, text="Distribuir restante", command=self._distribuir_restante,
            bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            actions, text="Limpar", command=self._limpar_todos,
            bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=8, pady=4
        ).pack(side=tk.LEFT, padx=4)

        # Enter global: tenta salvar, não avança foco
        self.bind('<Return>', self._on_enter)
        # Escape: cancelar
        self.bind('<Escape>', lambda e: self.destroy())

        # Rodapé com totalizador
        self.total_var = tk.StringVar(value=self._calc_total_text())
        self.total_label = tk.Label(
            self,
            textvariable=self.total_var,
            font=TELEGRAM_FONTS['body_bold'],
            fg=TELEGRAM_COLORS['info'],
            bg=TELEGRAM_COLORS['white']
        )
        self.total_label.grid(row=3, column=0, columnspan=2, pady=(6, 4))

        # Botões
        btns = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        btns.grid(row=4, column=0, columnspan=2, pady=(4, 12))

        self.btn_salvar = tk.Button(
            btns,
            text="💾 Salvar Grade",
            command=self._salvar,
            bg=TELEGRAM_COLORS['success'],
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'],
            relief='flat', padx=12, pady=6
        )
        self.btn_salvar.pack(side=tk.LEFT, padx=6)

        btn_cancelar = tk.Button(
            btns,
            text="Cancelar",
            command=self.destroy,
            bg=TELEGRAM_COLORS['error'],
            fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'],
            relief='flat', padx=12, pady=6
        )
        btn_cancelar.pack(side=tk.LEFT, padx=6)

        self._on_change()  # inicializar estado
        # Focar primeiro campo e selecionar para digitação mais rápida
        if self._inputs:
            try:
                self._inputs[0].focus_set()
                self._inputs[0].selection_range(0, tk.END)
            except Exception:
                pass

    def _calc_total(self) -> int:
        total = 0
        for var in self.vars.values():
            try:
                total += int(var.get())
            except Exception:
                pass
        return total

    def _calc_total_text(self) -> str:
        return f"Total selecionado: {self._calc_total()} / {self.quantidade_total}"

    def _on_change(self):
        total = self._calc_total()
        self.total_var.set(self._calc_total_text())
        # feedback visual
        if total == self.quantidade_total:
            self.total_label.config(fg=TELEGRAM_COLORS['success'])
            self.btn_salvar.config(state=tk.NORMAL)
        else:
            self.total_label.config(fg=TELEGRAM_COLORS['error'])
            self.btn_salvar.config(state=tk.DISABLED)

    def _on_var_change(self, tam: str):
        """Chamado quando um campo muda; aplica cap para não estourar o total."""
        try:
            v = max(0, int(self.vars[tam].get()))
        except Exception:
            v = 0
        # Recalcular total e cap se exceder
        total_sem_tam = sum(int(self.vars[t].get()) if t != tam else 0 for t in self.vars)
        max_para_tam = max(0, self.quantidade_total - total_sem_tam)
        if v > max_para_tam:
            self.vars[tam].set(max_para_tam)
        self._on_change()

    def _inc_dec(self, tam: str, delta: int):
        try:
            atual = int(self.vars[tam].get())
        except Exception:
            atual = 0
        novo = max(0, atual + delta)
        # Aplicar cap via _on_var_change
        self.vars[tam].set(novo)

    def _salvar(self):
        total = self._calc_total()
        if total != self.quantidade_total:
            messagebox.showwarning(
                "Atenção",
                f"A soma da grade ({total}) deve ser igual à quantidade do produto ({self.quantidade_total})."
            )
            return

        grade: Dict[str, int] = {}
        for tam, var in self.vars.items():
            try:
                v = int(var.get())
            except Exception:
                v = 0
            if v > 0:
                grade[tam] = v

        try:
            salvar_grade(self.produto_index, grade)
            # Preparar callback e destruir antes de chamar para evitar conflitos de janela/grab
            cb = self.on_saved
            idx = self.produto_index
            payload = grade.copy()
            # Fechar primeiro
            self.destroy()
            # Disparar callback no próximo ciclo do loop de eventos
            if cb:
                try:
                    self.master.after(0, lambda: cb(idx, payload))
                except Exception:
                    # Fallback direto
                    cb(idx, payload)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar grade: {e}")

    def _validate_int(self, proposed: str, tam: str) -> bool:
        """Validação numérica para os Entries. Mantém apenas inteiros >= 0 e aplica cap.
        proposed: conteúdo proposto no Entry
        tam: tamanho associado
        """
        if proposed == "":
            # Permite vazio durante a digitação, trata como 0
            self.vars[tam].set(0)
            self._on_change()
            return True
        if not proposed.isdigit():
            return False
        # Aplicar cap pelo handler padrão
        try:
            val = int(proposed)
        except Exception:
            val = 0
        # Defere o ajuste final ao trace (_on_var_change)
        return True

    def _on_enter(self, event=None):
        """Enter: tenta salvar se total estiver correto. Não altera foco."""
        if self._calc_total() == self.quantidade_total:
            self._salvar()
        # Impedir propagação para o root (que também binda <Return>)
        return "break"

    # Ações rápidas
    def _limpar_todos(self):
        for t in self.vars:
            self.vars[t].set(0)
        self._on_change()

    def _preset_pmg(self, base: int):
        """Aplica padrão P/M/G com quantidade 'base' cada, respeitando o total."""
        alvo = ["P", "M", "G"]
        # Zerar antes de aplicar
        for t in self.vars:
            self.vars[t].set(0)
        restante = self.quantidade_total
        for t in alvo:
            if t in self.vars and restante > 0:
                q = min(base, restante)
                self.vars[t].set(q)
                restante -= q
        self._on_change()

    def _preset_pmg_gg(self, base: int = 1):
        """Aplica padrão P/M/G/GG com quantidade 'base' cada, respeitando o total."""
        alvo = ["P", "M", "G", "GG"]
        # Zerar antes de aplicar
        for t in self.vars:
            self.vars[t].set(0)
        restante = self.quantidade_total
        for t in alvo:
            if t in self.vars and restante > 0:
                q = min(base, restante)
                self.vars[t].set(q)
                restante -= q
        self._on_change()

    def _distribuir_restante(self):
        """Distribui o restante priorizando tamanhos conforme a categoria atual."""
        restante = self.quantidade_total - self._calc_total()
        if restante <= 0:
            return
        # Preferência por categoria
        cat = (self.categoria or "").lower()
        if "infantil" in cat:
            preferencia = [
                "M", "P", "G", "GG", "PP",
                "1", "2", "3", "4", "6", "8", "10", "12", "14", "16", "18",
                "6M", "9M", "12M", "18M",
            ]
        else:
            preferencia = ["M", "P", "G", "GG", "XG", "EXG", "PP"]
        ordem = [t for t in preferencia if t in self._ordem] + [t for t in self._ordem if t not in preferencia]
        idx = 0
        n = len(ordem)
        while restante > 0 and n > 0:
            t = ordem[idx % n]
            # Cap é aplicado por _on_var_change via set
            self.vars[t].set(int(self.vars[t].get()) + 1)
            novo_total = self._calc_total()
            if novo_total <= self.quantidade_total:
                restante -= 1
            idx += 1
        self._on_change()
