"""Interface gráfica para reparar PDFs problemáticos usando qpdf ou pypdf.

Requisitos:
    - Python 3
    - Tkinter (já incluído na instalação padrão do Python no Windows)
    - pypdf  (pip install pypdf)
    - Opcional: qpdf (instalação via conda/choco ou binário oficial)

Execução:
    python repdf.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Tkinter é necessário para esta ferramenta.") from exc

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None  # type: ignore
    PdfWriter = None  # type: ignore


@dataclass
class RepairResult:
    entrada: Path
    saida: Path
    sucesso: bool
    mensagem: str
    modo: str


class PDFRepairApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Reparador de PDF")
        self.root.geometry("640x420")

        self.mode_var = tk.StringVar(value="qpdf")
        self._create_widgets()
        self.pdf_paths: List[Path] = []

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        intro = ttk.Label(
            main_frame,
            text=(
                "Selecione um ou mais PDFs para reparo. "
                "A saída será salva com sufixo _reparado.pdf no mesmo diretório."
            ),
            wraplength=600,
            justify=tk.LEFT,
        )
        intro.pack(anchor=tk.W, pady=(0, 12))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.select_button = ttk.Button(btn_frame, text="Selecionar PDFs", command=self._on_select)
        self.select_button.pack(side=tk.LEFT)

        self.repair_button = ttk.Button(
            btn_frame, text="Reparar", command=self._start_repair_thread, state=tk.DISABLED
        )
        self.repair_button.pack(side=tk.LEFT, padx=(12, 0))

        self.clear_button = ttk.Button(btn_frame, text="Limpar lista", command=self._clear_list)
        self.clear_button.pack(side=tk.LEFT, padx=(12, 0))

        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(mode_frame, text="Modo de reparo:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="qpdf (rápido)",
            variable=self.mode_var,
            value="qpdf",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            mode_frame,
            text="PyPDF (compatível)",
            variable=self.mode_var,
            value="pypdf",
        ).pack(side=tk.LEFT, padx=(8, 0))

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("arquivo", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("status", text="Status")
        self.tree.column("arquivo", width=420, anchor=tk.W)
        self.tree.column("status", width=180, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar(value="Selecione arquivos para iniciar.")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="#444")
        status_label.pack(anchor=tk.W, pady=(8, 0))

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _on_select(self) -> None:
        initialdir = str(Path.home())
        selected = filedialog.askopenfilenames(
            parent=self.root,
            title="Escolha PDFs para reparar",
            initialdir=initialdir,
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if not selected:
            return

        self.pdf_paths = [Path(path) for path in selected]
        self._refresh_tree()
        self.status_var.set(f"{len(self.pdf_paths)} arquivo(s) prontos para reparo.")
        self.repair_button.config(state=tk.NORMAL)

    def _clear_list(self) -> None:
        self.pdf_paths.clear()
        self._refresh_tree()
        self.status_var.set("Selecione arquivos para iniciar.")
        self.repair_button.config(state=tk.DISABLED)

    def _refresh_tree(self, results: Optional[List[RepairResult]] = None) -> None:
        self.tree.delete(*self.tree.get_children())
        if results is None:
            for path in self.pdf_paths:
                self.tree.insert("", tk.END, values=(path.name, "aguardando"))
        else:
            for result in results:
                status = f"{result.modo}: ok" if result.sucesso else f"{result.modo}: erro"
                exibido = result.saida.name if result.sucesso else result.entrada.name
                self.tree.insert("", tk.END, values=(exibido, status))

    def _start_repair_thread(self) -> None:
        if not self.pdf_paths:
            messagebox.showinfo("Reparo de PDF", "Selecione ao menos um arquivo.")
            return

        self.repair_button.config(state=tk.DISABLED)
        self.select_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.status_var.set("Processando... aguarde.")

        worker = threading.Thread(target=self._run_repair, daemon=True)
        worker.start()

    def _run_repair(self) -> None:
        results = []
        modo = self.mode_var.get()
        for entrada in self.pdf_paths:
            saida = entrada.with_name(f"{entrada.stem}_reparado.pdf")
            if modo == "pypdf":
                resultado = reparar_com_pypdf(entrada, saida)
            else:
                resultado = reparar_com_qpdf(entrada, saida)
            results.append(resultado)

        self.root.after(0, self._finalize_repair, results)

    def _finalize_repair(self, results: List[RepairResult]) -> None:
        self._refresh_tree(results)
        sucesso = sum(1 for r in results if r.sucesso)
        falhas = len(results) - sucesso
        self.status_var.set(f"Finalizado: {sucesso} sucesso(s), {falhas} falha(s).")
        self.repair_button.config(state=tk.NORMAL if self.pdf_paths else tk.DISABLED)
        self.select_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
        if falhas:
            messagebox.showwarning(
                "Reparo concluído",
                "Alguns arquivos não puderam ser reparados. Verifique os detalhes no console.",
            )
        else:
            messagebox.showinfo("Reparo concluído", "Todos os PDFs foram reparados com sucesso!")


# ----------------------------------------------------------------------
# Funções utilitárias
# ----------------------------------------------------------------------

def reparar_com_qpdf(entrada: Path, saida: Path) -> RepairResult:
    comando = [
        "qpdf",
        "--stream-data=uncompress",
        "--object-streams=disable",
        str(entrada),
        str(saida),
    ]

    try:
        proc = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        mensagem = "qpdf não encontrado. Instale com 'conda install -c conda-forge qpdf' ou adicione ao PATH."
        print(mensagem)
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="qpdf")
    except Exception as exc:  # pragma: no cover - erros de subprocesso
        mensagem = f"Erro ao executar qpdf: {exc}"
        print(mensagem)
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="qpdf")

    if proc.returncode != 0:
        mensagem = proc.stderr.strip() or "qpdf retornou erro desconhecido"
        print(f"❌ Falha ({entrada.name}): {mensagem}")
        if saida.exists():
            saida.unlink(missing_ok=True)
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="qpdf")

    if not saida.exists() or saida.stat().st_size == 0:
        mensagem = "Arquivo de saída não gerado"
        print(f"❌ Falha ({entrada.name}): {mensagem}")
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="qpdf")

    tamanho_kb = saida.stat().st_size / 1024
    mensagem = f"Reparado com sucesso ({tamanho_kb:.1f} KB)"
    print(f"🎉 {mensagem}: {saida}")
    return RepairResult(entrada=entrada, saida=saida, sucesso=True, mensagem=mensagem, modo="qpdf")


def reparar_com_pypdf(entrada: Path, saida: Path) -> RepairResult:
    if PdfReader is None or PdfWriter is None:
        mensagem = "Pacote 'pypdf' não encontrado. Instale com 'pip install pypdf'."
        print(mensagem)
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="pypdf")

    try:
        reader = PdfReader(str(entrada), strict=False)
    except Exception as exc:
        mensagem = f"Falha ao abrir PDF: {exc}"
        print(f"❌ {mensagem}")
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="pypdf")

    writer = PdfWriter()
    paginas_validas = 0

    for idx, page in enumerate(reader.pages, start=1):
        try:
            writer.add_page(page)
            paginas_validas += 1
            print(f"✅ PyPDF adicionou página {idx}")
        except Exception as exc:
            print(f"⚠️  PyPDF pulou página {idx}: {exc}")

    if paginas_validas == 0:
        mensagem = "Nenhuma página válida encontrada"
        print(f"❌ {mensagem} ({entrada.name})")
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="pypdf")

    try:
        with saida.open("wb") as fh:
            writer.write(fh)
    except Exception as exc:
        mensagem = f"Erro ao salvar PDF: {exc}"
        print(f"❌ {mensagem}")
        if saida.exists():
            saida.unlink(missing_ok=True)
        return RepairResult(entrada=entrada, saida=saida, sucesso=False, mensagem=mensagem, modo="pypdf")

    tamanho_kb = saida.stat().st_size / 1024
    mensagem = f"PyPDF salvou {paginas_validas} página(s) ({tamanho_kb:.1f} KB)"
    print(f"🎉 {mensagem}: {saida}")
    return RepairResult(entrada=entrada, saida=saida, sucesso=True, mensagem=mensagem, modo="pypdf")


def main() -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    app = PDFRepairApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
