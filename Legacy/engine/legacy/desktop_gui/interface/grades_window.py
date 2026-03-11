"""
📊 JANELA DE VISUALIZAÇÃO/EDIÇÃO DE GRADES
=========================================

Exibe as grades já inseridas em uma tabela estilo planilha, permite editar os tamanhos/quantidades,
deletar itens e salvar as alterações. Também oferece ação para limpar todas as grades.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Tuple

from ..core.file_manager import carregar_grades, salvar_grades, limpar_grades
from ..config.theme import TELEGRAM_COLORS, TELEGRAM_FONTS


class GradesWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, nomes_map: Dict[str, str] | None = None):
        super().__init__(master)
        self.title("Grades Cadastradas")
        self.configure(bg=TELEGRAM_COLORS['white'])
        self.resizable(True, True)
        self.minsize(700, 400)

        self._nomes_map = nomes_map or {}
        self._grades: Dict[str, dict] = {}

        self._build_ui()
        self._load_data()
        self.grab_set()

    def _build_ui(self):
        # Header
        header = tk.Label(
            self,
            text="📊 EDITOR DE GRADES\nDê duplo clique em 'Tamanhos' para editar (formato TAM=QTD por linha)",
            font=TELEGRAM_FONTS['title'],
            fg=TELEGRAM_COLORS['primary'],
            bg=TELEGRAM_COLORS['white']
        )
        header.pack(fill=tk.X, padx=12, pady=(12, 6))

        # Tree
        frame = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        cols = ("index", "nome", "total", "tamanhos")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        self.tree.heading("index", text="#")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("total", text="Total")
        self.tree.heading("tamanhos", text="Tamanhos")
        self.tree.column("index", width=40, anchor="center")
        self.tree.column("nome", width=200)
        self.tree.column("total", width=60, anchor="e")
        self.tree.column("tamanhos", width=360)

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Bind edição
        self.tree.bind("<Double-1>", self._on_double_click)

        # Botões
        actions = tk.Frame(self, bg=TELEGRAM_COLORS['white'])
        actions.pack(fill=tk.X, padx=12, pady=(4, 12))

        self.btn_salvar = tk.Button(
            actions, text="💾 Salvar Alterações", command=self._salvar_alteracoes,
            bg=TELEGRAM_COLORS['success'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=6
        )
        self.btn_salvar.pack(side=tk.LEFT, padx=4)

        self.btn_deletar = tk.Button(
            actions, text="🗑️ Deletar Selecionado(s)", command=self._deletar_selecionados,
            bg=TELEGRAM_COLORS['error'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=6
        )
        self.btn_deletar.pack(side=tk.LEFT, padx=4)

        self.btn_limpar = tk.Button(
            actions, text="🧹 Limpar Todas as Grades", command=self._limpar_todas,
            bg=TELEGRAM_COLORS['warning'], fg=TELEGRAM_COLORS['white'],
            font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=6
        )
        self.btn_limpar.pack(side=tk.LEFT, padx=4)

    def _load_data(self):
        self._grades = carregar_grades() or {}
        # preencher tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx_str, reg in self._grades.items():
            sizes = reg.get("sizes", {}) if isinstance(reg, dict) else {}
            total = int(reg.get("total", sum(int(v) for v in sizes.values()))) if isinstance(reg, dict) else 0
            nome = self._nomes_map.get(str(idx_str), "")
            tamanhos_txt = self._sizes_to_text(sizes)
            self.tree.insert("", "end", values=(idx_str, nome, total, tamanhos_txt))

    # Helpers de conversão
    @staticmethod
    def _sizes_to_text(sizes: Dict[str, int]) -> str:
        # Ex: "P=1; M=2; 42=1"
        parts = []
        for k, v in sizes.items():
            try:
                vv = int(v)
            except Exception:
                vv = 0
            if vv > 0:
                parts.append(f"{k}={vv}")
        return "; ".join(parts)

    @staticmethod
    def _text_to_sizes(texto: str) -> Tuple[Dict[str, int], int]:
        sizes: Dict[str, int] = {}
        total = 0
        texto = (texto or "").strip()
        if not texto:
            return sizes, total
        # Aceitar separadores ; , e quebras de linha
        raw = []
        for part in texto.replace("\n", ";").split(";"):
            for sub in part.split(","):
                s = sub.strip()
                if s:
                    raw.append(s)
        for item in raw:
            if "=" not in item:
                # Tolerar formato "P 2" (espaço)
                if " " in item:
                    k, v = item.split(" ", 1)
                else:
                    raise ValueError("Formato inválido. Use TAM=QTD por item.")
            else:
                k, v = item.split("=", 1)
            k = k.strip()
            v = v.strip()
            if not v.isdigit():
                raise ValueError(f"Quantidade inválida para {k}: {v}")
            q = int(v)
            if q < 0:
                raise ValueError(f"Quantidade negativa para {k}")
            if q == 0:
                continue
            sizes[k] = q
            total += q
        return sizes, total

    # Eventos/ações
    def _on_double_click(self, event):
        # Editar célula 'tamanhos'
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item_id or col != "#4":  # tamanhos é a coluna 4
            return
        valores = self.tree.item(item_id, "values")
        idx_str = valores[0]
        tamanhos_txt = valores[3]
        self._abrir_editor_tamanhos(item_id, idx_str, tamanhos_txt)

    def _abrir_editor_tamanhos(self, item_id, idx_str: str, tamanhos_txt: str):
        editor = tk.Toplevel(self)
        editor.title(f"Editar Tamanhos - Item {idx_str}")
        editor.configure(bg=TELEGRAM_COLORS['white'])
        editor.geometry("500x300")
        editor.transient(self)
        editor.grab_set()

        tk.Label(editor, text="Edite os tamanhos (um por linha, formato TAM=QTD)",
                 font=TELEGRAM_FONTS['body_bold'], bg=TELEGRAM_COLORS['white']).pack(anchor="w", padx=12, pady=(12, 6))

        txt = tk.Text(editor, height=10, font=("Consolas", 11))
        # Converter o texto com separadores ; para linhas
        linhas = [p.strip() for p in (tamanhos_txt or "").replace(";", "\n").split("\n") if p.strip()]
        txt.insert("1.0", "\n".join(linhas))
        txt.pack(fill=tk.BOTH, expand=True, padx=12)

        status = tk.Label(editor, text="", font=TELEGRAM_FONTS['small'], fg=TELEGRAM_COLORS['info'], bg=TELEGRAM_COLORS['white'])
        status.pack(fill=tk.X, padx=12, pady=(4, 0))

        def salvar_local():
            try:
                sizes, total = self._text_to_sizes(txt.get("1.0", tk.END))
                # Atualizar tree e cache
                valores = list(self.tree.item(item_id, "values"))
                valores[2] = str(total)
                valores[3] = self._sizes_to_text(sizes)
                self.tree.item(item_id, values=valores)
                # Atualizar cache _grades
                self._grades[str(idx_str)] = {
                    "sizes": {str(k): int(v) for k, v in sizes.items()},
                    "total": int(total),
                    "timestamp": self._grades.get(str(idx_str), {}).get("timestamp"),
                }
                status.config(text="✅ Atualizado (ainda não salvo em disco)", fg=TELEGRAM_COLORS['success'])
            except Exception as e:
                status.config(text=f"❌ {e}", fg=TELEGRAM_COLORS['error'])

        btns = tk.Frame(editor, bg=TELEGRAM_COLORS['white'])
        btns.pack(fill=tk.X, padx=12, pady=8)
        tk.Button(btns, text="Aplicar", command=salvar_local,
                  bg=TELEGRAM_COLORS['info'], fg=TELEGRAM_COLORS['white'],
                  font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=4).pack(side=tk.LEFT)
        tk.Button(btns, text="Fechar", command=editor.destroy,
                  bg=TELEGRAM_COLORS['light_gray'], fg=TELEGRAM_COLORS['text'],
                  font=TELEGRAM_FONTS['button'], relief='flat', padx=10, pady=4).pack(side=tk.LEFT, padx=6)

    def _deletar_selecionados(self):
        itens = self.tree.selection()
        if not itens:
            return
        if not messagebox.askyesno("Confirmar", f"Deletar {len(itens)} registro(s) de grade?"):
            return
        for it in itens:
            valores = self.tree.item(it, "values")
            idx_str = str(valores[0])
            self.tree.delete(it)
            if idx_str in self._grades:
                del self._grades[idx_str]

    def _salvar_alteracoes(self):
        try:
            # Recoletar dados da tree para salvar estado atual
            out: Dict[str, dict] = {}
            for it in self.tree.get_children():
                idx_str, _nome, total, tamanhos_txt = self.tree.item(it, "values")
                try:
                    sizes, total_calc = self._text_to_sizes(tamanhos_txt)
                except Exception as e:
                    messagebox.showerror("Erro", f"Item {idx_str}: {e}")
                    return
                out[str(idx_str)] = {
                    "sizes": {str(k): int(v) for k, v in sizes.items()},
                    "total": int(total_calc),
                }
            salvar_grades(out)
            messagebox.showinfo("Sucesso", "Grades salvas com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")

    def _limpar_todas(self):
        if not messagebox.askyesno("Confirmar", "Apagar TODAS as grades cadastradas? Esta ação não pode ser desfeita."):
            return
        try:
            limpar_grades()
            self._load_data()
            messagebox.showinfo("Sucesso", "Todas as grades foram apagadas.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar: {e}")
