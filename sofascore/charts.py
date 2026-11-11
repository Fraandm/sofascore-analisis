"""Gráficos ligeros dibujados sobre Canvas de Tkinter.

No se usa matplotlib a propósito: así el ejecutable sigue siendo pequeño,
los gráficos respetan el tema claro/oscuro al instante y no hay ventanas
externas. Todos los widgets son responsivos: se redibujan al cambiar de
tamaño y reciben la paleta desde :mod:`sofascore.gui`.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_PALETTE: Dict[str, str] = {
    "bg": "#f2f4f7",
    "fg": "#16191d",
    "muted": "#5b6472",
    "chart_bg": "#ffffff",
    "chart_grid": "#e6eaef",
    "chart_axis": "#b6bfc9",
    "chart_text": "#16191d",
    "chart_muted": "#5b6472",
    "accent": "#0a66c2",
    "accent_soft": "#9ec6ef",
    "accent2": "#e07b39",
    "home": "#0a66c2",
    "away": "#e07b39",
    "good": "#2e9e5b",
    "warn": "#d99a2b",
    "bad": "#cf4b4b",
    "track": "#e9edf2",
    "card_bg": "#ffffff",
    "card_border": "#d6dde5",
}

FONT = "Segoe UI"


def _hex_to_rgb(color: str) -> tuple:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def blend(color_a: str, color_b: str, amount: float) -> str:
    """Mezcla dos colores en formato ``#rrggbb`` (0 = a, 1 = b)."""
    amount = max(0.0, min(1.0, float(amount)))
    red_a, green_a, blue_a = _hex_to_rgb(color_a)
    red_b, green_b, blue_b = _hex_to_rgb(color_b)
    red = round(red_a + (red_b - red_a) * amount)
    green = round(green_a + (green_b - green_a) * amount)
    blue = round(blue_a + (blue_b - blue_a) * amount)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _truncate(text: str, limit: int) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


class ChartCanvas(tk.Canvas):
    """Canvas base con redibujado diferido al cambiar de tamaño."""

    empty_text = "Sin datos todavía."

    def __init__(
        self,
        master: tk.Misc,
        palette: Optional[Dict[str, str]] = None,
        height: int = 220,
        **kwargs: Any,
    ) -> None:
        self.palette = dict(DEFAULT_PALETTE)
        if palette:
            self.palette.update(palette)
        super().__init__(
            master,
            height=height,
            background=self.palette["chart_bg"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self._redraw_job: Optional[str] = None
        self.bind("<Configure>", self._schedule_redraw)

    # ------------------------------------------------------------------
    def set_palette(self, palette: Dict[str, str]) -> None:
        self.palette.update(palette)
        try:
            self.configure(background=self.palette["chart_bg"])
        except tk.TclError:
            return
        self.redraw()

    def _schedule_redraw(self, _event: Any = None) -> None:
        if self._redraw_job is not None:
            try:
                self.after_cancel(self._redraw_job)
            except tk.TclError:
                pass
        self._redraw_job = self.after(60, self.redraw)

    def redraw(self) -> None:
        self._redraw_job = None
        if not self.winfo_exists():
            return
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 30 or height <= 30:
            return
        try:
            self.draw(width, height)
        except tk.TclError:
            pass

    def draw(self, width: int, height: int) -> None:  # pragma: no cover - base
        raise NotImplementedError

    def clear(self) -> None:
        self.redraw()

    # ------------------------------------------------------------------
    def _empty(self, width: int, height: int, text: Optional[str] = None) -> None:
        palette = self.palette
        self.create_text(
            width / 2,
            height / 2 - 8,
            text=text or self.empty_text,
            fill=palette["chart_muted"],
            font=(FONT, 9),
            anchor="center",
            width=max(80, width - 40),
            justify="center",
        )


class ScrollableColumn(ttk.Frame):
    """Columna con desplazamiento vertical y barra que se oculta si sobra sitio."""

    def __init__(
        self,
        master: tk.Misc,
        palette: Optional[Dict[str, str]] = None,
    ) -> None:
        self.palette = dict(DEFAULT_PALETTE)
        if palette:
            self.palette.update(palette)
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            background=self.palette["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.scrollbar.grid_remove()
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self._scrollbar_visible = False
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.content.bind("<MouseWheel>", self._on_mousewheel)

    def bind_wheel(self, widget: tk.Misc) -> None:
        """Permite desplazar la columna con la rueda sobre un gráfico."""
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")

    def set_palette(self, palette: Dict[str, str]) -> None:
        self.palette.update(palette)
        try:
            self.canvas.configure(background=self.palette["bg"])
        except tk.TclError:
            pass

    def clear(self) -> None:
        self.canvas.yview_moveto(0)

    def _on_canvas_configure(self, event: Any) -> None:
        self.canvas.itemconfigure(self._window, width=max(1, event.width))
        self._update_scrollbar()

    def _on_content_configure(self, _event: Any = None) -> None:
        bbox = self.canvas.bbox("all")
        if bbox is not None:
            self.canvas.configure(scrollregion=bbox)
        self._update_scrollbar()

    def _update_scrollbar(self) -> None:
        bbox = self.canvas.bbox("all")
        content_height = (bbox[3] - bbox[1]) if bbox else 0
        needed = content_height > self.canvas.winfo_height() + 2
        if needed and not self._scrollbar_visible:
            self.scrollbar.grid()
            self._scrollbar_visible = True
        elif not needed and self._scrollbar_visible:
            self.scrollbar.grid_remove()
            self.canvas.yview_moveto(0)
            self._scrollbar_visible = False

    def _on_mousewheel(self, event: Any) -> None:
        if not self._scrollbar_visible:
            return
        delta = int(-getattr(event, "delta", 0) / 120)
        if delta == 0:
            return
        self.canvas.yview_scroll(delta, "units")


class HistogramChart(ChartCanvas):
    """Histograma vertical con barra modal resaltada y línea de media."""

    def __init__(self, master: tk.Misc, palette: Optional[Dict[str, str]] = None, **kwargs: Any) -> None:
        super().__init__(master, palette=palette, **kwargs)
        self._title = ""
        self._labels: List[str] = []
        self._values: List[float] = []
        self._marker: Optional[float] = None
        self._step = 1

    def set_data(
        self,
        labels: Sequence[str],
        values: Sequence[float],
        title: str = "",
        marker: Optional[float] = None,
        step: int = 1,
    ) -> None:
        self._title = title
        self._labels = list(labels)
        self._values = [float(value) for value in values]
        self._marker = marker
        self._step = max(1, int(step))
        self.redraw()

    def clear(self) -> None:
        self._title = ""
        self._labels = []
        self._values = []
        self._marker = None
        self.redraw()

    def draw(self, width: int, height: int) -> None:
        palette = self.palette
        left, right, top, bottom = 44, 14, 30, 28
        plot_width = width - left - right
        plot_height = height - top - bottom

        if self._title:
            self.create_text(
                left,
                14,
                text=self._title,
                anchor="w",
                fill=palette["chart_text"],
                font=(FONT, 10, "bold"),
            )
        if not self._values or plot_width < 30 or plot_height < 30:
            self._empty(width, height)
            return

        values = self._values
        maximum = max(values) or 1.0
        count = len(values)

        for index in range(5):
            y = top + plot_height * index / 4.0
            value = maximum * (1.0 - index / 4.0)
            self.create_line(
                left,
                y,
                width - right,
                y,
                fill=palette["chart_grid"],
                dash=(2, 4),
            )
            self.create_text(
                left - 6,
                y,
                text=f"{value:.0f}%",
                anchor="e",
                fill=palette["chart_muted"],
                font=(FONT, 7),
            )

        self.create_line(
            left,
            top + plot_height,
            width - right,
            top + plot_height,
            fill=palette["chart_axis"],
        )

        slot = plot_width / count
        bar_width = max(1.0, min(slot * 0.72, 46.0))
        modal = max(range(count), key=lambda index: values[index])
        label_step = max(1, int(math.ceil(count / max(1.0, plot_width / 38.0))))

        for index, value in enumerate(values):
            x0 = left + index * slot + (slot - bar_width) / 2.0
            x1 = x0 + bar_width
            bar_height = plot_height * (value / maximum)
            color = (
                palette["accent"] if index == modal else palette["accent_soft"]
            )
            if value > 0:
                self.create_rectangle(
                    x0,
                    top + plot_height - bar_height,
                    x1,
                    top + plot_height,
                    fill=color,
                    outline="",
                )
            if index % label_step == 0:
                self.create_text(
                    left + (index + 0.5) * slot,
                    top + plot_height + 7,
                    text=self._labels[index] if index < len(self._labels) else str(index),
                    anchor="n",
                    fill=palette["chart_muted"],
                    font=(FONT, 7),
                )

        if self._marker is not None:
            marker_x = left + (float(self._marker) / self._step) * slot
            marker_x = max(left, min(width - right, marker_x))
            self.create_line(
                marker_x,
                top,
                marker_x,
                top + plot_height,
                fill=palette["chart_text"],
                dash=(3, 3),
                width=1,
            )
            text = f"media {self._marker:.2f}".rstrip("0").rstrip(".")
            self.create_text(
                marker_x + 4,
                top + 2,
                text=text,
                anchor="nw",
                fill=palette["chart_text"],
                font=(FONT, 7, "bold"),
            )


class GroupedBarChart(ChartCanvas):
    """Barras horizontales agrupadas para comparar local y visitante."""

    def __init__(self, master: tk.Misc, palette: Optional[Dict[str, str]] = None, **kwargs: Any) -> None:
        super().__init__(master, palette=palette, **kwargs)
        self._title = ""
        self._items: List[Dict[str, Any]] = []
        self._home_name = "Local"
        self._away_name = "Visitante"

    def set_data(
        self,
        items: Sequence[Dict[str, Any]],
        title: str = "",
        home_name: str = "Local",
        away_name: str = "Visitante",
    ) -> None:
        self._title = title
        self._items = list(items)
        self._home_name = home_name
        self._away_name = away_name
        self.redraw()

    def clear(self) -> None:
        self._title = ""
        self._items = []
        self.redraw()

    def draw(self, width: int, height: int) -> None:
        palette = self.palette
        if self._title:
            self.create_text(
                12,
                14,
                text=self._title,
                anchor="w",
                fill=palette["chart_text"],
                font=(FONT, 10, "bold"),
            )
        if not self._items:
            self._empty(width, height)
            return

        # Leyenda arriba a la derecha.
        legend_y = 14
        away_text = _truncate(self._away_name, 16)
        home_text = _truncate(self._home_name, 16)
        self.create_rectangle(
            width - 12 - 8, legend_y - 4, width - 12, legend_y + 4,
            fill=palette["away"], outline="",
        )
        self.create_text(
            width - 16,
            legend_y,
            text=away_text,
            anchor="e",
            fill=palette["chart_muted"],
            font=(FONT, 8),
        )
        home_x = width - 16 - max(34, len(away_text) * 7) - 14
        self.create_rectangle(
            home_x - 8, legend_y - 4, home_x, legend_y + 4,
            fill=palette["home"], outline="",
        )
        self.create_text(
            home_x - 12,
            legend_y,
            text=home_text,
            anchor="e",
            fill=palette["chart_muted"],
            font=(FONT, 8),
        )

        left = 112
        right = 46
        top = 34
        bottom = 8
        plot_width = width - left - right
        plot_height = height - top - bottom
        if plot_width < 40 or plot_height < 30:
            self._empty(width, height)
            return

        count = len(self._items)
        row_height = plot_height / count
        maximum = max(
            [float(item.get("home") or 0) for item in self._items]
            + [float(item.get("away") or 0) for item in self._items]
            + [0.001]
        )
        bar_height = max(4.0, min(11.0, row_height * 0.30))

        for index, item in enumerate(self._items):
            center = top + (index + 0.5) * row_height
            label = _truncate(str(item.get("label", "")), 16)
            self.create_text(
                left - 8,
                center,
                text=label,
                anchor="e",
                fill=palette["chart_text"],
                font=(FONT, 8),
            )
            for side, color, offset in (
                ("home", palette["home"], -bar_height - 1),
                ("away", palette["away"], 1),
            ):
                value = float(item.get(side) or 0)
                length = plot_width * (value / maximum)
                y0 = center + offset
                self.create_rectangle(
                    left,
                    y0,
                    left + max(0.0, length),
                    y0 + bar_height,
                    fill=color,
                    outline="",
                )
                text = f"{value:.2f}".rstrip("0").rstrip(".")
                text_x = left + length + 4
                if text_x > width - right + 34:
                    text_x = left + length - 4
                    anchor = "e"
                    text_color = palette["chart_bg"]
                else:
                    anchor = "w"
                    text_color = palette["chart_muted"]
                self.create_text(
                    text_x,
                    y0 + bar_height / 2.0,
                    text=text,
                    anchor=anchor,
                    fill=text_color,
                    font=(FONT, 7),
                )


class HorizontalBarChart(ChartCanvas):
    """Barras horizontales con porcentaje, usadas para mercados y marcadores."""

    def __init__(self, master: tk.Misc, palette: Optional[Dict[str, str]] = None, **kwargs: Any) -> None:
        super().__init__(master, palette=palette, **kwargs)
        self._title = ""
        self._items: List[Dict[str, Any]] = []

    def set_data(self, items: Sequence[Dict[str, Any]], title: str = "") -> None:
        self._title = title
        self._items = list(items)
        self.redraw()

    def clear(self) -> None:
        self._title = ""
        self._items = []
        self.redraw()

    def draw(self, width: int, height: int) -> None:
        palette = self.palette
        if self._title:
            self.create_text(
                12,
                14,
                text=self._title,
                anchor="w",
                fill=palette["chart_text"],
                font=(FONT, 10, "bold"),
            )
        if not self._items:
            self._empty(width, height)
            return

        left = min(178, max(90, int(width * 0.42)))
        right = 50
        top = 28
        bottom = 6
        plot_width = width - left - right
        plot_height = height - top - bottom
        if plot_width < 24 or plot_height < 20:
            self._empty(width, height)
            return

        count = len(self._items)
        row_height = plot_height / count
        bar_height = max(7.0, min(14.0, row_height * 0.44))

        for index, item in enumerate(self._items):
            center = top + (index + 0.5) * row_height
            if item.get("header"):
                self.create_text(
                    8,
                    center,
                    text=str(item.get("label", "")),
                    anchor="w",
                    fill=palette["accent"],
                    font=(FONT, 8, "bold"),
                )
                continue

            label = _truncate(str(item.get("label", "")), 24)
            self.create_text(
                left - 8,
                center,
                text=label,
                anchor="e",
                fill=palette["chart_text"],
                font=(FONT, 8),
                width=max(40, left - 16),
            )
            value = max(0.0, min(1.0, float(item.get("value") or 0)))
            y0 = center - bar_height / 2.0
            self.create_rectangle(
                left,
                y0,
                left + plot_width,
                y0 + bar_height,
                fill=palette["track"],
                outline="",
            )
            color = str(item.get("color") or palette["accent"])
            self.create_rectangle(
                left,
                y0,
                left + plot_width * value,
                y0 + bar_height,
                fill=color,
                outline="",
            )
            self.create_text(
                width - 8,
                center,
                text=f"{value * 100:.0f}%",
                anchor="e",
                fill=palette["chart_text"],
                font=(FONT, 8, "bold"),
            )


class DonutChart(ChartCanvas):
    """Anillo de probabilidades (1X2) con leyenda."""

    def __init__(self, master: tk.Misc, palette: Optional[Dict[str, str]] = None, **kwargs: Any) -> None:
        super().__init__(master, palette=palette, **kwargs)
        self._segments: List[Dict[str, Any]] = []
        self._center_value = ""
        self._center_label = ""

    def set_data(
        self,
        segments: Sequence[Dict[str, Any]],
        center_value: str = "",
        center_label: str = "",
    ) -> None:
        self._segments = list(segments)
        self._center_value = center_value
        self._center_label = center_label
        self.redraw()

    def clear(self) -> None:
        self._segments = []
        self._center_value = ""
        self._center_label = ""
        self.redraw()

    def draw(self, width: int, height: int) -> None:
        palette = self.palette
        if not self._segments:
            self._empty(width, height)
            return

        total = sum(max(0.0, float(item.get("value") or 0)) for item in self._segments)
        if total <= 0:
            self._empty(width, height)
            return

        margin = 12
        compact = height < 140
        strip_prefix = height < 180
        legend_width = 124 if width >= 340 else (118 if width >= 300 else 0)
        radius = min((width - legend_width) / 2.0, (height - 2 * margin) / 2.0) - 6
        radius = max(24.0, radius)
        center_x = margin + radius + 4
        center_y = height / 2.0
        outer = (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )
        inner_radius = radius * 0.62
        inner = (
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius,
        )

        start = 90.0
        for item in self._segments:
            value = max(0.0, float(item.get("value") or 0))
            extent = -360.0 * value / total
            self.create_arc(
                outer,
                start=start,
                extent=extent,
                fill=str(item.get("color") or palette["accent"]),
                outline=palette["chart_bg"],
                width=2,
            )
            start += extent
        self.create_oval(inner, fill=palette["chart_bg"], outline=palette["chart_bg"])

        value_font = 13 if compact else 17
        if self._center_value:
            self.create_text(
                center_x,
                center_y - (6 if self._center_label else 0),
                text=self._center_value,
                fill=palette["chart_text"],
                font=(FONT, value_font, "bold"),
                anchor="center",
            )
        if self._center_label and (not compact or inner_radius >= 18):
            label = self._center_label
            if strip_prefix:
                label = label.removeprefix("gana ")
            self.create_text(
                center_x,
                center_y + (9 if compact else 11),
                text=_truncate(label, 11 if compact else 14),
                fill=palette["chart_muted"],
                font=(FONT, 6 if compact else 7),
                anchor="center",
            )

        if legend_width:
            legend_x = width - legend_width + 8
            row_height = min(
                20.0 if compact else 26.0,
                (height - 2 * margin) / max(1, len(self._segments)),
            )
            start_y = center_y - row_height * len(self._segments) / 2.0 + row_height / 2.0
            for index, item in enumerate(self._segments):
                y = start_y + index * row_height
                color = str(item.get("color") or palette["accent"])
                self.create_rectangle(
                    legend_x,
                    y - 4,
                    legend_x + 9,
                    y + 5,
                    fill=color,
                    outline="",
                )
                value = max(0.0, float(item.get("value") or 0))
                self.create_text(
                    legend_x + 14,
                    y - 1,
                    text=_truncate(str(item.get("label", "")), 15),
                    anchor="w",
                    fill=palette["chart_text"],
                    font=(FONT, 6 if compact else 7),
                )
                self.create_text(
                    legend_x + 14,
                    y + 8,
                    text=f"{value * 100:.0f}%",
                    anchor="w",
                    fill=palette["chart_muted"],
                    font=(FONT, 6 if compact else 7, "bold"),
                )


class HeatmapChart(ChartCanvas):
    """Matriz de marcadores con intensidad de color."""

    def __init__(self, master: tk.Misc, palette: Optional[Dict[str, str]] = None, **kwargs: Any) -> None:
        super().__init__(master, palette=palette, **kwargs)
        self._labels: List[str] = []
        self._matrix: List[List[float]] = []
        self._title = ""
        self._home_name = "Local"
        self._away_name = "Visitante"

    def set_data(
        self,
        labels: Sequence[str],
        matrix: Sequence[Sequence[float]],
        title: str = "",
        home_name: str = "Local",
        away_name: str = "Visitante",
    ) -> None:
        self._labels = [str(label) for label in labels]
        self._matrix = [[float(value) for value in row] for row in matrix]
        self._title = title
        self._home_name = home_name
        self._away_name = away_name
        self.redraw()

    def clear(self) -> None:
        self._labels = []
        self._matrix = []
        self._title = ""
        self.redraw()

    def draw(self, width: int, height: int) -> None:
        palette = self.palette
        if self._title:
            self.create_text(
                12,
                14,
                text=self._title,
                anchor="w",
                fill=palette["chart_text"],
                font=(FONT, 10, "bold"),
            )
        if not self._matrix or not self._labels:
            self._empty(width, height)
            return

        left, right, top, bottom = 54, 12, 34, 42
        plot_width = width - left - right
        plot_height = height - top - bottom
        rows = len(self._matrix)
        columns = len(self._matrix[0]) if rows else 0
        if columns == 0 or plot_width < 40 or plot_height < 40:
            self._empty(width, height)
            return

        cell_width = plot_width / columns
        cell_height = plot_height / rows
        maximum = max(max(row) for row in self._matrix) or 1.0
        best = max(
            ((row, column) for row in range(rows) for column in range(columns)),
            key=lambda pair: self._matrix[pair[0]][pair[1]],
        )
        font_size = (
            8
            if cell_width >= 34 and cell_height >= 22
            else (7 if cell_width >= 24 and cell_height >= 16 else 6)
        )

        for row in range(rows):
            display_row = rows - 1 - row
            for column in range(columns):
                value = self._matrix[row][column]
                ratio = value / maximum
                color = blend(
                    palette["chart_bg"], palette["accent"], 0.08 + 0.82 * ratio
                )
                x0 = left + column * cell_width
                y0 = top + display_row * cell_height
                self.create_rectangle(
                    x0 + 1,
                    y0 + 1,
                    x0 + cell_width - 1,
                    y0 + cell_height - 1,
                    fill=color,
                    outline=palette["chart_bg"],
                )
                if value >= 0.0001:
                    text_color = (
                        palette["chart_bg"]
                        if ratio >= 0.55
                        else palette["chart_text"]
                    )
                    self.create_text(
                        x0 + cell_width / 2.0,
                        y0 + cell_height / 2.0,
                        text=f"{value * 100:.2f}",
                        fill=text_color,
                        font=(
                            FONT,
                            font_size,
                            "bold" if (row, column) == best else "normal",
                        ),
                    )
                if (row, column) == best:
                    self.create_rectangle(
                        x0 + 1,
                        y0 + 1,
                        x0 + cell_width - 1,
                        y0 + cell_height - 1,
                        outline=palette["chart_text"],
                        width=2,
                    )

        for column, label in enumerate(self._labels):
            self.create_text(
                left + (column + 0.5) * cell_width,
                top + plot_height + 7,
                text=label,
                anchor="n",
                fill=palette["chart_muted"],
                font=(FONT, 7),
            )
        for row, label in enumerate(self._labels):
            display_row = rows - 1 - row
            self.create_text(
                left - 7,
                top + (display_row + 0.5) * cell_height,
                text=label,
                anchor="e",
                fill=palette["chart_muted"],
                font=(FONT, 7),
            )

        self.create_text(
            left + plot_width / 2.0,
            height - 8,
            text=f"Goles de {_truncate(self._away_name, 20)} →",
            anchor="s",
            fill=palette["chart_muted"],
            font=(FONT, 7),
        )
        self.create_text(
            12,
            top + plot_height / 2.0,
            text=f"Goles de {_truncate(self._home_name, 20)} (↑)",
            anchor="w",
            angle=90,
            fill=palette["chart_muted"],
            font=(FONT, 7),
        )


class KpiStrip(tk.Frame):
    """Fila de tarjetas con las cifras clave de la simulación."""

    def __init__(
        self,
        master: tk.Misc,
        palette: Dict[str, str],
        columns: int = 5,
    ) -> None:
        self.palette = dict(DEFAULT_PALETTE)
        self.palette.update(palette)
        super().__init__(master, background=self.palette["bg"])
        self.columns = columns
        self._cards: List[Dict[str, tk.Widget]] = []
        for index in range(columns):
            card = tk.Frame(
                self,
                background=self.palette["card_bg"],
                highlightbackground=self.palette["card_border"],
                highlightthickness=1,
                bd=0,
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0 if index == 0 else 6, 0),
            )
            self.columnconfigure(index, weight=1)
            accent = tk.Frame(card, background=self.palette["accent"], height=3)
            accent.pack(fill="x")
            title = tk.Label(
                card,
                text="",
                anchor="w",
                background=self.palette["card_bg"],
                foreground=self.palette["chart_muted"],
                font=(FONT, 7, "bold"),
            )
            title.pack(fill="x", padx=9, pady=(6, 0))
            value = tk.Label(
                card,
                text="—",
                anchor="w",
                background=self.palette["card_bg"],
                foreground=self.palette["chart_text"],
                font=(FONT, 16, "bold"),
            )
            value.pack(fill="x", padx=9)
            subtitle = tk.Label(
                card,
                text="",
                anchor="w",
                background=self.palette["card_bg"],
                foreground=self.palette["chart_muted"],
                font=(FONT, 7),
            )
            subtitle.pack(fill="x", padx=9, pady=(0, 6))
            self._cards.append(
                {
                    "card": card,
                    "accent": accent,
                    "title": title,
                    "value": value,
                    "subtitle": subtitle,
                    "color_key": None,
                }
            )

    def set_palette(self, palette: Dict[str, str]) -> None:
        self.palette.update(palette)
        self.configure(background=self.palette["bg"])
        for card in self._cards:
            card["card"].configure(
                background=self.palette["card_bg"],
                highlightbackground=self.palette["card_border"],
            )
            card["title"].configure(
                background=self.palette["card_bg"],
                foreground=self.palette["chart_muted"],
            )
            card["subtitle"].configure(
                background=self.palette["card_bg"],
                foreground=self.palette["chart_muted"],
            )
            key = card.get("color_key")
            if key:
                color = self.palette.get(key, self.palette["accent"])
                card["value"].configure(
                    background=self.palette["card_bg"], foreground=color
                )
                card["accent"].configure(background=color)
            else:
                card["value"].configure(
                    background=self.palette["card_bg"],
                    foreground=self.palette["chart_text"],
                )

    def set_cards(self, cards: Sequence[Dict[str, Any]]) -> None:
        default_keys = ("accent", "home", "good", "warn", "accent2")
        for index, (slot, data) in enumerate(zip(self._cards, cards)):
            key = data.get("color_key") or default_keys[index % len(default_keys)]
            color = self.palette.get(
                key, data.get("color") or self.palette["chart_text"]
            )
            slot["color_key"] = key
            slot["title"].configure(text=str(data.get("title", "")))
            slot["value"].configure(text=str(data.get("value", "—")), foreground=color)
            slot["subtitle"].configure(text=str(data.get("subtitle", "")))
            slot["accent"].configure(background=color)

    def clear(self) -> None:
        self.set_cards([{} for _ in self._cards])
