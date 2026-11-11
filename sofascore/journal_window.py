"""Cuaderno de predicciones y panel de acierto."""

from __future__ import annotations

import csv
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from .storage import HistoryStore


def _day_text(value: Any) -> str:
    text = str(value or "")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


class JournalWindow(tk.Toplevel):
    def __init__(self, app: Any, store: HistoryStore) -> None:
        super().__init__(app.root)
        self.app = app
        self.store = store
        self.title("Cuaderno de predicciones · SofaScore")
        self.configure(background=app.palette["bg"])
        self.geometry(self._geometry(1080, 680))
        self.minsize(820, 520)
        self.transient(app.root)
        self.predictions: List[Dict[str, Any]] = []
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
        palette = self.app.palette
        header = ttk.Frame(self, padding=(14, 12, 14, 6))
        header.pack(fill="x")
        ttk.Label(
            header, text="Cuaderno de predicciones", style="Team.TLabel"
        ).pack(side="left")
        ttk.Label(
            header,
            text="Historial local y acierto del modelo",
            style="Small.TLabel",
        ).pack(side="left", padx=(10, 0))
        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")
        ttk.Button(
            header, text="Exportar CSV", command=self._export_csv
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            header, text="Actualizar", command=self.refresh
        ).pack(side="right", padx=(0, 6))

        kpis = ttk.Frame(self, padding=(14, 0, 14, 8))
        kpis.pack(fill="x")
        self.metric_vars: Dict[str, tk.StringVar] = {}
        for index, (key, title, color) in enumerate(
            (
                ("total", "PREDICCIONES", palette["accent"]),
                ("resolved", "RESUELTAS", palette["good"]),
                ("accuracy", "ACIERTO 1X2", palette["good"]),
                ("brier", "BRIER", palette["warn"]),
                ("mae", "MAE GOLES", palette["accent2"]),
            )
        ):
            card = tk.Frame(
                kpis,
                background=palette["card_bg"],
                highlightbackground=palette["card_border"],
                highlightthickness=1,
            )
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0))
            kpis.columnconfigure(index, weight=1)
            tk.Frame(card, background=color, height=3).pack(fill="x")
            tk.Label(
                card,
                text=title,
                background=palette["card_bg"],
                foreground=palette["chart_muted"],
                font=("Segoe UI", 7, "bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(7, 0))
            var = tk.StringVar(value="—")
            self.metric_vars[key] = var
            tk.Label(
                card,
                textvariable=var,
                background=palette["card_bg"],
                foreground=color,
                font=("Segoe UI", 16, "bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 7))

        filters = ttk.Frame(self, padding=(14, 0, 14, 6))
        filters.pack(fill="x")
        ttk.Label(filters, text="Buscar").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.pack(side="left", fill="x", expand=True, padx=(4, 10))
        self.search_var.trace_add("write", lambda *_args: self.refresh())
        ttk.Label(filters, text="Estado").pack(side="left")
        self.status_var = tk.StringVar(value="Todas")
        combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=("Todas", "Resueltas", "Pendientes"),
            state="readonly",
            width=12,
        )
        combo.pack(side="left", padx=(4, 0))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

        table_frame = ttk.Frame(self, padding=(14, 0, 14, 8))
        table_frame.pack(fill="both", expand=True)
        columns = ("created", "date", "competition", "match", "pick", "prob", "actual", "hit")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        for column, heading, width, anchor in (
            ("created", "Guardada", 105, "w"),
            ("date", "Fecha", 80, "w"),
            ("competition", "Competición", 150, "w"),
            ("match", "Partido", 260, "w"),
            ("pick", "Pronóstico", 150, "w"),
            ("prob", "Prob.", 65, "e"),
            ("actual", "Real", 65, "e"),
            ("hit", "Acierto", 80, "w"),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor=anchor, stretch=column == "match")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_selected)

        self.footer_var = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self.footer_var,
            style="Small.TLabel",
            padding=(14, 0, 14, 10),
        ).pack(fill="x")

    def refresh(self) -> None:
        self.predictions = self.store.list_predictions(limit=1000)
        metrics = self.store.accuracy()
        self.metric_vars["total"].set(str(len(self.predictions)))
        self.metric_vars["resolved"].set(str(metrics["total"]))
        self.metric_vars["accuracy"].set(
            f"{metrics['accuracy'] * 100:.1f} %".replace(".", ",")
            if metrics["total"]
            else "—"
        )
        self.metric_vars["brier"].set(
            f"{metrics['brier']:.3f}".replace(".", ",")
            if metrics["total"]
            else "—"
        )
        self.metric_vars["mae"].set(
            f"{metrics['goal_mae']:.2f}".replace(".", ",")
            if metrics["total"]
            else "—"
        )
        query = self.search_var.get().casefold().strip()
        status_filter = self.status_var.get()
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for prediction in self.predictions:
            resolved = (
                prediction.get("actual_score") not in (None, "")
                and prediction.get("actual_status") == "finished"
            )
            if status_filter == "Resueltas" and not resolved:
                continue
            if status_filter == "Pendientes" and resolved:
                continue
            text = " ".join(
                str(prediction.get(key) or "")
                for key in ("home_name", "away_name", "tournament")
            ).casefold()
            if query and query not in text:
                continue
            probs = {
                "local": float(prediction.get("prob_home") or 0.0),
                "empate": float(prediction.get("prob_draw") or 0.0),
                "visitante": float(prediction.get("prob_away") or 0.0),
            }
            pick_key = max(probs, key=probs.get)
            pick = {
                "local": prediction.get("home_name") or "Local",
                "empate": "Empate",
                "visitante": prediction.get("away_name") or "Visitante",
            }[pick_key]
            actual_side = None
            if resolved:
                try:
                    home, away = str(prediction["actual_score"]).split("-", 1)
                    actual_side = (
                        "local"
                        if int(home) > int(away)
                        else "visitante"
                        if int(away) > int(home)
                        else "empate"
                    )
                except (TypeError, ValueError):
                    pass
            hit = (
                "Sí"
                if actual_side and pick_key == actual_side
                else "No"
                if actual_side
                else "Pendiente"
            )
            self.tree.insert(
                "",
                "end",
                iid=str(prediction.get("id")),
                values=(
                    datetime.fromtimestamp(
                        float(prediction.get("created_at") or 0)
                    ).strftime("%d/%m %H:%M"),
                    _day_text(prediction.get("day")),
                    prediction.get("tournament") or "",
                    f"{prediction.get('home_name') or 'Local'} vs "
                    f"{prediction.get('away_name') or 'Visitante'}",
                    pick,
                    f"{probs[pick_key] * 100:.0f}%",
                    prediction.get("actual_score") or "—",
                    hit,
                ),
                tags=("hit",) if hit == "Sí" else ("miss",) if hit == "No" else (),
            )
            shown += 1
        self.tree.tag_configure("hit", foreground=self.app.palette["good"])
        self.tree.tag_configure("miss", foreground=self.app.palette["bad"])
        self.footer_var.set(
            (f"{shown} predicción mostrada" if shown == 1 else f"{shown} predicciones mostradas")
            + " · "
            f"Base de datos: {self.store.path}"
        )

    def _open_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        prediction_id = int(selection[0])
        prediction = next(
            (item for item in self.predictions if item.get("id") == prediction_id),
            None,
        )
        if not prediction:
            return
        match_id = prediction.get("match_id")
        self.app._select_match_by_id(match_id)
        if not any(
            item.get("id") == match_id for item in self.app.matches
        ):
            self.footer_var.set(
                "Ese partido no está en la fecha cargada; puedes consultar "
                "sus datos en el Explorador."
            )

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar cuaderno de predicciones",
            defaultextension=".csv",
            initialfile="predicciones.csv",
            filetypes=(("CSV", "*.csv"), ("Todos los archivos", "*.*")),
        )
        if not path:
            return
        try:
            with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(
                    [
                        "guardada",
                        "fecha",
                        "competicion",
                        "local",
                        "visitante",
                        "pronostico",
                        "probabilidad",
                        "resultado_real",
                        "acierto",
                    ]
                )
                for iid in self.tree.get_children():
                    values = self.tree.item(iid, "values")
                    writer.writerow(values)
        except OSError as exc:
            messagebox.showerror("No se pudo exportar", str(exc), parent=self)
            return
        self.footer_var.set(f"Exportado: {path}")

