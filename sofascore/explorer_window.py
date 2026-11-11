"""Explorador del historial local y controles de la API."""

from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List

from .storage import HistoryStore


def _day_text(value: Any) -> str:
    text = str(value or "")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _status_text(value: Any) -> str:
    return {
        "finished": "Finalizado",
        "inprogress": "En vivo",
        "live": "En vivo",
        "halftime": "Descanso",
        "notstarted": "Próximo",
        "delayed": "Retrasado",
    }.get(str(value or ""), str(value or ""))


class ExplorerWindow(tk.Toplevel):
    def __init__(self, app: Any, store: HistoryStore) -> None:
        super().__init__(app.root)
        self.app = app
        self.store = store
        self.title("Explorador de datos · SofaScore")
        self.configure(background=app.palette["bg"])
        self.geometry(self._geometry(1160, 720))
        self.minsize(900, 560)
        self.transient(app.root)
        self._build()
        self.refresh()
        self.lift()
        self.focus_force()

    def _geometry(self, width: int, height: int) -> str:
        root = self.app.root
        x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
        y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _build(self) -> None:
        header = ttk.Frame(self, padding=(14, 12, 14, 6))
        header.pack(fill="x")
        ttk.Label(
            header, text="Explorador de datos", style="Team.TLabel"
        ).pack(side="left")
        ttk.Label(
            header,
            text="Partidos y predicciones guardadas en tu equipo",
            style="Small.TLabel",
        ).pack(side="left", padx=(10, 0))
        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")
        ttk.Button(
            header, text="Borrar historial", command=self._clear_history
        ).pack(side="right", padx=(0, 6))

        api_frame = ttk.LabelFrame(self, text="API local", padding=10)
        api_frame.pack(fill="x", padx=14, pady=(0, 8))
        self.api_status = tk.StringVar(value="API local detenida.")
        ttk.Label(
            api_frame, textvariable=self.api_status, style="Small.TLabel"
        ).pack(side="left")
        self.api_toggle_btn = ttk.Button(
            api_frame, text="Iniciar API", command=self._toggle_api
        )
        self.api_toggle_btn.pack(side="right")
        ttk.Label(
            api_frame,
            text="Solo escucha en 127.0.0.1 · uso personal",
            style="Small.TLabel",
        ).pack(side="right", padx=(0, 10))

        filters = ttk.Frame(self, padding=(14, 0, 14, 6))
        filters.pack(fill="x")
        ttk.Label(filters, text="Buscar").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.pack(side="left", fill="x", expand=True, padx=(4, 10))
        search.bind("<Return>", lambda _event: self.refresh())
        ttk.Label(filters, text="Estado").pack(side="left")
        self.status_filter = tk.StringVar(value="Todos")
        combo = ttk.Combobox(
            filters,
            textvariable=self.status_filter,
            values=("Todos", "finished", "inprogress", "notstarted"),
            state="readonly",
            width=13,
        )
        combo.pack(side="left", padx=(4, 8))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Button(filters, text="Buscar", command=self.refresh).pack(side="left")
        ttk.Button(
            filters, text="Exportar CSV", command=self._export_csv
        ).pack(side="left", padx=(6, 0))

        table_frame = ttk.Frame(self, padding=(14, 0, 14, 6))
        table_frame.pack(fill="both", expand=True)
        columns = (
            "day",
            "competition",
            "home",
            "away",
            "score",
            "status",
            "pick",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        for column, heading, width, anchor in (
            ("day", "Fecha", 90, "w"),
            ("competition", "Competición", 170, "w"),
            ("home", "Local", 170, "w"),
            ("away", "Visitante", 170, "w"),
            ("score", "Marcador", 75, "center"),
            ("status", "Estado", 90, "w"),
            ("pick", "Pronóstico guardado", 190, "w"),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(
                column, width=width, anchor=anchor, stretch=column in ("home", "away")
            )
        yscroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_selected)

        footer = ttk.Frame(self, padding=(14, 0, 14, 10))
        footer.pack(fill="x")
        self.footer_var = tk.StringVar(value="")
        ttk.Label(
            footer, textvariable=self.footer_var, style="Small.TLabel"
        ).pack(side="left")
        self.refresh_api_state()

    def refresh(self) -> None:
        status = "" if self.status_filter.get() == "Todos" else self.status_filter.get()
        rows = self.store.list_matches(
            query=self.search_var.get().strip(),
            status=status,
            limit=500,
        )
        predictions = self.store.latest_predictions(
            [row["id"] for row in rows if row.get("id") is not None]
        )
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            prediction = predictions.get(row["id"]) or {}
            pick = "—"
            if prediction:
                probabilities = {
                    "local": float(prediction.get("prob_home") or 0.0),
                    "empate": float(prediction.get("prob_draw") or 0.0),
                    "visitante": float(prediction.get("prob_away") or 0.0),
                }
                side = max(probabilities, key=probabilities.get)
                name = {
                    "local": row.get("home_name") or "Local",
                    "empate": "Empate",
                    "visitante": row.get("away_name") or "Visitante",
                }[side]
                pick = f"{name} · {probabilities[side] * 100:.0f}%"
            score = (
                f"{row.get('home_score')}-{row.get('away_score')}"
                if row.get("home_score") is not None
                and row.get("away_score") is not None
                else "—"
            )
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    _day_text(row.get("day")),
                    row.get("tournament") or "",
                    row.get("home_name") or "",
                    row.get("away_name") or "",
                    score,
                    _status_text(row.get("status")),
                    pick,
                ),
            )
        self.footer_var.set(
            (f"{len(rows)} partido" if len(rows) == 1 else f"{len(rows)} partidos")
            + f" · {len(predictions)} con pronóstico · "
            f"{self.store.path}"
        )

    def _open_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        match_id = int(selection[0])
        self.app._select_match_by_id(match_id)
        if not any(item.get("id") == match_id for item in self.app.matches):
            self.footer_var.set(
                "Partido fuera de la fecha cargada. Carga su fecha para "
                "abrirlo en la vista principal."
            )

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar historial de partidos",
            defaultextension=".csv",
            initialfile="historial_partidos.csv",
            filetypes=(("CSV", "*.csv"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        try:
            with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(
                    [
                        "fecha",
                        "competicion",
                        "local",
                        "visitante",
                        "marcador",
                        "estado",
                        "pronostico",
                    ]
                )
                for iid in self.tree.get_children():
                    writer.writerow(self.tree.item(iid, "values"))
        except OSError as exc:
            messagebox.showerror("No se pudo exportar", str(exc), parent=self)
            return
        self.footer_var.set(f"Exportado: {path}")

    def _toggle_api(self) -> None:
        if self.app.local_api_running():
            self.app.stop_local_api()
        else:
            try:
                url = self.app.start_local_api()
            except OSError as exc:
                messagebox.showerror("API local", str(exc), parent=self)
                return
            self.footer_var.set(f"API local disponible en {url}")
        self.refresh_api_state()

    def refresh_api_state(self) -> None:
        if self.app.local_api_running():
            self.api_status.set(f"API activa en {self.app.local_api_url()}")
            self.api_toggle_btn.configure(text="Detener API")
        else:
            self.api_status.set("API local detenida.")
            self.api_toggle_btn.configure(text="Iniciar API")

    def _clear_history(self) -> None:
        if not messagebox.askyesno(
            "Borrar historial",
            "¿Eliminar partidos, análisis y predicciones guardadas?\n"
            "Esta acción no se puede deshacer.",
            parent=self,
        ):
            return
        self.store.clear()
        self.refresh()
        self.app._refresh_history_windows()
        self.footer_var.set("Historial eliminado.")

