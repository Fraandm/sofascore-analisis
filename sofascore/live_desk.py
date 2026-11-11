"""Sala de directo: tarjetas de partidos en vivo y pronósticos guardados."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any, Dict, List, Optional

from . import charts


def _team_label(team: Dict[str, Any]) -> str:
    return str((team or {}).get("short_name") or (team or {}).get("name") or "")


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


class LiveDeskWindow(tk.Toplevel):
    def __init__(self, app: Any) -> None:
        super().__init__(app.root)
        self.app = app
        self.title("Sala de directo · SofaScore")
        self.configure(background=app.palette["bg"])
        self.geometry(self._geometry(1120, 700))
        self.minsize(820, 500)
        self.transient(app.root)
        self.filter = "live"
        self._signature: Optional[tuple] = None
        self._refresh_job: Optional[str] = None
        self._build()
        self.refresh(force=True)
        self._schedule()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _geometry(self, width: int, height: int) -> str:
        root = self.app.root
        x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
        y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _build(self) -> None:
        palette = self.app.palette
        header = ttk.Frame(self, padding=(14, 12, 14, 6))
        header.pack(fill="x")
        ttk.Label(header, text="Sala de directo", style="Team.TLabel").pack(
            side="left"
        )
        self.summary_var = tk.StringVar(value="")
        ttk.Label(
            header, textvariable=self.summary_var, style="Small.TLabel"
        ).pack(side="left", padx=(10, 0))
        ttk.Button(header, text="Cerrar", command=self.close).pack(side="right")
        ttk.Button(
            header, text="Actualizar", command=self._update_now
        ).pack(side="right", padx=(0, 6))

        controls = ttk.Frame(self, padding=(14, 0, 14, 6))
        controls.pack(fill="x")
        self.filter_buttons: Dict[str, ttk.Button] = {}
        for key, label in (
            ("live", "En vivo"),
            ("favorites", "★ Favoritos"),
            ("all", "Todos"),
        ):
            button = ttk.Button(
                controls,
                text=label,
                width=12,
                style="ChipActive.TButton" if key == "live" else "Chip.TButton",
                command=lambda item=key: self._set_filter(item),
            )
            button.pack(side="left", padx=(0, 5))
            self.filter_buttons[key] = button
        self.last_var = tk.StringVar(value="")
        tk.Label(
            controls,
            textvariable=self.last_var,
            background=palette["bg"],
            foreground=palette["muted"],
            font=("Segoe UI", 8),
        ).pack(side="right")

        self.scroller = charts.ScrollableColumn(self, palette)
        self.scroller.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.cards = tk.Frame(self.scroller.content, background=palette["bg"])
        self.cards.pack(fill="both", expand=True)
        self.empty_var = tk.StringVar()

    def _set_filter(self, key: str) -> None:
        self.filter = key
        for item, button in self.filter_buttons.items():
            button.configure(
                style="ChipActive.TButton"
                if item == key
                else "Chip.TButton"
            )
        self._signature = None
        self.refresh(force=True)

    def _schedule(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
        self._refresh_job = self.after(2000, self._tick)

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        self.refresh()
        self._schedule()

    def _update_now(self) -> None:
        self.app._refresh_live_async()
        self.last_var.set("Actualizando…")

    def close(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None
        self.destroy()

    def _visible_matches(self) -> List[Dict[str, Any]]:
        matches = list(self.app.matches)
        if self.filter == "live":
            matches = [
                match
                for match in matches
                if match.get("status_type") in ("inprogress", "live", "halftime")
            ]
        elif self.filter == "favorites":
            matches = [
                match
                for match in matches
                if self.app._match_has_favorite(match)
            ]
        return matches[:40]

    def refresh(self, force: bool = False) -> None:
        matches = self._visible_matches()
        predictions = {}
        if self.app.storage is not None:
            try:
                predictions = self.app.storage.latest_predictions(
                    [match.get("id") for match in matches]
                )
            except Exception:
                predictions = {}
        signature = tuple(
            (
                match.get("id"),
                match.get("status_type"),
                match.get("home_score"),
                match.get("away_score"),
                str(match.get("status_time")),
                bool(predictions.get(match.get("id"))),
                tuple(
                    bool(
                        self.app._image_photos.get(
                            (("team", self.app._team_id(match.get(side) or {})), 18)
                        )
                    )
                    for side in ("home_team", "away_team")
                ),
            )
            for match in matches
        )
        self.summary_var.set(
            _plural(len(matches), "partido", "partidos")
            + (" · en directo" if self.filter == "live" else "")
        )
        self.last_var.set(
            f"Actualizado {datetime.now().strftime('%H:%M:%S')}"
        )
        if not force and signature == self._signature:
            return
        self._signature = signature
        for child in self.cards.winfo_children():
            child.destroy()
        if not matches:
            if self.filter == "favorites":
                message = (
                    "No hay partidos de tus favoritos.\n"
                    "Marca equipos con ★ Favoritos o el clic derecho."
                )
            elif self.filter == "live":
                message = (
                    "No hay partidos en vivo ahora mismo.\n"
                    "Prueba «Todos» o espera al siguiente partido."
                )
            else:
                message = "No hay partidos con este filtro."
            tk.Label(
                self.cards,
                text=message,
                background=self.app.palette["bg"],
                foreground=self.app.palette["muted"],
                font=("Segoe UI", 10),
                justify="center",
            ).pack(pady=50)
            return
        for index, match in enumerate(matches):
            self._build_card(match, predictions.get(match.get("id")), index)

    def _build_card(
        self,
        match: Dict[str, Any],
        prediction: Optional[Dict[str, Any]],
        index: int,
    ) -> None:
        palette = self.app.palette
        card = tk.Frame(
            self.cards,
            background=palette["card_bg"],
            highlightbackground=palette["card_border"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        card.pack(fill="x", pady=(0, 6))
        top = tk.Frame(card, background=palette["card_bg"])
        top.pack(fill="x")
        tournament = (match.get("tournament") or {})
        tk.Label(
            top,
            text=tournament.get("name") or "Competición",
            background=palette["card_bg"],
            foreground=palette["muted"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(side="left")
        status_text = self.app._match_status_text(match)
        if not status_text:
            status_text = self.app._match_time(match)
        status_color = (
            palette["bad"]
            if match.get("status_type") in ("inprogress", "live", "halftime")
            else palette["muted"]
        )
        tk.Label(
            top,
            text=status_text,
            background=palette["card_bg"],
            foreground=status_color,
            font=("Segoe UI", 8, "bold"),
            anchor="e",
        ).pack(side="right")

        main = tk.Frame(card, background=palette["card_bg"])
        main.pack(fill="x", pady=(5, 3))
        self._team_row(main, match.get("home_team") or {}, "left")
        score = self.app._match_score(match)
        tk.Label(
            main,
            text=score,
            background=palette["card_bg"],
            foreground=palette["chart_text"],
            font=("Segoe UI", 18, "bold"),
            width=7,
        ).pack(side="left", expand=True)
        self._team_row(main, match.get("away_team") or {}, "right")

        bottom = tk.Frame(card, background=palette["card_bg"])
        bottom.pack(fill="x", pady=(2, 0))
        if prediction:
            probability_text = (
                f"1 {float(prediction.get('prob_home') or 0) * 100:.0f}%  ·  "
                f"X {float(prediction.get('prob_draw') or 0) * 100:.0f}%  ·  "
                f"2 {float(prediction.get('prob_away') or 0) * 100:.0f}%"
            )
            tk.Label(
                bottom,
                text=probability_text,
                background=palette["card_bg"],
                foreground=palette["accent"],
                font=("Segoe UI", 8, "bold"),
                anchor="w",
            ).pack(side="left")
        else:
            tk.Label(
                bottom,
                text="Sin pronóstico guardado",
                background=palette["card_bg"],
                foreground=palette["chart_muted"],
                font=("Segoe UI", 8),
                anchor="w",
            ).pack(side="left")
        ttk.Button(
            bottom,
            text="Abrir en la app",
            style="Chip.TButton",
            command=lambda match_id=match.get("id"): self._open_match(match_id),
        ).pack(side="right")

    def _team_row(self, parent: tk.Frame, team: Dict[str, Any], side: str) -> None:
        palette = self.app.palette
        row = tk.Frame(parent, background=palette["card_bg"])
        row.pack(side=side, expand=True, fill="x")
        anchor = "w" if side == "left" else "e"
        canvas = tk.Canvas(
            row,
            width=24,
            height=24,
            background=palette["card_bg"],
            highlightthickness=0,
        )
        photo = None
        team_id = self.app._team_id(team)
        if team_id is not None:
            photo = self.app._photo("team", team_id, 18)
        if photo is not None:
            canvas.create_image(12, 12, image=photo)
        else:
            canvas.create_text(
                12,
                12,
                text=(_team_label(team) or "?")[:1].upper(),
                fill=palette["muted"],
                font=("Segoe UI", 9, "bold"),
            )
        row_label = tk.Label(
            row,
            text=_team_label(team) or "Equipo",
            background=palette["card_bg"],
            foreground=palette["chart_text"],
            font=("Segoe UI", 11, "bold"),
            anchor=anchor,
        )
        if side == "left":
            canvas.pack(side="left")
            row_label.pack(side="left", padx=(7, 0), fill="x", expand=True)
        else:
            canvas.pack(side="right")
            row_label.pack(side="right", padx=(0, 7), fill="x", expand=True)

    def _open_match(self, match_id: Any) -> None:
        if match_id is None:
            return
        self.app._select_match_by_id(int(match_id))
        self.app.root.lift()
        self.app.root.focus_force()

