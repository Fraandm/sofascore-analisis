"""Ventana de Estudio de previas."""

from __future__ import annotations

import re
import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional

from . import preview


class PreviewWindow(tk.Toplevel):
    def __init__(
        self,
        app: Any,
        analysis: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(app.root)
        self.app = app
        self.analysis = analysis
        self.summary = summary
        self.title("Estudio de previas · SofaScore")
        self.configure(background=app.palette["bg"])
        self.geometry(self._geometry(1000, 720))
        self.minsize(760, 520)
        self.transient(app.root)
        self.generated_markdown = preview.render_markdown(analysis, summary)
        self.generated_html = preview.render_html(analysis, summary)
        self._build()
        self.lift()
        self.focus_force()

    def _geometry(self, width: int, height: int) -> str:
        root = self.app.root
        x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
        y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _build(self) -> None:
        palette = self.app.palette
        toolbar = ttk.Frame(self, padding=(12, 10, 12, 6))
        toolbar.pack(fill="x")
        ttk.Label(
            toolbar,
            text="Estudio de previas",
            style="Team.TLabel",
        ).pack(side="left")
        ttk.Label(
            toolbar,
            text="Texto listo para guardar o abrir como HTML",
            style="Small.TLabel",
        ).pack(side="left", padx=(10, 0))
        ttk.Button(
            toolbar, text="Cerrar", command=self.destroy
        ).pack(side="right")
        ttk.Button(
            toolbar, text="Abrir HTML", command=self._open_html
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar, text="Guardar HTML", command=lambda: self._save("html")
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar, text="Guardar Markdown", command=lambda: self._save("md")
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar, text="Copiar", command=self._copy
        ).pack(side="right", padx=(0, 6))

        body = ttk.Frame(self, padding=(12, 0, 12, 6))
        body.pack(fill="both", expand=True)
        self.text = tk.Text(
            body,
            wrap="word",
            background=palette["field"],
            foreground=palette["fg"],
            insertbackground=palette["fg"],
            relief="flat",
            padx=18,
            pady=14,
            font=("Segoe UI", 10),
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.text.tag_configure(
            "h1",
            font=("Segoe UI", 18, "bold"),
            foreground=palette["fg"],
            spacing3=8,
        )
        self.text.tag_configure(
            "h2",
            font=("Segoe UI", 11, "bold"),
            foreground=palette["accent"],
            spacing1=12,
            spacing3=4,
        )
        self.text.tag_configure(
            "bullet",
            lmargin1=16,
            lmargin2=24,
            spacing1=2,
        )
        self.text.tag_configure(
            "muted", foreground=palette["muted"], font=("Segoe UI", 9)
        )
        self.text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.text.tag_configure("italic", font=("Segoe UI", 10, "italic"))
        self.text.tag_configure("table", font=("Consolas", 9))
        self._render_text()
        self.text.configure(state="disabled")

        footer = ttk.Frame(self, padding=(12, 0, 12, 10))
        footer.pack(fill="x")
        self.status_var = tk.StringVar(value="")
        ttk.Label(
            footer, textvariable=self.status_var, style="Small.TLabel"
        ).pack(side="left")
        ttk.Label(
            footer,
            text="El HTML incluye estilos y se puede imprimir como PDF desde el navegador.",
            style="Small.TLabel",
        ).pack(side="right")

    def _insert_inline(self, text: str, *tags: str) -> None:
        parts = re.split(r"(\*\*.+?\*\*|_[^_]+_)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                self.text.insert("end", part[2:-2], (*tags, "bold"))
            elif part.startswith("_") and part.endswith("_") and len(part) > 2:
                self.text.insert("end", part[1:-1], (*tags, "italic"))
            else:
                self.text.insert("end", part, tags)

    def _render_text(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for raw in self.generated_markdown.splitlines():
            line = raw.rstrip()
            if line.startswith("# "):
                self.text.insert("end", line[2:].replace("**", "") + "\n", "h1")
            elif line.startswith("## "):
                self.text.insert("end", line[3:].replace("**", "") + "\n", "h2")
            elif line.startswith("- "):
                self.text.insert("end", "• ", "bullet")
                self._insert_inline(line[2:], "bullet")
                self.text.insert("end", "\n")
            elif line.startswith("|"):
                cells = [cell.strip().replace("**", "") for cell in line.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                    continue
                self.text.insert("end", "   ".join(cells) + "\n", "table")
            elif line.startswith("---"):
                self.text.insert("end", "─" * 60 + "\n", "muted")
            else:
                self._insert_inline(line)
                self.text.insert("end", "\n")
        self.text.configure(state="disabled")

    def _safe_name(self) -> str:
        home = preview.build_preview(self.analysis, self.summary)["home"]
        away = preview.build_preview(self.analysis, self.summary)["away"]
        name = f"previa_{home}_vs_{away}".lower()
        return re.sub(r"[^a-z0-9]+", "_", name).strip("_")[:80] or "previa"

    def _save(self, kind: str) -> None:
        extension = ".html" if kind == "html" else ".md"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar previa",
            defaultextension=extension,
            initialfile=self._safe_name() + extension,
            filetypes=(
                ("HTML", "*.html")
                if kind == "html"
                else ("Markdown", "*.md"),
                ("Todos los archivos", "*.*"),
            ),
        )
        if not path:
            return
        try:
            Path(path).write_text(
                self.generated_html if kind == "html" else self.generated_markdown,
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)
            return
        self.status_var.set(f"Guardado: {path}")

    def _open_html(self) -> None:
        try:
            directory = Path(tempfile.gettempdir()) / "sofascore-previews"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (self._safe_name() + ".html")
            path.write_text(self.generated_html, encoding="utf-8")
            webbrowser.open(path.as_uri())
            self.status_var.set(f"Abierto en el navegador: {path}")
        except OSError as exc:
            messagebox.showerror("No se pudo abrir", str(exc), parent=self)

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.generated_markdown)
        self.status_var.set("Markdown copiado al portapapeles.")

