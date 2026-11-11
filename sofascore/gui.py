"""Interfaz gráfica de escritorio (Tkinter) para analizar la forma.

Flujo de uso:
1. Elegir una fecha (o buscar un equipo) y cargar los próximos partidos.
2. Seleccionar un partido de la lista.
3. Elegir la ventana: últimos 5, 10, 15 o toda la temporada.
4. Pulsar «Analizar partido» y revisar el resumen y el detalle por equipo.
5. Exportar a CSV o JSON.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from . import (
    __version__,
    api_server,
    charts,
    explorer_window,
    export,
    form,
    journal_window,
    live_desk,
    neural,
    normalize,
    preview,
    preview_window,
    regions,
    simulation,
    simulation_cache,
    storage,
    upcoming,
)
from .client import ClientConfig, SofaScoreClient
from .exceptions import SofaScoreError
from .extractor import SofaScoreExtractor, parse_day, resolve_timezone

APP_TITLE = "SofaScore · Análisis de forma"
REGION_LABELS = {
    "Ambas": "ambas",
    "Europa": "europa",
    "Sudamérica": "sudamerica",
}
COMPETITION_LABELS = {
    "Principales": "principales",
    "Todas": "todas",
}


def _plural(count: int, singular: str, plural: str) -> str:
    """Devuelve «1 partido» o «3 partidos» según corresponda."""
    return f"{count} {singular if count == 1 else plural}"


def _short_text(text: Any, limit: int) -> str:
    """Recorta un texto largo para encabezados de tabla."""
    value = str(text or "")
    return value if len(value) <= limit else value[: max(1, limit - 1)] + "…"


def _team_label(team: Optional[Dict[str, Any]]) -> str:
    """Nombre corto para las columnas del listado, con el largo como respaldo."""
    team = team or {}
    return str(team.get("short_name") or team.get("name") or "")


def top_league_index(match: Dict[str, Any]) -> Optional[int]:
    """Posición de un partido entre las cinco grandes ligas (o ``None``)."""
    tournament = (match or {}).get("tournament") or {}
    raw_id = tournament.get("id")
    try:
        tournament_id = int(raw_id)
    except (TypeError, ValueError):
        tournament_id = None
    if tournament_id in TOP_LEAGUE_IDS:
        return TOP_LEAGUE_IDS[tournament_id]
    name = normalize.normalize_text(tournament.get("name") or "")
    for index, (_, _, aliases) in enumerate(TOP_LEAGUES):
        if name in aliases:
            return index
    return None


def match_section(match: Dict[str, Any]) -> str:
    """Sección visual de un partido: ``top``, ``other`` o ``south``."""
    if top_league_index(match) is not None:
        return "top"
    region = (match or {}).get("region") or regions.region_for_match(match or {})
    if region == regions.REGION_SOUTH_AMERICA:
        return "south"
    return "other"


def _status_rank(match: Dict[str, Any]) -> int:
    status = (match or {}).get("status_type")
    if status in ("inprogress", "live", "halftime"):
        return 0
    if status == "finished":
        return 2
    return 1


def group_matches(
    matches: List[Dict[str, Any]],
) -> List[tuple]:
    """Agrupa y ordena los partidos: 5 grandes, resto de Europa y Sudamérica."""
    sections: Dict[str, List[Dict[str, Any]]] = {
        "top": [],
        "other": [],
        "south": [],
    }
    for match in matches:
        sections[match_section(match)].append(match)

    def tournament_name(match: Dict[str, Any]) -> str:
        return normalize.normalize_text(
            ((match or {}).get("tournament") or {}).get("name") or ""
        )

    sections["top"].sort(
        key=lambda match: (
            _status_rank(match),
            top_league_index(match) or 0,
            match.get("start_timestamp") or 0,
            tournament_name(match),
        )
    )
    for key in ("other", "south"):
        sections[key].sort(
            key=lambda match: (
                _status_rank(match),
                tournament_name(match),
                match.get("start_timestamp") or 0,
            )
        )
    return [(key, sections[key]) for key in ("top", "other", "south") if sections[key]]


WINDOW_OPTIONS = (
    ("Últimos 5", "5"),
    ("Últimos 10", "10"),
    ("Últimos 15", "15"),
    ("Toda la temporada", "all"),
)
SIM_ITERATION_VALUES = ("10000", "25000", "50000", "100000", "250000")
SIM_HISTOGRAM_OPTIONS = (
    ("Goles totales", "goals", "total"),
    ("Goles del local", "goals_home", "home"),
    ("Goles del visitante", "goals_away", "away"),
    ("Córners", "corners", "total"),
    ("Tarjetas", "cards", "total"),
    ("Remates", "shots", "total"),
    ("Remates al arco", "shots_on_target", "total"),
    ("Faltas", "fouls", "total"),
    ("Paradas", "saves", "total"),
)
SIM_MARKET_OPTIONS = (
    ("Goles", "goals"),
    ("Córners", "corners"),
    ("Tarjetas", "cards"),
    ("Remates", "shots"),
    ("Remates al arco", "shots_on_target"),
    ("Faltas", "fouls"),
    ("Paradas", "saves"),
)
TIMEZONES = (
    "local",
    "UTC",
    "Europe/Madrid",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Lisbon",
    "Europe/Istanbul",
    "America/Mexico_City",
    "America/Bogota",
    "America/Lima",
    "America/Santiago",
    "America/Argentina/Buenos_Aires",
    "America/Sao_Paulo",
    "America/Montevideo",
    "America/Asuncion",
    "America/La_Paz",
    "America/Caracas",
    "America/Guayaquil",
)

LIGHT_PALETTE = {
    "bg": "#f2f4f7",
    "fg": "#16191d",
    "muted": "#5b6472",
    "field": "#ffffff",
    "alt": "#e9edf2",
    "border": "#c3cad4",
    "button": "#e8ecf1",
    "button_active": "#dbe1e8",
    "accent": "#0a66c2",
    "accent_active": "#0b5aab",
    "accent_fg": "#ffffff",
    "select_bg": "#cfe3fa",
    "select_fg": "#101418",
    "tab": "#e3e8ee",
    "tab_selected": "#f2f4f7",
    "trough": "#d8dee6",
    "chart_bg": "#ffffff",
    "chart_grid": "#e6eaef",
    "chart_axis": "#b6bfc9",
    "chart_text": "#16191d",
    "chart_muted": "#5b6472",
    "home": "#0a66c2",
    "away": "#e07b39",
    "accent_soft": "#9ec6ef",
    "accent2": "#d9712f",
    "good": "#2e9e5b",
    "warn": "#d99a2b",
    "bad": "#cf4b4b",
    "track": "#e9edf2",
    "card_bg": "#ffffff",
    "card_border": "#d6dde5",
    "section_top_bg": "#e2efff",
    "section_top_fg": "#0a4f9e",
    "section_other_bg": "#eef1f5",
    "section_other_fg": "#5b6472",
    "section_south_bg": "#e5f5ea",
    "section_south_fg": "#237a4b",
}

DARK_PALETTE = {
    "bg": "#1b1f24",
    "fg": "#e7eaee",
    "muted": "#9aa5b1",
    "field": "#232930",
    "alt": "#282f37",
    "border": "#3b444f",
    "button": "#2b323a",
    "button_active": "#36404b",
    "accent": "#2f7ed8",
    "accent_active": "#3c8be4",
    "accent_fg": "#ffffff",
    "select_bg": "#2f6fbe",
    "select_fg": "#ffffff",
    "tab": "#242b32",
    "tab_selected": "#1b1f24",
    "trough": "#2a3139",
    "chart_bg": "#1f252b",
    "chart_grid": "#2d353e",
    "chart_axis": "#46505b",
    "chart_text": "#e7eaee",
    "chart_muted": "#9aa5b1",
    "home": "#4c9bea",
    "away": "#ef9a5a",
    "accent_soft": "#2c4f74",
    "accent2": "#e88a3f",
    "good": "#4cc47d",
    "warn": "#e0b354",
    "bad": "#e06b6b",
    "track": "#2a3139",
    "card_bg": "#232930",
    "card_border": "#39424c",
    "section_top_bg": "#203a55",
    "section_top_fg": "#9ecbff",
    "section_other_bg": "#272e36",
    "section_other_fg": "#aab4bf",
    "section_south_bg": "#20382a",
    "section_south_fg": "#8fd6aa",
}


TOP_LEAGUES = (
    (17, "Premier League", ("premier league",)),
    (8, "LaLiga", ("laliga", "la liga")),
    (23, "Serie A", ("serie a",)),
    (35, "Bundesliga", ("bundesliga",)),
    (34, "Ligue 1", ("ligue 1",)),
)
TOP_LEAGUE_IDS = {tournament_id: index for index, (tournament_id, _, _) in enumerate(TOP_LEAGUES)}
STATUS_FILTER_LABELS = {
    "all": "Todo",
    "live": "En vivo",
    "upcoming": "Próximos",
    "finished": "Finales",
}


def _settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "sofascore-gui" / "settings.json"


def load_preferences() -> Dict[str, Any]:
    """Preferencias guardadas de la interfaz (tema, zona horaria...)."""
    try:
        with _settings_path().open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preferences(preferences: Dict[str, Any]) -> None:
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(preferences, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _format_number(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "—"
    if isinstance(value, (int, float)):
        if abs(value - round(value)) < 1e-9:
            return f"{float(value):.1f}"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    return str(value)


def _format_int(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return _format_number(number)


def _format_difference(value: Any) -> str:
    if value is None:
        return "—"
    number = float(value)
    if abs(number) < 1e-9:
        return "0"
    text = f"{number:+.2f}".rstrip("0").rstrip(".")
    return text.replace("+", "+") if text else "0"


def _short_day(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        return date.fromisoformat(value).strftime("%d/%m/%y")
    except ValueError:
        return value


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # pragma: no cover - depende de Windows
        pass


class SofaScoreApp:
    def __init__(
        self,
        root: tk.Tk,
        client: Optional[SofaScoreClient] = None,
        workers: int = 6,
        timezone_name: str = "local",
        auto_load: bool = True,
        theme: str = "auto",
    ) -> None:
        self.root = root
        self.client = client or SofaScoreClient(ClientConfig(rate_limit=0.08))
        self.extractor = SofaScoreExtractor(self.client, workers=workers)
        self.timezone_name = timezone_name
        self.queue: "queue.Queue[Any]" = queue.Queue()

        preferences = load_preferences()
        if theme in ("oscuro", "dark"):
            initial_dark = True
        elif theme in ("claro", "light"):
            initial_dark = False
        else:
            initial_dark = bool(preferences.get("dark", False))
        self.dark_mode = initial_dark
        self.dark_var = tk.BooleanVar(value=initial_dark)
        self.palette = dict(DARK_PALETTE if initial_dark else LIGHT_PALETTE)

        self.matches: List[Dict[str, Any]] = []
        self.team_matches: List[Dict[str, Any]] = []
        self.team_results: List[Dict[str, Any]] = []
        self.current_day = ""
        self.matches_base_text = ""
        self.day_load_token = 0
        self.loading_rest = False
        self.league_filter_var = tk.StringVar(value="all")
        self.league_label_var = tk.StringVar(value="Todas las competiciones")
        self.status_filter_var = tk.StringVar(value="all")
        self.favorites_only = False
        self.auto_live_var = tk.BooleanVar(
            value=bool(preferences.get("auto_live", True))
        )
        self.alerts_var = tk.BooleanVar(
            value=bool(preferences.get("alerts", True))
        )
        self.favorites: Dict[int, str] = {}
        raw_favorites = preferences.get("favorites") or {}
        if isinstance(raw_favorites, dict):
            for key, value in raw_favorites.items():
                try:
                    self.favorites[int(key)] = str(value)
                except (TypeError, ValueError):
                    continue
        self.live_refresh_running = False
        self._score_snapshot: Dict[int, tuple] = {}
        self._auto_live_job: Optional[str] = None
        self._toast: Optional[tk.Toplevel] = None
        self._tooltip: Optional[tk.Toplevel] = None
        self._tooltip_job: Optional[str] = None
        self._tooltip_iid: Optional[str] = None
        self.storage: Optional[storage.HistoryStore] = None
        self.storage_error = ""
        try:
            self.storage = storage.HistoryStore()
        except Exception as exc:  # noqa: BLE001 - la app sigue funcionando
            self.storage_error = str(exc)
        self._live_desk_window: Optional[live_desk.LiveDeskWindow] = None
        self._journal_window: Optional[journal_window.JournalWindow] = None
        self._preview_window: Optional[preview_window.PreviewWindow] = None
        self._explorer_window: Optional[explorer_window.ExplorerWindow] = None
        self._api_server: Optional[api_server.LocalAPIServer] = None
        self.api_running_var = tk.BooleanVar(value=False)
        if os.name == "nt":
            image_base = Path(
                os.environ.get(
                    "LOCALAPPDATA", Path.home() / "AppData" / "Local"
                )
            )
        else:
            image_base = Path(
                os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
            )
        self._image_dir = image_base / "sofascore-gui" / "images"
        try:
            self._image_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self._image_queue: "queue.Queue[tuple]" = queue.Queue()
        self._image_photos: Dict[tuple, tk.PhotoImage] = {}
        self._image_pending: set = set()
        self._image_failed: set = set()
        self._image_workers_started = False
        self._status_chip_buttons: Dict[str, ttk.Button] = {}
        self.legend_labels: List[tuple] = []
        self._league_submenus: List[tk.Menu] = []
        self.pending_context_match: Optional[Dict[str, Any]] = None
        self.selected_match: Optional[Dict[str, Any]] = None
        self.analysis: Optional[Dict[str, Any]] = None
        self.simulation_summary: Optional[Dict[str, Any]] = None
        self.context_cache: Dict[int, Dict[str, Any]] = {}
        self.context_token = 0
        self.busy = False

        self._build_ui()
        self._build_menu()
        self._bind_shortcuts()
        self._drain_job: Optional[str] = None
        self._drain_job = self.root.after(100, self._drain_queue)
        if self.auto_live_var.get():
            self._auto_live_job = self.root.after(45000, self._auto_live_tick)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if auto_load:
            self.root.after(500, self.load_day)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.title(APP_TITLE)
        width = max(1120, min(1380, self.root.winfo_screenwidth() - 80))
        height = max(720, min(880, self.root.winfo_screenheight() - 140))
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(1120, 720)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Team.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=24)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        header = ttk.Frame(self.root, padding=(14, 10, 14, 4))
        header.pack(fill="x")
        ttk.Label(header, text="Análisis de forma reciente", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            header,
            text="Elige un próximo partido · datos de SofaScore",
            style="Subtitle.TLabel",
        ).pack(side="left", padx=(12, 0), pady=(6, 0))

        tz_frame = ttk.Frame(header)
        tz_frame.pack(side="right")
        self.dark_check = ttk.Checkbutton(
            tz_frame,
            text="Modo oscuro",
            variable=self.dark_var,
            command=self._on_theme_toggle,
        )
        self.dark_check.pack(side="left", padx=(0, 14))
        ttk.Label(tz_frame, text="Zona horaria:", style="Small.TLabel").pack(
            side="left", padx=(0, 4)
        )
        self.tz_var = tk.StringVar(value=self.timezone_name)
        self.tz_combo = ttk.Combobox(
            tz_frame,
            textvariable=self.tz_var,
            values=list(TIMEZONES),
            state="readonly",
            width=26,
        )
        self.tz_combo.pack(side="left")
        self.tz_combo.bind("<<ComboboxSelected>>", self._on_timezone_change)

        status = ttk.Frame(self.root, padding=(14, 4, 14, 8))
        status.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(
            status, textvariable=self.status_var, anchor="w", style="Small.TLabel"
        ).pack(side="left", fill="x", expand=True)
        self.progress = ttk.Progressbar(status, mode="determinate", length=240)
        self.progress.pack(side="right")

        main = ttk.Panedwindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        left = ttk.Frame(main)
        right = ttk.Frame(main, padding=(10, 0, 0, 0))
        main.add(left, weight=2)
        main.add(right, weight=3)

        self._build_left(left)
        self._build_right(right)
        self._apply_theme(self.dark_mode)

    # ------------------------------------------------------------------
    # Menú y atajos
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="Cargar partidos", accelerator="F5", command=self.load_day
        )
        file_menu.add_command(
            label="Exportar análisis CSV",
            accelerator="Ctrl+E",
            command=self.export_csv,
        )
        file_menu.add_command(
            label="Exportar análisis JSON",
            accelerator="Ctrl+Shift+E",
            command=self.export_json,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exportar simulación CSV",
            command=self.export_simulation_csv,
        )
        file_menu.add_command(
            label="Exportar simulación JSON",
            command=self.export_simulation_json,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", accelerator="Ctrl+Q", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_checkbutton(
            label="Modo oscuro",
            variable=self.dark_var,
            command=self._on_theme_toggle,
        )
        view_menu.add_command(
            label="Limpiar filtro", accelerator="Esc", command=self._clear_filter
        )
        view_menu.add_command(
            label="Buscar equipo", accelerator="Ctrl+G", command=self._focus_team_search
        )
        view_menu.add_command(
            label="Solo favoritos", command=self._toggle_favorites_only
        )
        view_menu.add_command(
            label="Actualizar partidos en vivo", command=self._refresh_live_async
        )
        view_menu.add_checkbutton(
            label="Alertas de favoritos",
            variable=self.alerts_var,
            command=self._on_alerts_toggle,
        )
        view_menu.add_command(
            label="Ir a Simulación",
            command=lambda: self.result_notebook.select(self.simulation_tab),
        )
        menubar.add_cascade(label="Ver", menu=view_menu)

        apps_menu = tk.Menu(menubar, tearoff=False)
        apps_menu.add_command(
            label="Sala de directo",
            accelerator="Ctrl+Shift+L",
            command=self.open_live_desk,
        )
        apps_menu.add_command(
            label="Cuaderno de predicciones",
            accelerator="Ctrl+Shift+P",
            command=self.open_journal,
        )
        apps_menu.add_command(
            label="Estudio de previas",
            accelerator="Ctrl+Shift+R",
            command=self.open_preview_studio,
        )
        apps_menu.add_command(
            label="Explorador de datos",
            accelerator="Ctrl+Shift+D",
            command=self.open_explorer,
        )
        apps_menu.add_separator()
        apps_menu.add_checkbutton(
            label="API local",
            variable=self.api_running_var,
            command=self._toggle_local_api,
        )
        apps_menu.add_command(
            label="Abrir carpeta de datos",
            command=self._open_data_folder,
        )
        menubar.add_cascade(label="Aplicaciones", menu=apps_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label="Atajos y consejos", accelerator="F1", command=self._show_help
        )
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de SofaScore", command=self._about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.root.config(menu=menubar)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F5>", lambda _event: self.load_day())
        self.root.bind("<Control-r>", lambda _event: self.load_day())
        self.root.bind("<Control-e>", lambda _event: self.export_csv())
        self.root.bind("<Control-Shift-E>", lambda _event: self.export_json())
        self.root.bind("<Control-q>", lambda _event: self._on_close())
        self.root.bind("<Control-d>", lambda _event: self._toggle_dark())
        self.root.bind("<Control-f>", lambda _event: self._focus_filter())
        self.root.bind("<Control-g>", lambda _event: self._focus_team_search())
        self.root.bind("<F1>", lambda _event: self._show_help())
        self.root.bind(
            "<Control-Shift-L>", lambda _event: self.open_live_desk()
        )
        self.root.bind(
            "<Control-Shift-P>", lambda _event: self.open_journal()
        )
        self.root.bind(
            "<Control-Shift-R>", lambda _event: self.open_preview_studio()
        )
        self.root.bind(
            "<Control-Shift-D>", lambda _event: self.open_explorer()
        )
        self.root.bind("<Escape>", lambda _event: self._clear_filter())
        self.matches_tree.bind("<Double-1>", self._on_match_double_click)
        self.team_matches_tree.bind("<Double-1>", self._on_match_double_click)
        self.team_tree.bind("<Double-1>", self._on_team_double_click)
        self.matches_tree.bind("<Button-3>", self._on_match_context)
        self.team_matches_tree.bind("<Button-3>", self._on_match_context)
        self.team_tree.bind("<Button-3>", self._on_team_context)
        self.matches_tree.bind("<Return>", self._on_match_double_click)
        self.team_matches_tree.bind("<Return>", self._on_match_double_click)
        self.team_tree.bind("<Return>", self._on_team_double_click)

    def _toggle_dark(self) -> None:
        self.dark_var.set(not self.dark_mode)
        self._on_theme_toggle()

    def _clear_filter(self) -> None:
        had_league = self.league_filter_var.get() != "all"
        had_status = (
            self.status_filter_var.get() != "all" or self.favorites_only
        )
        if had_league:
            self._reset_league_filter()
        if had_status:
            self._reset_status_filters()
        if self.match_filter_var.get():
            self.match_filter_var.set("")
        elif had_league or had_status:
            self._render_matches()
        self._focus_filter()

    # ------------------------------------------------------------------
    # Favoritos, chips de estado y alertas
    # ------------------------------------------------------------------
    def _team_id(self, team: Optional[Dict[str, Any]]) -> Optional[int]:
        try:
            return int((team or {}).get("id"))
        except (TypeError, ValueError):
            return None

    def _match_has_favorite(self, match: Dict[str, Any]) -> bool:
        for key in ("home_team", "away_team"):
            team_id = self._team_id(match.get(key))
            if team_id is not None and team_id in self.favorites:
                return True
        return False

    def _save_preference(self, key: str, value: Any) -> None:
        preferences = load_preferences()
        preferences[key] = value
        save_preferences(preferences)

    def _save_favorites(self) -> None:
        self._save_preference(
            "favorites", {str(key): name for key, name in self.favorites.items()}
        )

    def _toggle_favorite(self, team_id: Optional[int], name: str) -> None:
        if team_id is None:
            return
        name = str(name or team_id)
        if team_id in self.favorites:
            self.favorites.pop(team_id, None)
            self.status_var.set(f"☆ {name} eliminado de favoritos.")
        else:
            self.favorites[team_id] = name
            self.status_var.set(
                f"★ {name} añadido a favoritos. Recibirás alertas si está activado."
            )
        self._save_favorites()
        if self.favorites_only and not self.favorites:
            self.favorites_only = False
        self._render_matches()
        self._refresh_favorite_menu()
        self._refresh_team_stars()

    def _refresh_team_stars(self) -> None:
        if not hasattr(self, "team_tree"):
            return
        for team in self.team_results:
            team_id = self._team_id(team)
            if team_id is None:
                continue
            iid = str(team_id)
            if not self.team_tree.exists(iid):
                continue
            name = str(team.get("name") or "")
            if team_id in self.favorites:
                name = f"★ {name}"
            values = list(self.team_tree.item(iid, "values"))
            if values:
                values[0] = name
                self.team_tree.item(iid, values=values)

    def _refresh_favorite_menu(self) -> None:
        if not hasattr(self, "fav_menu"):
            return
        menu = self.fav_menu
        menu.delete(0, "end")
        match = self.selected_match
        if not match:
            menu.add_command(label="Selecciona un partido", state="disabled")
            try:
                self.fav_btn.configure(text="☆ Favoritos")
            except tk.TclError:
                pass
            return
        has_favorite = self._match_has_favorite(match)
        try:
            self.fav_btn.configure(
                text="★ Favoritos" if has_favorite else "☆ Favoritos"
            )
        except tk.TclError:
            pass
        for key in ("home_team", "away_team"):
            team = match.get(key) or {}
            team_id = self._team_id(team)
            if team_id is None:
                continue
            name = _team_label(team) or str(team_id)
            if team_id in self.favorites:
                menu.add_command(
                    label=f"☆ Quitar {name} de favoritos",
                    command=lambda tid=team_id, label=name: self._toggle_favorite(
                        tid, label
                    ),
                )
            else:
                menu.add_command(
                    label=f"★ Añadir {name} a favoritos",
                    command=lambda tid=team_id, label=name: self._toggle_favorite(
                        tid, label
                    ),
                )
        menu.add_separator()
        menu.add_command(
            label=(
                "Quitar filtro de favoritos"
                if self.favorites_only
                else "Ver solo favoritos"
            ),
            command=self._toggle_favorites_only,
        )
        menu.add_checkbutton(
            label="Alertas de favoritos",
            variable=self.alerts_var,
            command=self._on_alerts_toggle,
        )

    def _toggle_favorites_only(self) -> None:
        if not self.favorites and not self.favorites_only:
            self.status_var.set(
                "Aún no tienes favoritos: usa ☆ Favoritos o el clic derecho."
            )
            return
        self.favorites_only = not self.favorites_only
        self._render_matches()
        self._refresh_favorite_menu()

    def _match_from_tree(
        self, tree: ttk.Treeview, iid: str
    ) -> Optional[Dict[str, Any]]:
        try:
            match_id = int(iid)
        except (TypeError, ValueError):
            return None
        pool = self.matches if tree is self.matches_tree else self.team_matches
        return next((item for item in pool if item.get("id") == match_id), None)

    def _on_match_context(self, event) -> None:
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid or str(iid).startswith("__section__"):
            return
        tree.selection_set(iid)
        match = self._match_from_tree(tree, iid)
        if not match:
            return
        menu = tk.Menu(self.root, tearoff=False)
        for key in ("home_team", "away_team"):
            team = match.get(key) or {}
            team_id = self._team_id(team)
            if team_id is None:
                continue
            name = _team_label(team) or str(team_id)
            if team_id in self.favorites:
                menu.add_command(
                    label=f"☆ Quitar {name} de favoritos",
                    command=lambda tid=team_id, label=name: self._toggle_favorite(
                        tid, label
                    ),
                )
            else:
                menu.add_command(
                    label=f"★ Añadir {name} a favoritos",
                    command=lambda tid=team_id, label=name: self._toggle_favorite(
                        tid, label
                    ),
                )
        menu.add_separator()
        menu.add_command(
            label=(
                "Quitar filtro de favoritos"
                if self.favorites_only
                else "Ver solo favoritos"
            ),
            command=self._toggle_favorites_only,
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_team_context(self, event) -> None:
        tree = self.team_tree
        iid = tree.identify_row(event.y)
        if not iid:
            return
        tree.selection_set(iid)
        values = tree.item(iid, "values")
        name = str(values[0]) if values else iid
        try:
            team_id = int(iid)
        except (TypeError, ValueError):
            return
        menu = tk.Menu(self.root, tearoff=False)
        if team_id in self.favorites:
            menu.add_command(
                label=f"☆ Quitar {name} de favoritos",
                command=lambda: self._toggle_favorite(team_id, name),
            )
        else:
            menu.add_command(
                label=f"★ Añadir {name} a favoritos",
                command=lambda: self._toggle_favorite(team_id, name),
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_status_chip(self, key: str) -> None:
        if key == "favorites":
            self._toggle_favorites_only()
            return
        if key == "all":
            self.status_filter_var.set("all")
            self.favorites_only = False
            self._render_matches()
            return
        current = self.status_filter_var.get()
        self.status_filter_var.set("all" if current == key else key)
        self._render_matches()

    def _update_status_chips(self) -> None:
        for key, button in self._status_chip_buttons.items():
            if key == "favorites":
                active = self.favorites_only
            else:
                active = self.status_filter_var.get() == key
            try:
                button.configure(
                    style="ChipActive.TButton" if active else "Chip.TButton"
                )
            except tk.TclError:
                continue

    def _reset_status_filters(self) -> None:
        self.status_filter_var.set("all")
        self.favorites_only = False
        self._update_status_chips()

    def _on_alerts_toggle(self) -> None:
        self._save_preference("alerts", bool(self.alerts_var.get()))

    def _on_auto_live_toggle(self) -> None:
        enabled = bool(self.auto_live_var.get())
        self._save_preference("auto_live", enabled)
        try:
            self.auto_live_check.configure(text="Auto en vivo")
        except (AttributeError, tk.TclError):
            pass
        if self._auto_live_job is not None:
            try:
                self.root.after_cancel(self._auto_live_job)
            except tk.TclError:
                pass
            self._auto_live_job = None
        if enabled:
            self._auto_live_job = self.root.after(1000, self._auto_live_tick)
            self.status_var.set("Actualización automática de partidos en vivo activada.")
        else:
            self.status_var.set("Actualización automática de partidos en vivo desactivada.")

    def _auto_live_tick(self) -> None:
        self._auto_live_job = self.root.after(45000, self._auto_live_tick)
        if (
            not self.auto_live_var.get()
            or self.busy
            or self.loading_rest
            or self.live_refresh_running
        ):
            return
        if not self._needs_live_refresh():
            return
        self._refresh_live_async()

    def _needs_live_refresh(self) -> bool:
        now = time.time()
        for match in self.matches:
            if match.get("status_type") in ("inprogress", "live", "halftime"):
                return True
            if not self._match_has_favorite(match):
                continue
            timestamp = match.get("start_timestamp")
            if timestamp is None:
                continue
            try:
                difference = int(timestamp) - now
            except (TypeError, ValueError):
                continue
            if 0 <= difference <= 1800:
                return True
        return False

    def _refresh_live_async(self) -> None:
        if self.live_refresh_running:
            return
        self.live_refresh_running = True
        live_ids = [
            match.get("id")
            for match in self.matches
            if match.get("id") is not None
            and match.get("status_type") in ("inprogress", "live", "halftime")
        ]

        def work() -> None:
            try:
                live = self.extractor.get_live_matches()
            except Exception as exc:  # noqa: BLE001 - actualización silenciosa
                self._post(self._finish_live_refresh, exc)
                return
            updates = {
                match.get("id"): match
                for match in live
                if match.get("id") is not None
            }
            # Si un partido acaba de terminar, el endpoint en vivo puede
            # dejar de devolverlo. Consultamos unos pocos para actualizar
            # el marcador final sin recargar toda la fecha.
            missing = [item for item in live_ids if item not in updates][:6]
            for match_id in missing:
                try:
                    detail = self.extractor.get_match(int(match_id))
                except Exception:
                    continue
                updated = (detail or {}).get("match")
                if updated:
                    updates[match_id] = updated
            self._post(self._apply_live_updates, list(updates.values()))

        threading.Thread(target=work, daemon=True).start()

    def _finish_live_refresh(self, _exc: Optional[BaseException] = None) -> None:
        self.live_refresh_running = False

    def _remember_scores(self, matches: List[Dict[str, Any]]) -> None:
        self._score_snapshot = {
            match.get("id"): (
                match.get("status_type"),
                match.get("home_score"),
                match.get("away_score"),
            )
            for match in matches
        }

    def _alert_changes(
        self, match: Dict[str, Any], old: tuple, new: Dict[str, Any]
    ) -> None:
        if not self.alerts_var.get() or not self._match_has_favorite(match):
            return
        old_status, old_home, old_away = old
        new_status = new.get("status_type")
        new_home = new.get("home_score")
        new_away = new.get("away_score")
        home = _team_label(match.get("home_team")) or "Local"
        away = _team_label(match.get("away_team")) or "Visitante"
        messages: List[str] = []
        live_statuses = ("inprogress", "live", "halftime")
        if old_status not in live_statuses and new_status in live_statuses:
            messages.append(f"Comienza {home} vs {away}")
        if (
            old_home is not None
            and old_away is not None
            and new_home is not None
            and new_away is not None
            and (old_home, old_away) != (new_home, new_away)
            and new_status in live_statuses
        ):
            messages.append(f"⚽ {home} {new_home}-{new_away} {away}")
        if old_status in live_statuses and new_status == "finished":
            messages.append(f"Final: {home} {new_home}-{new_away} {away}")
        if messages:
            self._notify("SofaScore · Favoritos", " · ".join(messages), match.get("id"))

    def _apply_live_updates(self, live_matches: List[Dict[str, Any]]) -> None:
        self.live_refresh_running = False
        try:
            self.auto_live_check.configure(
                text=f"Auto · {datetime.now().strftime('%H:%M')}"
            )
        except (AttributeError, tk.TclError):
            pass
        updates = {
            match.get("id"): match
            for match in live_matches
            if match.get("id") is not None
        }
        if not updates:
            return
        selected_id = self.selected_match.get("id") if self.selected_match else None
        changed = False
        updated_matches: List[Dict[str, Any]] = []
        for match in self.matches:
            update = updates.get(match.get("id"))
            if update is None:
                continue
            old = self._score_snapshot.get(match.get("id"))
            if old is not None:
                self._alert_changes(match, old, update)
            region = match.get("region")
            match.update(update)
            if region and not match.get("region"):
                match["region"] = region
            updated_matches.append(match)
            changed = True
        if not changed:
            return
        self._remember_scores(self.matches)
        if self.storage is not None:
            try:
                for match in updated_matches:
                    self.storage.update_match_result(match)
                if updated_matches:
                    self._refresh_history_windows()
            except Exception:
                pass
        self._render_matches()
        if selected_id is not None and selected_id in updates:
            self._update_match_header()
            self._refresh_favorite_menu()
        if self._window_alive(self._live_desk_window):
            self._live_desk_window.refresh()

    def _select_match_by_id(self, match_id: Optional[int]) -> None:
        if match_id is None:
            return
        match = next(
            (item for item in self.matches if item.get("id") == match_id), None
        )
        if match is None:
            return
        try:
            self.left_notebook.select(0)
            self.matches_tree.selection_set(str(match_id))
            self.matches_tree.see(str(match_id))
        except tk.TclError:
            return
        self.selected_match = match
        self._update_match_header()
        if not self.busy:
            self._load_match_context(match)

    def _notify(
        self, title: str, message: str, match_id: Optional[int] = None
    ) -> None:
        if not self.alerts_var.get():
            return
        try:
            self.root.bell()
        except tk.TclError:
            pass
        try:
            if getattr(self, "_toast", None) is not None:
                self._close_toast()
        except tk.TclError:
            pass
        palette = self.palette
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        frame = tk.Frame(
            toast,
            background=palette["card_bg"],
            highlightbackground=palette["accent"],
            highlightthickness=2,
            padx=12,
            pady=8,
        )
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, background=palette["card_bg"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=title,
            background=palette["card_bg"],
            foreground=palette["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(side="left")
        close = tk.Label(
            header,
            text="×",
            background=palette["card_bg"],
            foreground=palette["muted"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        close.pack(side="right")
        body = tk.Label(
            frame,
            text=message,
            background=palette["card_bg"],
            foreground=palette["fg"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=300,
        )
        body.pack(fill="x", pady=(4, 0))
        close.bind("<Button-1>", lambda _event: self._close_toast())
        if match_id is not None:
            for widget in (frame, header, body):
                widget.configure(cursor="hand2")
                widget.bind(
                    "<Button-1>",
                    lambda _event: (
                        self._close_toast(),
                        self._select_match_by_id(match_id),
                    ),
                )
        toast.update_idletasks()
        width = max(260, toast.winfo_reqwidth())
        height = toast.winfo_reqheight()
        x = self.root.winfo_rootx() + self.root.winfo_width() - width - 24
        y = self.root.winfo_rooty() + self.root.winfo_height() - height - 24
        toast.geometry(f"{width}x{height}+{x}+{y}")
        toast.after(7000, self._close_toast)
        self._toast = toast

    def _close_toast(self) -> None:
        toast = self._toast
        self._toast = None
        if toast is not None:
            try:
                toast.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Tooltips y ayuda contextual
    # ------------------------------------------------------------------
    def _bind_tooltip(self, widget: tk.Misc, text: str) -> None:
        widget.bind(
            "<Enter>",
            lambda event: self._show_tooltip(text, event.x_root, event.y_root),
            add="+",
        )
        widget.bind("<Leave>", lambda _event: self._hide_tooltip(), add="+")

    def _hide_tooltip(self, reset: bool = True) -> None:
        if self._tooltip_job is not None:
            try:
                self.root.after_cancel(self._tooltip_job)
            except tk.TclError:
                pass
            self._tooltip_job = None
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except tk.TclError:
                pass
            self._tooltip = None
        if reset:
            self._tooltip_iid = None

    def _show_tooltip(self, text: str, x_root: int, y_root: int) -> None:
        self._hide_tooltip(reset=False)
        if not text:
            return
        palette = self.palette
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        frame = tk.Frame(
            top,
            background=palette["card_bg"],
            highlightbackground=palette["border"],
            highlightthickness=1,
            padx=10,
            pady=7,
        )
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=text,
            background=palette["card_bg"],
            foreground=palette["fg"],
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
            wraplength=380,
        ).pack(fill="both", expand=True)
        top.update_idletasks()
        width = top.winfo_reqwidth()
        height = top.winfo_reqheight()
        vx = self.root.winfo_vrootx()
        vy = self.root.winfo_vrooty()
        vw = self.root.winfo_vrootwidth()
        vh = self.root.winfo_vrootheight()
        if vw <= 1:
            vx, vw = 0, self.root.winfo_screenwidth()
        if vh <= 1:
            vy, vh = 0, self.root.winfo_screenheight()
        x = min(max(vx + 4, x_root + 14), vx + vw - width - 8)
        y = min(max(vy + 4, y_root + 18), vy + vh - height - 8)
        top.geometry(f"+{x}+{y}")
        self._tooltip = top

    def _match_tooltip_text(self, match: Dict[str, Any]) -> str:
        tournament = match.get("tournament") or {}
        home = (match.get("home_team") or {}).get("name") or "Local"
        away = (match.get("away_team") or {}).get("name") or "Visitante"
        lines = [f"{home}  vs  {away}"]
        competition = tournament.get("name") or ""
        country = tournament.get("country") or ""
        if competition:
            lines.append(
                f"{competition}" + (f" · {country}" if country else "")
            )
        status = self._match_status_text(match)
        if status:
            lines.append(status)
        timestamp = match.get("start_timestamp")
        if timestamp is not None:
            try:
                tz = resolve_timezone(self._tz_name())
                moment = datetime.fromtimestamp(int(timestamp), tz=tz)
                lines.append(moment.strftime("%d/%m/%Y %H:%M"))
            except Exception:
                pass
        round_number = match.get("round")
        if round_number:
            lines.append(f"Jornada {round_number}")
        venue = match.get("venue") or {}
        venue_name = venue.get("name")
        if venue_name:
            city = (venue.get("city") or {}).get("name")
            lines.append(
                f"Estadio: {venue_name}"
                + (f" ({city})" if city else "")
            )
        return "\n".join(lines)

    def _on_match_motion(self, event) -> None:
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid or str(iid).startswith("__section__"):
            self._hide_tooltip()
            return
        if iid == self._tooltip_iid:
            return
        self._hide_tooltip()
        match = self._match_from_tree(tree, iid)
        if match is None:
            return
        self._tooltip_iid = iid
        text = self._match_tooltip_text(match)
        self._tooltip_job = self.root.after(
            450,
            lambda x=event.x_root, y=event.y_root: self._show_tooltip(text, x, y),
        )

    def _update_status_badge(self, match: Optional[Dict[str, Any]]) -> None:
        if not hasattr(self, "status_badge"):
            return
        if not match:
            try:
                self.status_badge.pack_forget()
            except tk.TclError:
                pass
            return
        if not self.status_badge.winfo_manager():
            self.status_badge.pack(side="right", padx=(8, 0))
        status = match.get("status_type")
        if status in ("inprogress", "live", "halftime"):
            minute = form.match_minute(match)
            text = f"EN VIVO {int(minute)}'" if minute > 0 else "EN VIVO"
            color = self.palette["bad"]
        elif status == "finished":
            text = "FINAL"
            color = self.palette["muted"]
        else:
            text = "PRÓXIMO"
            color = self.palette["accent"]
        try:
            self.status_badge.configure(text=text, background=color)
        except tk.TclError:
            pass

    def _show_help(self) -> None:
        messagebox.showinfo(
            "Atajos y consejos",
            (
                "Atajos principales\n\n"
                "F5 / Ctrl+R  ·  recargar la fecha\n"
                "Ctrl+E  ·  exportar análisis a CSV\n"
                "Ctrl+Shift+E  ·  exportar análisis a JSON\n"
                "Ctrl+D  ·  cambiar tema\n"
                "Ctrl+F  ·  buscar en el listado\n"
                "Ctrl+G  ·  buscar equipo\n"
                "Ctrl+Shift+L  ·  sala de directo\n"
                "Ctrl+Shift+P  ·  cuaderno de predicciones\n"
                "Ctrl+Shift+R  ·  estudio de previas\n"
                "Ctrl+Shift+D  ·  explorador de datos\n"
                "Esc  ·  limpiar todos los filtros\n"
                "F1  ·  mostrar esta ayuda\n\n"
                "Consejos\n"
                "• Usa Liga para filtrar por competición.\n"
                "• Los chips Vivo, Próx., Final y ★ Favs filtran al instante.\n"
                "• Pasa el ratón por un partido para ver todos sus datos.\n"
                "• Clic derecho en un partido o equipo para gestionar favoritos.\n"
                "• Auto en vivo actualiza los marcadores cada 45 segundos.\n"
                "• Las predicciones se guardan solas en el cuaderno."
            ),
            parent=self.root,
        )

    # ------------------------------------------------------------------
    # Aplicaciones integradas
    # ------------------------------------------------------------------
    def _window_alive(self, window: Optional[tk.Toplevel]) -> bool:
        try:
            return window is not None and bool(window.winfo_exists())
        except tk.TclError:
            return False

    def _storage_or_error(self) -> Optional[storage.HistoryStore]:
        if self.storage is None:
            messagebox.showerror(
                "Historial no disponible",
                "No se pudo abrir la base de datos local.\n\n"
                + (self.storage_error or "Comprueba los permisos de escritura."),
                parent=self.root,
            )
            return None
        return self.storage

    def open_live_desk(self) -> None:
        if self._window_alive(self._live_desk_window):
            self._live_desk_window.lift()
            self._live_desk_window.focus_force()
            return
        self._live_desk_window = live_desk.LiveDeskWindow(self)

    def open_journal(self) -> None:
        store = self._storage_or_error()
        if store is None:
            return
        if self._window_alive(self._journal_window):
            self._journal_window.lift()
            self._journal_window.refresh()
            return
        self._journal_window = journal_window.JournalWindow(self, store)

    def open_preview_studio(self) -> None:
        if not self.analysis:
            messagebox.showinfo(
                "Estudio de previas",
                "Analiza primero un partido para generar la previa.",
                parent=self.root,
            )
            return
        summary = None
        analysis_id = ((self.analysis or {}).get("match") or {}).get("id")
        summary_id = ((self.simulation_summary or {}).get("meta") or {}).get(
            "match_id"
        )
        if self.simulation_summary is not None and analysis_id == summary_id:
            summary = self.simulation_summary
        if self._window_alive(self._preview_window):
            self._preview_window.destroy()
        self._preview_window = preview_window.PreviewWindow(
            self, self.analysis, summary
        )

    def open_explorer(self) -> None:
        store = self._storage_or_error()
        if store is None:
            return
        if self._window_alive(self._explorer_window):
            self._explorer_window.lift()
            self._explorer_window.refresh()
            self._explorer_window.refresh_api_state()
            return
        self._explorer_window = explorer_window.ExplorerWindow(self, store)

    def local_api_running(self) -> bool:
        return self._api_server is not None and self._api_server.running

    def local_api_url(self) -> str:
        return self._api_server.url if self._api_server is not None else ""

    def start_local_api(self) -> str:
        store = self._storage_or_error()
        if store is None:
            raise OSError("El historial local no está disponible.")
        if self.local_api_running():
            return self.local_api_url()
        self._api_server = api_server.LocalAPIServer(store)
        url = self._api_server.start()
        self.api_running_var.set(True)
        self.status_var.set(f"API local activa en {url}")
        if self._window_alive(self._explorer_window):
            self._explorer_window.refresh_api_state()
        return url

    def stop_local_api(self) -> None:
        if self._api_server is not None:
            self._api_server.stop()
            self._api_server = None
        self.api_running_var.set(False)
        self.status_var.set("API local detenida.")
        if self._window_alive(self._explorer_window):
            self._explorer_window.refresh_api_state()

    def _toggle_local_api(self) -> None:
        if self.api_running_var.get():
            try:
                self.start_local_api()
            except OSError as exc:
                self.api_running_var.set(False)
                messagebox.showerror("API local", str(exc), parent=self.root)
        else:
            self.stop_local_api()

    def _open_data_folder(self) -> None:
        if self.storage is None:
            return
        folder = self.storage.path.parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        try:
            if os.name == "nt":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                import webbrowser

                webbrowser.open(folder.as_uri())
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Carpeta de datos", str(exc), parent=self.root
            )

    def _refresh_history_windows(self) -> None:
        if self._window_alive(self._journal_window):
            try:
                self._journal_window.refresh()
            except tk.TclError:
                pass
        if self._window_alive(self._explorer_window):
            try:
                self._explorer_window.refresh()
            except tk.TclError:
                pass

    def _save_matches_history(self, matches: List[Dict[str, Any]], day: str) -> None:
        if self.storage is None:
            return
        try:
            self.storage.save_matches(matches, day)
            if self._window_alive(self._explorer_window):
                self._explorer_window.refresh()
        except Exception:
            pass

    def _save_match_history(self, match: Dict[str, Any]) -> None:
        if self.storage is None:
            return
        try:
            self.storage.save_match(match)
        except Exception:
            pass

    def _save_analysis_history(self, analysis: Dict[str, Any]) -> None:
        if self.storage is None:
            return
        try:
            self.storage.save_analysis(analysis)
        except Exception:
            pass

    def _save_prediction_history(
        self, summary: Dict[str, Any], analysis: Dict[str, Any]
    ) -> None:
        if self.storage is None:
            return
        try:
            stored = dict(summary)
            meta = dict(summary.get("meta") or {})
            meta["model_version"] = __version__
            stored["meta"] = meta
            self.storage.save_prediction(stored, analysis)
            self._refresh_history_windows()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Escudos y banderas (imágenes con caché en disco)
    # ------------------------------------------------------------------
    def _start_image_workers(self) -> None:
        if self._image_workers_started:
            return
        self._image_workers_started = True
        for _ in range(3):
            threading.Thread(target=self._image_worker, daemon=True).start()

    def _image_path(self, key: tuple) -> Path:
        kind, item_id = key
        return self._image_dir / f"{kind}_{item_id}.png"

    def _load_photo(
        self, key: tuple, path: Path, size: int
    ) -> Optional[tk.PhotoImage]:
        existing = self._image_photos.get((key, size))
        if existing is not None:
            return existing
        try:
            image = tk.PhotoImage(file=str(path))
        except (tk.TclError, OSError):
            self._image_failed.add(key)
            return None
        factor = max(
            1,
            (max(image.width(), image.height()) + size - 1) // size,
        )
        if factor > 1:
            image = image.subsample(factor)
        self._image_photos[(key, size)] = image
        return image

    def _queue_image(self, kind: str, item_id: Any) -> None:
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            return
        key = (kind, item_id)
        if (
            key in self._image_photos
            or key in self._image_pending
            or key in self._image_failed
        ):
            return
        path = self._image_path(key)
        if path.exists():
            self._load_photo(key, path, 18 if kind == "team" else 16)
            self._load_photo(key, path, 28 if kind == "team" else 16)
            return
        self._image_pending.add(key)
        self._start_image_workers()
        self._image_queue.put(key)

    def _image_worker(self) -> None:
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:  # pragma: no cover - dependencia obligatoria
            return
        while True:
            key = self._image_queue.get()
            kind, item_id = key
            path = self._image_path(key)
            if path.exists():
                self._post(self._image_ready, key, True)
                continue
            if kind == "team":
                url = f"https://img.sofascore.com/api/v1/team/{item_id}/image"
            else:
                url = (
                    f"https://img.sofascore.com/api/v1/category/{item_id}/image"
                )
            ok = False
            for interface in ("0.0.0.0", None):
                kwargs: Dict[str, Any] = {
                    "headers": {
                        "Accept": "image/png,image/*",
                        "Referer": "https://www.sofascore.com/",
                    },
                    "timeout": 20,
                    "impersonate": "chrome",
                }
                if interface is not None:
                    kwargs["interface"] = interface
                try:
                    response = curl_requests.get(url, **kwargs)
                except Exception:
                    continue
                if (
                    response.status_code == 200
                    and response.content.startswith(b"\x89PNG")
                ):
                    try:
                        tmp = path.with_suffix(".tmp")
                        tmp.write_bytes(response.content)
                        os.replace(tmp, path)
                        ok = True
                    except OSError:
                        ok = False
                    break
            self._post(self._image_ready, key, ok)

    def _image_ready(self, key: tuple, ok: bool) -> None:
        self._image_pending.discard(key)
        if not ok:
            self._image_failed.add(key)
            return
        path = self._image_path(key)
        if key[0] == "team":
            self._load_photo(key, path, 18)
            self._load_photo(key, path, 28)
            self._apply_image_to_rows(key)
            if self.selected_match:
                self._update_header_images()
        else:
            self._load_photo(key, path, 16)
            if self.selected_match:
                self._update_header_images()

    def _photo(self, kind: str, item_id: Any, size: int) -> Optional[tk.PhotoImage]:
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            return None
        key = (kind, item_id)
        photo = self._image_photos.get((key, size))
        if photo is not None:
            return photo
        path = self._image_path(key)
        if path.exists():
            return self._load_photo(key, path, size)
        self._queue_image(kind, item_id)
        return None

    def _row_crest(self, match: Dict[str, Any]) -> Any:
        team = match.get("home_team") or {}
        team_id = self._team_id(team)
        if team_id is None:
            return ""
        photo = self._photo("team", team_id, 18)
        return photo or ""

    def _sync_row_icons(self, tree: ttk.Treeview) -> None:
        pool = self.matches if tree is self.matches_tree else self.team_matches
        for match in pool:
            iid = str(match.get("id"))
            if not tree.exists(iid):
                continue
            photo = self._row_crest(match)
            if photo:
                tree.item(iid, image=photo)

    def _apply_image_to_rows(self, key: tuple) -> None:
        if key[0] != "team":
            return
        team_id = key[1]
        photo = self._image_photos.get((key, 18))
        if photo is None:
            return
        for match in self.matches:
            home = match.get("home_team") or {}
            if self._team_id(home) != team_id:
                continue
            iid = str(match.get("id"))
            if self.matches_tree.exists(iid):
                self.matches_tree.item(iid, image=photo)
        for match in self.team_matches:
            home = match.get("home_team") or {}
            if self._team_id(home) != team_id:
                continue
            iid = str(match.get("id"))
            if self.team_matches_tree.exists(iid):
                self.team_matches_tree.item(iid, image=photo)

    def _draw_team_placeholder(
        self, canvas: tk.Canvas, team: Dict[str, Any]
    ) -> None:
        canvas.delete("all")
        label = _team_label(team)
        initials = "".join(
            part[0] for part in label.split()[:2] if part
        ).upper() or "?"
        canvas.create_text(
            16,
            16,
            text=initials,
            fill=self.palette["muted"],
            font=("Segoe UI", 9, "bold"),
        )

    def _update_header_images(self) -> None:
        if not hasattr(self, "home_crest_canvas"):
            return
        match = self.selected_match
        if not match:
            for canvas in (self.home_crest_canvas, self.away_crest_canvas):
                canvas.delete("all")
            self.comp_flag_canvas.delete("all")
            return
        home_team = match.get("home_team") or {}
        away_team = match.get("away_team") or {}
        for canvas, team in (
            (self.home_crest_canvas, home_team),
            (self.away_crest_canvas, away_team),
        ):
            self._draw_team_placeholder(canvas, team)
            team_id = self._team_id(team)
            if team_id is None:
                continue
            photo = self._photo("team", team_id, 28)
            if photo is not None:
                canvas.delete("all")
                canvas.create_image(16, 16, image=photo)
        self.comp_flag_canvas.delete("all")
        category_id = (match.get("tournament") or {}).get("category_id")
        if category_id is not None:
            photo = self._photo("category", category_id, 16)
            if photo is not None:
                self.comp_flag_canvas.create_image(
                    11, 8, image=photo
                )

    def _focus_filter(self) -> None:
        try:
            self.left_notebook.select(0)
        except tk.TclError:
            pass
        self.match_filter_entry.focus_set()
        self.match_filter_entry.select_range(0, "end")

    def _focus_team_search(self) -> None:
        try:
            self.left_notebook.select(1)
        except tk.TclError:
            pass
        self.team_entry.focus_set()
        self.team_entry.select_range(0, "end")

    def _on_close(self) -> None:
        if self._api_server is not None:
            try:
                self._api_server.stop()
            except Exception:
                pass
            self._api_server = None
        if self._window_alive(self._live_desk_window):
            try:
                self._live_desk_window.close()
            except tk.TclError:
                pass
        for window in (
            self._journal_window,
            self._preview_window,
            self._explorer_window,
        ):
            if self._window_alive(window):
                try:
                    window.destroy()
                except tk.TclError:
                    pass
        for job in (
            getattr(self, "_drain_job", None),
            getattr(self, "_auto_live_job", None),
            getattr(self, "_tooltip_job", None),
        ):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self._drain_job = None
        self._auto_live_job = None
        self._tooltip_job = None
        self._hide_tooltip()
        if getattr(self, "_toast", None) is not None:
            self._close_toast()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _about(self) -> None:
        model = neural.model_version()
        model_text = (
            "modelo neuronal activo"
            if model != "none"
            else "modelo neuronal no disponible"
        )
        messagebox.showinfo(
            "Acerca de SofaScore",
            (
                f"SofaScore · Análisis de forma {__version__}\n\n"
                "Datos: API interna de SofaScore.\n"
                f"Simulación: Monte Carlo con NumPy, {model_text}.\n"
                "Gráficos: Canvas de Tkinter, sin dependencias externas.\n\n"
                "Proyecto no afiliado a SofaScore."
            ),
            parent=self.root,
        )

    def _on_match_double_click(self, event=None) -> None:
        tree = event.widget if event is not None else None
        if tree is None or not tree.selection():
            return
        if str(tree.selection()[0]).startswith("__section__"):
            return
        self.analyze()

    def _on_team_double_click(self, _event=None) -> None:
        if self._selected_team_id() is not None:
            self.view_team_matches()

    # ------------------------------------------------------------------
    # Tema claro / oscuro
    # ------------------------------------------------------------------
    def _apply_theme(self, dark: bool) -> None:
        """Aplica la paleta clara u oscura a todos los widgets ttk."""
        self.dark_mode = bool(dark)
        p = DARK_PALETTE if self.dark_mode else LIGHT_PALETTE
        self.palette = dict(p)
        style = self.style

        self.root.configure(bg=p["bg"])
        style.configure(
            ".",
            background=p["bg"],
            foreground=p["fg"],
            fieldbackground=p["field"],
            bordercolor=p["border"],
            lightcolor=p["border"],
            darkcolor=p["border"],
            troughcolor=p["trough"],
            selectbackground=p["select_bg"],
            selectforeground=p["select_fg"],
            insertcolor=p["fg"],
            focuscolor=p["accent"],
        )
        style.configure("TFrame", background=p["bg"])
        style.configure("TLabel", background=p["bg"], foreground=p["fg"])
        style.configure(
            "TLabelframe", background=p["bg"], bordercolor=p["border"]
        )
        style.configure(
            "TLabelframe.Label", background=p["bg"], foreground=p["fg"]
        )
        style.configure(
            "TButton",
            background=p["button"],
            foreground=p["fg"],
            bordercolor=p["border"],
            padding=(8, 4),
        )
        style.map(
            "TButton",
            background=[("active", p["button_active"]), ("disabled", p["bg"])],
            foreground=[("disabled", p["muted"])],
        )
        style.configure(
            "Accent.TButton",
            background=p["accent"],
            foreground=p["accent_fg"],
            bordercolor=p["accent"],
            padding=(10, 5),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("active", p["accent_active"]),
                ("disabled", p["button"]),
            ],
            foreground=[("disabled", p["muted"])],
        )
        style.configure(
            "Filter.TMenubutton",
            background=p["field"],
            foreground=p["fg"],
            bordercolor=p["border"],
            arrowcolor=p["fg"],
            padding=(8, 4),
            relief="flat",
        )
        style.map(
            "Filter.TMenubutton",
            background=[
                ("active", p["button_active"]),
                ("pressed", p["button_active"]),
            ],
            foreground=[("active", p["fg"])],
        )
        style.configure(
            "FilterActive.TMenubutton",
            background=p["accent"],
            foreground=p["accent_fg"],
            bordercolor=p["accent"],
            arrowcolor=p["accent_fg"],
            padding=(8, 4),
            relief="flat",
        )
        style.map(
            "FilterActive.TMenubutton",
            background=[
                ("active", p["accent_active"]),
                ("pressed", p["accent_active"]),
            ],
            foreground=[("active", p["accent_fg"])],
        )
        style.configure(
            "Chip.TButton",
            background=p["field"],
            foreground=p["muted"],
            bordercolor=p["border"],
            padding=(7, 2),
            font=("Segoe UI", 8, "bold"),
        )
        style.map(
            "Chip.TButton",
            background=[
                ("active", p["button_active"]),
                ("pressed", p["button_active"]),
            ],
            foreground=[("active", p["fg"])],
        )
        style.configure(
            "ChipActive.TButton",
            background=p["accent"],
            foreground=p["accent_fg"],
            bordercolor=p["accent"],
            padding=(7, 2),
            font=("Segoe UI", 8, "bold"),
        )
        style.map(
            "ChipActive.TButton",
            background=[
                ("active", p["accent_active"]),
                ("pressed", p["accent_active"]),
            ],
            foreground=[("active", p["accent_fg"])],
        )
        for widget_style in ("TCheckbutton", "TRadiobutton"):
            style.configure(
                widget_style, background=p["bg"], foreground=p["fg"]
            )
            style.map(
                widget_style,
                background=[("active", p["bg"])],
                foreground=[("active", p["fg"])],
            )
        style.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
        style.configure(
            "TNotebook.Tab",
            background=p["tab"],
            foreground=p["muted"],
            padding=(12, 6),
            bordercolor=p["border"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", p["tab_selected"])],
            foreground=[("selected", p["fg"])],
        )
        style.configure(
            "Treeview",
            background=p["field"],
            fieldbackground=p["field"],
            foreground=p["fg"],
            bordercolor=p["border"],
            rowheight=24,
        )
        style.map(
            "Treeview",
            background=[("selected", p["select_bg"])],
            foreground=[("selected", p["select_fg"])],
        )
        style.configure(
            "Treeview.Heading",
            background=p["button"],
            foreground=p["fg"],
            bordercolor=p["border"],
            relief="flat",
        )
        style.map(
            "Treeview.Heading", background=[("active", p["button_active"])]
        )
        style.configure(
            "TEntry",
            fieldbackground=p["field"],
            foreground=p["fg"],
            bordercolor=p["border"],
            insertcolor=p["fg"],
        )
        style.map(
            "TEntry",
            fieldbackground=[("readonly", p["field"])],
            foreground=[("disabled", p["muted"])],
        )
        style.configure(
            "TCombobox",
            fieldbackground=p["field"],
            background=p["button"],
            foreground=p["fg"],
            arrowcolor=p["fg"],
            bordercolor=p["border"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", p["field"])],
            foreground=[("readonly", p["fg"])],
            selectbackground=[("readonly", p["field"])],
            selectforeground=[("readonly", p["fg"])],
        )
        style.configure(
            "TScrollbar",
            background=p["button"],
            troughcolor=p["trough"],
            bordercolor=p["border"],
            arrowcolor=p["fg"],
        )
        style.map(
            "TScrollbar", background=[("active", p["button_active"])]
        )
        style.configure(
            "TProgressbar",
            background=p["accent"],
            troughcolor=p["trough"],
            bordercolor=p["border"],
        )
        style.configure(
            "Title.TLabel",
            background=p["bg"],
            foreground=p["fg"],
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Subtitle.TLabel", background=p["bg"], foreground=p["muted"]
        )
        style.configure(
            "Team.TLabel",
            background=p["bg"],
            foreground=p["fg"],
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Small.TLabel", background=p["bg"], foreground=p["muted"]
        )

        for option, value in (
            ("background", p["field"]),
            ("foreground", p["fg"]),
            ("selectBackground", p["select_bg"]),
            ("selectForeground", p["select_fg"]),
        ):
            self.root.option_add(f"*TCombobox*Listbox.{option}", value)

        for tree in (
            self.matches_tree,
            self.team_tree,
            self.team_matches_tree,
            self.summary_tree,
            self.home_tree,
            self.away_tree,
            self.sim_validation_tree,
        ):
            tree.tag_configure("alt", background=p["alt"])
            tree.tag_configure("live", foreground=p["bad"])
            tree.tag_configure("finished", foreground=p["muted"])
            tree.tag_configure(
                "section_top",
                background=p["section_top_bg"],
                foreground=p["section_top_fg"],
                font=("Segoe UI", 9, "bold"),
            )
            tree.tag_configure(
                "section_other",
                background=p["section_other_bg"],
                foreground=p["section_other_fg"],
                font=("Segoe UI", 9, "bold"),
            )
            tree.tag_configure(
                "section_south",
                background=p["section_south_bg"],
                foreground=p["section_south_fg"],
                font=("Segoe UI", 9, "bold"),
            )

        for label, key in getattr(self, "legend_labels", []):
            try:
                label.configure(
                    background=p["bg"], foreground=p[key]
                )
            except tk.TclError:
                pass
        if hasattr(self, "empty_hint_label"):
            try:
                self.empty_hint_label.configure(
                    background=p["field"], foreground=p["muted"]
                )
            except tk.TclError:
                pass
        if hasattr(self, "auto_live_check"):
            try:
                self.auto_live_check.configure(background=p["bg"])
            except tk.TclError:
                pass
        for canvas in (
            getattr(self, "home_crest_canvas", None),
            getattr(self, "away_crest_canvas", None),
            getattr(self, "comp_flag_canvas", None),
        ):
            if canvas is not None:
                try:
                    canvas.configure(background=p["bg"])
                except tk.TclError:
                    pass
        if hasattr(self, "selected_match"):
            self._update_header_images()
            self._update_status_badge(self.selected_match)

        for chart in getattr(self, "chart_widgets", []):
            chart.set_palette(self.palette)
        if hasattr(self, "kpi_strip"):
            self.kpi_strip.set_palette(self.palette)
        if hasattr(self, "lineup_badge"):
            self._refresh_context()

        self.dark_var.set(self.dark_mode)

    def _on_theme_toggle(self) -> None:
        self._apply_theme(self.dark_var.get())
        preferences = load_preferences()
        preferences["dark"] = self.dark_mode
        preferences["theme"] = "dark" if self.dark_mode else "light"
        save_preferences(preferences)

    # ------------------------------------------------------------------
    # Panel izquierdo: selección de partido
    # ------------------------------------------------------------------
    def _build_left(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)
        self.left_notebook = notebook

        day_tab = ttk.Frame(notebook, padding=8)
        team_tab = ttk.Frame(notebook, padding=8)
        notebook.add(day_tab, text="Por fecha")
        notebook.add(team_tab, text="Por equipo")

        # --- Por fecha -------------------------------------------------
        date_row = ttk.Frame(day_tab)
        date_row.pack(fill="x", pady=(0, 6))
        ttk.Label(date_row, text="Fecha").pack(side="left")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.date_entry = ttk.Entry(date_row, textvariable=self.date_var, width=10)
        self.date_entry.pack(side="left", padx=(4, 2))
        self.date_entry.bind("<Return>", lambda _event: self.load_day())
        ttk.Button(
            date_row, text="‹", width=2, command=lambda: self._shift_date(-1)
        ).pack(side="left")
        ttk.Button(
            date_row, text="›", width=2, command=lambda: self._shift_date(1)
        ).pack(side="left")
        ttk.Button(
            date_row, text="Hoy", width=4, command=lambda: self._set_date(0)
        ).pack(side="left", padx=(6, 2))
        ttk.Button(
            date_row, text="Mañana", width=7, command=lambda: self._set_date(1)
        ).pack(side="left")

        filters = ttk.Frame(day_tab)
        filters.pack(fill="x", pady=(0, 6))
        ttk.Label(filters, text="Región").pack(side="left")
        self.region_var = tk.StringVar(value="Ambas")
        ttk.Combobox(
            filters,
            textvariable=self.region_var,
            values=list(REGION_LABELS),
            state="readonly",
            width=11,
        ).pack(side="left", padx=(4, 10))
        ttk.Label(filters, text="Alcance").pack(side="left")
        self.competition_var = tk.StringVar(value="Todas")
        ttk.Combobox(
            filters,
            textvariable=self.competition_var,
            values=list(COMPETITION_LABELS),
            state="readonly",
            width=11,
        ).pack(side="left", padx=4)

        self.load_btn = ttk.Button(
            day_tab,
            text="Cargar partidos",
            style="Accent.TButton",
            command=self.load_day,
        )
        self.load_btn.pack(fill="x", pady=(0, 6))

        league_row = ttk.Frame(day_tab)
        league_row.pack(fill="x", pady=(0, 4))
        ttk.Label(league_row, text="Liga").pack(side="left")
        self.league_btn = ttk.Menubutton(
            league_row,
            textvariable=self.league_label_var,
            style="Filter.TMenubutton",
        )
        self.league_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.league_menu = tk.Menu(self.league_btn, tearoff=False)
        self.league_btn.configure(menu=self.league_menu)
        self._bind_tooltip(
            self.league_btn,
            "Filtra por competición: primero las cinco grandes y después el resto.",
        )
        self._rebuild_league_menu()

        self.matches_count_var = tk.StringVar(value="Sin partidos cargados.")
        self.matches_count_label = ttk.Label(
            day_tab,
            textvariable=self.matches_count_var,
            style="Small.TLabel",
            wraplength=330,
            justify="left",
        )
        self.matches_count_label.pack(anchor="w", pady=(0, 2))

        legend = ttk.Frame(day_tab)
        legend.pack(fill="x", pady=(0, 2))
        for text, color_key in (
            ("★ Top 5", "section_top_fg"),
            ("◆ Otras", "section_other_fg"),
            ("● Sudamérica", "section_south_fg"),
        ):
            label = tk.Label(
                legend,
                text=text,
                background=self.palette["bg"],
                foreground=self.palette[color_key],
                font=("Segoe UI", 8, "bold"),
            )
            label.pack(side="left", padx=(0, 10))
            self.legend_labels.append((label, color_key))
        self.auto_live_check = ttk.Checkbutton(
            legend,
            text="Auto en vivo",
            variable=self.auto_live_var,
            command=self._on_auto_live_toggle,
        )
        self.auto_live_check.pack(side="right")
        self._bind_tooltip(
            self.auto_live_check,
            "Actualiza marcadores y minutos cada 45 segundos.",
        )

        chips = ttk.Frame(day_tab)
        chips.pack(fill="x", pady=(0, 4))
        for key, label in (
            ("all", "Todo"),
            ("live", "Vivo"),
            ("upcoming", "Próx."),
            ("finished", "Final"),
            ("favorites", "★ Favs"),
        ):
            button = ttk.Button(
                chips,
                text=label,
                width=6,
                style="Chip.TButton",
                command=lambda chip=key: self._on_status_chip(chip),
            )
            button.pack(side="left", padx=(0, 4))
            self._status_chip_buttons[key] = button
        self._update_status_chips()

        filter_row = ttk.Frame(day_tab)
        filter_row.pack(fill="x", pady=(0, 4))
        ttk.Label(filter_row, text="Filtrar").pack(side="left")
        self.match_filter_var = tk.StringVar()
        self.match_filter_entry = ttk.Entry(
            filter_row, textvariable=self.match_filter_var
        )
        self.match_filter_entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
        self.match_filter_entry.bind("<Escape>", lambda _event: self.match_filter_var.set(""))
        self.filter_clear_btn = ttk.Button(
            filter_row,
            text="×",
            width=2,
            style="Chip.TButton",
            command=self._clear_filter,
        )
        self.filter_clear_btn.pack(side="right")
        self._bind_tooltip(
            self.filter_clear_btn, "Limpiar todos los filtros (Esc)"
        )
        self.match_filter_var.trace_add(
            "write", lambda *_args: self._render_matches()
        )

        match_frame = ttk.Frame(day_tab)
        match_frame.pack(fill="both", expand=True)
        self.matches_tree = self._make_tree(
            match_frame,
            columns=("hora", "competicion", "local", "visitante", "marcador", "alineacion"),
            headings=(
                "Hora",
                "Competición",
                "Local",
                "Visitante",
                "Marcador",
                "Alineación",
            ),
            widths=(44, 112, 78, 78, 56, 64),
            height=18,
            horizontal=False,
            row_icons=True,
        )
        self.matches_tree.bind("<<TreeviewSelect>>", self._on_match_select)
        self.matches_tree.bind(
            "<Configure>", lambda event: self._fit_match_columns(event.widget), add="+"
        )
        self.matches_tree.bind("<Motion>", self._on_match_motion)
        self.matches_tree.bind("<Leave>", lambda _event: self._hide_tooltip())
        self.matches_tree.bind("<Button-1>", lambda _event: self._hide_tooltip())
        self.matches_tree.bind("<MouseWheel>", lambda _event: self._hide_tooltip())
        self.empty_hint_var = tk.StringVar()
        self.empty_hint_label = tk.Label(
            match_frame,
            textvariable=self.empty_hint_var,
            background=self.palette["field"],
            foreground=self.palette["muted"],
            font=("Segoe UI", 9),
            justify="center",
            wraplength=250,
            padx=10,
            pady=8,
        )

        # --- Por equipo ------------------------------------------------
        search_row = ttk.Frame(team_tab)
        search_row.pack(fill="x", pady=(0, 6))
        ttk.Label(search_row, text="Equipo").pack(side="left")
        self.team_query_var = tk.StringVar()
        self.team_entry = ttk.Entry(search_row, textvariable=self.team_query_var)
        self.team_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.team_entry.bind("<Return>", lambda _event: self.search_team())
        self.search_btn = ttk.Button(
            search_row, text="Buscar", command=self.search_team
        )
        self.search_btn.pack(side="left")

        ttk.Label(
            team_tab, text="Resultados de equipos", style="Small.TLabel"
        ).pack(anchor="w", pady=(2, 2))
        results_frame = ttk.Frame(team_tab)
        results_frame.pack(fill="x", pady=(0, 6))
        self.team_tree = self._make_tree(
            results_frame,
            columns=("equipo", "pais", "id"),
            headings=("Equipo", "País", "ID"),
            widths=(150, 90, 50),
            height=5,
            horizontal=False,
        )
        self.team_tree.bind("<<TreeviewSelect>>", self._on_team_select)

        self.team_view_btn = ttk.Button(
            team_tab,
            text="Ver partidos del equipo",
            command=self.view_team_matches,
            state="disabled",
        )
        self.team_view_btn.pack(fill="x", pady=(0, 6))

        ttk.Label(
            team_tab, text="Partidos del equipo", style="Small.TLabel"
        ).pack(anchor="w", pady=(2, 2))
        team_matches_frame = ttk.Frame(team_tab)
        team_matches_frame.pack(fill="both", expand=True)
        self.team_matches_tree = self._make_tree(
            team_matches_frame,
            columns=("hora", "competicion", "local", "visitante", "marcador", "alineacion"),
            headings=(
                "Hora",
                "Competición",
                "Local",
                "Visitante",
                "Marcador",
                "Alineación",
            ),
            widths=(44, 112, 78, 78, 56, 64),
            height=12,
            horizontal=False,
            row_icons=True,
        )
        self.team_matches_tree.bind(
            "<Configure>", lambda event: self._fit_match_columns(event.widget), add="+"
        )
        self.team_matches_tree.bind("<Motion>", self._on_match_motion)
        self.team_matches_tree.bind("<Leave>", lambda _event: self._hide_tooltip())
        self.team_matches_tree.bind("<Button-1>", lambda _event: self._hide_tooltip())
        self.team_matches_tree.bind("<MouseWheel>", lambda _event: self._hide_tooltip())
        self.team_matches_tree.bind("<<TreeviewSelect>>", self._on_match_select)

    # ------------------------------------------------------------------
    # Panel derecho: análisis
    # ------------------------------------------------------------------
    def _build_right(self, parent: ttk.Frame) -> None:
        title_row = ttk.Frame(parent)
        title_row.pack(fill="x")
        self.home_crest_canvas = tk.Canvas(
            title_row,
            width=32,
            height=32,
            highlightthickness=0,
            bd=0,
            background=self.palette["bg"],
        )
        self.home_crest_canvas.pack(side="left")
        self.match_title_var = tk.StringVar(
            value="Selecciona un partido de la lista"
        )
        self.match_title_label = ttk.Label(
            title_row,
            textvariable=self.match_title_var,
            style="Team.TLabel",
            wraplength=660,
            justify="left",
        )
        self.match_title_label.pack(side="left", padx=(8, 8))
        self.away_crest_canvas = tk.Canvas(
            title_row,
            width=32,
            height=32,
            highlightthickness=0,
            bd=0,
            background=self.palette["bg"],
        )
        self.away_crest_canvas.pack(side="left")

        subtitle_row = ttk.Frame(parent)
        subtitle_row.pack(fill="x", pady=(2, 4))
        self.comp_flag_canvas = tk.Canvas(
            subtitle_row,
            width=22,
            height=16,
            highlightthickness=0,
            bd=0,
            background=self.palette["bg"],
        )
        self.comp_flag_canvas.pack(side="left", padx=(0, 6))
        self.match_subtitle_var = tk.StringVar(
            value="Los datos se obtienen de la API interna de SofaScore."
        )
        self.match_subtitle_label = ttk.Label(
            subtitle_row,
            textvariable=self.match_subtitle_var,
            style="Small.TLabel",
            wraplength=700,
            justify="left",
        )
        self.match_subtitle_label.pack(side="left", fill="x", expand=True)
        self.status_badge = tk.Label(
            subtitle_row,
            text="—",
            background=self.palette["muted"],
            foreground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
        )
        self.status_badge.pack(side="right", padx=(8, 0))

        context_row = ttk.Frame(parent)
        context_row.pack(fill="x", pady=(0, 6))
        self.lineup_badge = tk.Label(
            context_row,
            text="Alineación: —",
            background=self.palette["muted"],
            foreground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
        )
        self.lineup_badge.pack(side="left")
        self.referee_var = tk.StringVar(value="Árbitro: —")
        ttk.Label(
            context_row, textvariable=self.referee_var, style="Small.TLabel"
        ).pack(side="left", padx=(10, 0))
        self.fav_btn = ttk.Menubutton(
            context_row,
            text="☆ Favoritos",
            style="Filter.TMenubutton",
        )
        self.fav_btn.pack(side="right")
        self.fav_menu = tk.Menu(self.fav_btn, tearoff=False)
        self.fav_btn.configure(menu=self.fav_menu)
        self._bind_tooltip(
            self.fav_btn,
            "Marca equipos como favoritos para filtrarlos y recibir alertas.",
        )
        self._refresh_favorite_menu()

        controls = ttk.LabelFrame(parent, text="Ventana de análisis", padding=8)
        controls.pack(fill="x")
        self.window_var = tk.StringVar(value="10")
        for label, value in WINDOW_OPTIONS:
            ttk.Radiobutton(
                controls,
                text=label,
                value=value,
                variable=self.window_var,
            ).pack(side="left", padx=(0, 10))
        self.analyze_btn = ttk.Button(
            controls,
            text="Analizar partido",
            style="Accent.TButton",
            command=self.analyze,
            state="disabled",
        )
        self.analyze_btn.pack(side="right", padx=(8, 0))

        export_bar = ttk.Frame(parent)
        export_bar.pack(fill="x", pady=(6, 4))
        self.export_csv_btn = ttk.Button(
            export_bar,
            text="Exportar CSV",
            command=self.export_csv,
            state="disabled",
        )
        self.export_csv_btn.pack(side="right", padx=(6, 0))
        self.export_json_btn = ttk.Button(
            export_bar,
            text="Exportar JSON",
            command=self.export_json,
            state="disabled",
        )
        self.export_json_btn.pack(side="right")
        self.preview_btn = ttk.Button(
            export_bar,
            text="Previa",
            command=self.open_preview_studio,
            state="disabled",
        )
        self.preview_btn.pack(side="right", padx=(0, 6))

        self.result_notebook = ttk.Notebook(parent)
        self.result_notebook.pack(fill="both", expand=True, pady=(4, 0))

        summary_tab = ttk.Frame(self.result_notebook, padding=6)
        self.result_notebook.add(summary_tab, text="Resumen")
        self.summary_caption = tk.StringVar(
            value="Selecciona un partido y pulsa «Analizar partido»."
        )
        ttk.Label(
            summary_tab,
            textvariable=self.summary_caption,
            style="Small.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        summary_frame = ttk.Frame(summary_tab)
        summary_frame.pack(fill="both", expand=True)
        self.summary_tree = self._make_tree(
            summary_frame,
            columns=("stat", "home", "home_split", "away", "away_split", "diff"),
            headings=(
                "Estadística",
                "Local (media)",
                "Local (en casa)",
                "Visitante (media)",
                "Visitante (fuera)",
                "Diferencia",
            ),
            widths=(155, 117, 117, 117, 117, 65),
            height=14,
            horizontal=False,
        )

        home_tab = ttk.Frame(self.result_notebook, padding=6)
        self.result_notebook.add(home_tab, text="Local")
        self.home_caption = tk.StringVar(value="Sin análisis.")
        ttk.Label(
            home_tab,
            textvariable=self.home_caption,
            style="Small.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        home_frame = ttk.Frame(home_tab)
        home_frame.pack(fill="both", expand=True)
        self.home_tree = self._make_match_tree(home_frame)

        away_tab = ttk.Frame(self.result_notebook, padding=6)
        self.result_notebook.add(away_tab, text="Visitante")
        self.away_caption = tk.StringVar(value="Sin análisis.")
        ttk.Label(
            away_tab,
            textvariable=self.away_caption,
            style="Small.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        away_frame = ttk.Frame(away_tab)
        away_frame.pack(fill="both", expand=True)
        self.away_tree = self._make_match_tree(away_frame)

        self.simulation_tab = ttk.Frame(self.result_notebook, padding=4)
        self.result_notebook.add(self.simulation_tab, text="Simulación")
        self._build_simulation_tab(self.simulation_tab)

    def _build_simulation_tab(self, parent: ttk.Frame) -> None:
        """Panel de simulación Monte Carlo: controles, KPI y gráficos."""
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(2, 4))
        ttk.Label(controls, text="Simulaciones:").pack(side="left")
        self.sim_iterations_var = tk.StringVar(
            value=str(simulation.DEFAULT_ITERATIONS)
        )
        self.sim_iterations_combo = ttk.Combobox(
            controls,
            textvariable=self.sim_iterations_var,
            values=SIM_ITERATION_VALUES,
            width=9,
        )
        self.sim_iterations_combo.pack(side="left", padx=(4, 12))
        ttk.Label(controls, text="Semilla:").pack(side="left")
        self.sim_seed_var = tk.StringVar(value="42")
        self.sim_seed_entry = ttk.Entry(
            controls, textvariable=self.sim_seed_var, width=7
        )
        self.sim_seed_entry.pack(side="left", padx=(4, 12))
        self.simulate_btn = ttk.Button(
            controls,
            text="Simular partido",
            style="Accent.TButton",
            command=self.run_simulation,
            state="disabled",
        )
        self.simulate_btn.pack(side="right")
        self.clear_cache_btn = ttk.Button(
            controls,
            text="Vaciar caché",
            command=self.clear_simulation_cache,
        )
        self.clear_cache_btn.pack(side="right", padx=(0, 6))
        self._update_cache_button()

        info_row = ttk.Frame(parent)
        info_row.pack(fill="x", pady=(0, 6))
        ttk.Label(
            info_row,
            text="Monte Carlo con NumPy · probabilidades, no una predicción",
            style="Small.TLabel",
        ).pack(side="left")
        self.sim_json_btn = ttk.Button(
            info_row,
            text="JSON",
            width=7,
            command=self.export_simulation_json,
            state="disabled",
        )
        self.sim_json_btn.pack(side="right")
        self.sim_csv_btn = ttk.Button(
            info_row,
            text="CSV",
            width=7,
            command=self.export_simulation_csv,
            state="disabled",
        )
        self.sim_csv_btn.pack(side="right", padx=(0, 4))
        ttk.Label(info_row, text="Exportar:", style="Small.TLabel").pack(
            side="right", padx=(0, 4)
        )

        self.sim_context_var = tk.StringVar(
            value="Contexto: analiza un partido para consultar alineaciones y árbitro."
        )
        ttk.Label(
            parent,
            textvariable=self.sim_context_var,
            style="Small.TLabel",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(0, 4))

        self.kpi_strip = charts.KpiStrip(parent, self.palette, columns=5)
        self.kpi_strip.pack(fill="x", pady=(0, 6))
        self.kpi_strip.set_cards(
            [
                {
                    "title": "GOLES",
                    "value": "—",
                    "subtitle": "esperados",
                    "color": self.palette["accent"],
                },
                {
                    "title": "RESULTADO",
                    "value": "—",
                    "subtitle": "más probable",
                    "color": self.palette["home"],
                },
                {
                    "title": "AMBOS MARCAN",
                    "value": "—",
                    "subtitle": "sí / no",
                    "color": self.palette["good"],
                },
                {
                    "title": "OVER 2,5",
                    "value": "—",
                    "subtitle": "goles",
                    "color": self.palette["warn"],
                },
                {
                    "title": "CÓRNERS",
                    "value": "—",
                    "subtitle": "esperados",
                    "color": self.palette["accent2"],
                },
            ]
        )

        self.sim_notebook = ttk.Notebook(parent)
        self.sim_notebook.pack(fill="both", expand=True)

        panorama = ttk.Frame(self.sim_notebook, padding=4)
        self.sim_notebook.add(panorama, text="Panorama")
        panorama.columnconfigure(0, weight=3)
        panorama.columnconfigure(1, weight=2)
        panorama.rowconfigure(0, weight=1)
        self.sim_compare_chart = charts.GroupedBarChart(
            panorama, palette=self.palette, height=260
        )
        self.sim_compare_chart.empty_text = (
            "Ejecuta la simulación para comparar ambos equipos."
        )
        self.sim_compare_chart.grid(
            row=0, column=0, sticky="nsew", padx=(0, 6)
        )
        self.panorama_scroller = charts.ScrollableColumn(panorama, self.palette)
        self.panorama_scroller.grid(row=0, column=1, sticky="nsew")
        right = self.panorama_scroller.content
        right.columnconfigure(0, weight=1)
        self.sim_donut_chart = charts.DonutChart(
            right, palette=self.palette, height=140
        )
        self.sim_donut_chart.empty_text = "Probabilidades 1X2."
        self.sim_donut_chart.grid(row=0, column=0, sticky="ew")
        self.sim_scores_chart = charts.HorizontalBarChart(
            right, palette=self.palette, height=150
        )
        self.sim_scores_chart.empty_text = "Marcadores más probables."
        self.sim_scores_chart.grid(
            row=1, column=0, sticky="ew", pady=(6, 0)
        )
        self.panorama_scroller.bind_wheel(self.sim_donut_chart)
        self.panorama_scroller.bind_wheel(self.sim_scores_chart)

        distributions = ttk.Frame(self.sim_notebook, padding=4)
        self.sim_notebook.add(distributions, text="Distribuciones")
        distributions.columnconfigure(0, weight=1)
        distributions.rowconfigure(1, weight=1)
        hist_row = ttk.Frame(distributions)
        hist_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(hist_row, text="Distribución:").pack(side="left")
        self.sim_hist_var = tk.StringVar(value=SIM_HISTOGRAM_OPTIONS[0][0])
        self.sim_hist_combo = ttk.Combobox(
            hist_row,
            textvariable=self.sim_hist_var,
            values=[option[0] for option in SIM_HISTOGRAM_OPTIONS],
            state="readonly",
            width=24,
        )
        self.sim_hist_combo.pack(side="left", padx=(4, 0))
        self.sim_hist_combo.bind(
            "<<ComboboxSelected>>", self._on_sim_histogram_change
        )
        self.sim_hist_chart = charts.HistogramChart(
            distributions, palette=self.palette, height=260
        )
        self.sim_hist_chart.empty_text = (
            "Las distribuciones aparecerán tras la simulación."
        )
        self.sim_hist_chart.grid(row=1, column=0, sticky="nsew")
        self.sim_hist_caption = tk.StringVar(
            value="Media, mediana y rango P10–P90 de la métrica elegida."
        )
        ttk.Label(
            distributions,
            textvariable=self.sim_hist_caption,
            style="Small.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        markets = ttk.Frame(self.sim_notebook, padding=4)
        self.sim_notebook.add(markets, text="Mercados")
        markets.columnconfigure(0, weight=3)
        markets.columnconfigure(1, weight=2)
        markets.rowconfigure(1, weight=1)
        market_row = ttk.Frame(markets)
        market_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(market_row, text="Mercado:").pack(side="left")
        self.sim_market_var = tk.StringVar(value=SIM_MARKET_OPTIONS[0][0])
        self.sim_market_combo = ttk.Combobox(
            market_row,
            textvariable=self.sim_market_var,
            values=[option[0] for option in SIM_MARKET_OPTIONS],
            state="readonly",
            width=24,
        )
        self.sim_market_combo.pack(side="left", padx=(4, 0))
        self.sim_market_combo.bind(
            "<<ComboboxSelected>>", self._on_sim_market_change
        )
        self.sim_market_chart = charts.HorizontalBarChart(
            markets, palette=self.palette, height=240
        )
        self.sim_market_chart.empty_text = "Probabilidades over/under."
        self.sim_market_chart.grid(
            row=1, column=0, sticky="nsew", padx=(0, 6)
        )
        self.sim_heatmap = charts.HeatmapChart(
            markets, palette=self.palette, height=240
        )
        self.sim_heatmap.empty_text = "Matriz de marcadores."
        self.sim_heatmap.grid(row=1, column=1, sticky="nsew")

        self.sim_validation_tab = ttk.Frame(self.sim_notebook, padding=4)
        self.sim_notebook.add(self.sim_validation_tab, text="Validación")
        self.sim_validation_tab.columnconfigure(0, weight=3)
        self.sim_validation_tab.columnconfigure(1, weight=3)
        self.sim_validation_tab.rowconfigure(1, weight=1)
        self.sim_validation_caption = tk.StringVar(
            value="Disponible para partidos finalizados."
        )
        ttk.Label(
            self.sim_validation_tab,
            textvariable=self.sim_validation_caption,
            style="Small.TLabel",
            wraplength=780,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.sim_validation_chart = charts.GroupedBarChart(
            self.sim_validation_tab, palette=self.palette, height=240
        )
        self.sim_validation_chart.empty_text = (
            "Ejecuta la simulación de un partido finalizado para comparar."
        )
        self.sim_validation_chart.grid(
            row=1, column=0, sticky="nsew", padx=(0, 6)
        )
        validation_tree_frame = ttk.Frame(self.sim_validation_tab)
        validation_tree_frame.grid(row=1, column=1, sticky="nsew")
        self.sim_validation_tree = self._make_tree(
            validation_tree_frame,
            columns=("metrica", "real", "simulado", "error", "rango", "dentro"),
            headings=(
                "Métrica",
                "Actual",
                "Esperado",
                "Error",
                "Rango",
                "Dentro",
            ),
            widths=(90, 42, 58, 44, 64, 44),
            height=8,
            horizontal=False,
        )

        self.chart_widgets = [
            self.sim_compare_chart,
            self.panorama_scroller,
            self.sim_donut_chart,
            self.sim_scores_chart,
            self.sim_hist_chart,
            self.sim_market_chart,
            self.sim_heatmap,
            self.sim_validation_chart,
        ]

    def _make_tree(
        self,
        parent: ttk.Frame,
        columns: tuple,
        headings: tuple,
        widths: tuple,
        height: int = 10,
        horizontal: bool = True,
        row_icons: bool = False,
    ) -> ttk.Treeview:
        tree = ttk.Treeview(
            parent,
            columns=columns,
            show=("tree", "headings") if row_icons else "headings",
            selectmode="browse",
            height=height,
        )
        if row_icons:
            tree.heading("#0", text="Esc.")
            tree.column("#0", width=30, minwidth=20, stretch=False, anchor="center")
            tree._row_icons = True  # type: ignore[attr-defined]
            tree._icons_visible = True  # type: ignore[attr-defined]
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=max(40, width // 2), anchor="w")
        tree.tag_configure("alt", background=self.palette["alt"])
        tree.tag_configure(
            "section_top",
            background=self.palette["section_top_bg"],
            foreground=self.palette["section_top_fg"],
            font=("Segoe UI", 9, "bold"),
        )
        tree.tag_configure(
            "section_other",
            background=self.palette["section_other_bg"],
            foreground=self.palette["section_other_fg"],
            font=("Segoe UI", 9, "bold"),
        )
        tree.tag_configure(
            "section_south",
            background=self.palette["section_south_bg"],
            foreground=self.palette["section_south_fg"],
            font=("Segoe UI", 9, "bold"),
        )
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        if horizontal:
            xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
            tree.configure(xscrollcommand=xscroll.set)
            xscroll.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return tree

    def _make_match_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        return self._make_tree(
            parent,
            columns=(
                "fecha",
                "competicion",
                "condicion",
                "rival",
                "resultado",
                "goles",
                "corners",
                "tarjetas",
                "remates",
                "arco",
                "faltas",
                "paradas",
            ),
            headings=(
                "Fecha",
                "Competición",
                "Cond.",
                "Rival",
                "Resultado",
                "Goles",
                "Córners",
                "Tarjetas",
                "Remates",
                "Al arco",
                "Faltas",
                "Paradas",
            ),
            widths=(72, 135, 52, 115, 72, 55, 60, 62, 64, 60, 55, 60),
            height=16,
        )

    def _fit_match_columns(self, tree: ttk.Treeview) -> None:
        """Reparte el ancho disponible entre las columnas del listado de partidos."""
        try:
            if not tree.winfo_exists():
                return
        except tk.TclError:
            return
        available = tree.winfo_width() - 4
        if available < 120:
            return
        if getattr(tree, "_row_icons", False):
            show_icons = available - 30 >= 316
            if show_icons != getattr(tree, "_icons_visible", True):
                tree._icons_visible = show_icons  # type: ignore[attr-defined]
                tree.configure(
                    show=("tree", "headings") if show_icons else "headings"
                )
                if show_icons:
                    self._sync_row_icons(tree)
            if show_icons:
                available -= 30
        minimums = (37, 60, 55, 55, 43, 66)
        preferred = (44, 100, 72, 72, 64, 68)
        minimum_total = sum(minimums)
        preferred_total = sum(preferred)
        if available < minimum_total:
            widths = list(minimums)
        elif available <= preferred_total:
            ratio = (available - minimum_total) / (preferred_total - minimum_total)
            widths = [
                round(low + (high - low) * ratio)
                for low, high in zip(minimums, preferred)
            ]
        else:
            widths = list(preferred)
            extra = available - preferred_total
            bonus = (round(extra * 0.5), round(extra * 0.25))
            widths[1] += bonus[0]
            widths[2] += bonus[1]
            widths[3] += extra - bonus[0] - bonus[1]
        if available >= minimum_total:
            widths[-1] += available - sum(widths)
        for column, width in zip(tree["columns"], widths):
            try:
                if int(tree.column(column, "width")) != width:
                    tree.column(
                        column,
                        width=width,
                        minwidth=min(24, width),
                        stretch=False,
                    )
            except (tk.TclError, ValueError):
                continue
        heading_labels = {
            "competicion": ("Competición", "Comp.", 78),
            "marcador": ("Marcador", "Marc.", 63),
            "alineacion": ("Alineación", "Alineac.", 65),
        }
        for column, width in zip(tree["columns"], widths):
            labels = heading_labels.get(column)
            if not labels:
                continue
            text = labels[0] if width >= labels[2] else labels[1]
            try:
                if tree.heading(column, "text") != text:
                    tree.heading(column, text=text)
            except tk.TclError:
                continue
        self._update_section_rows(tree)

    # ------------------------------------------------------------------
    # Cola de mensajes entre hilos y UI
    # ------------------------------------------------------------------
    def _post(self, function, *args) -> None:
        self.queue.put((function, args))

    def _drain_queue(self) -> None:
        try:
            for _ in range(100):
                function, args = self.queue.get_nowait()
                try:
                    function(*args)
                except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                    self._show_error(exc)
        except queue.Empty:
            pass
        try:
            self._drain_job = self.root.after(100, self._drain_queue)
        except tk.TclError:
            self._drain_job = None

    def _progress_cb(self, done: int, total: int, message: str) -> None:
        self._post(self._update_progress, done, total, message)

    def _update_progress(self, done: int, total: int, message: str) -> None:
        self.status_var.set(message)
        if total and total > 0:
            self.progress.configure(maximum=total, value=done)
        else:
            self.progress.configure(maximum=1, value=0)

    def _set_busy(self, busy: bool) -> None:
        self.busy = bool(busy)
        state = "disabled" if busy else "normal"
        for button in (self.load_btn, self.search_btn, self.league_btn):
            button.configure(state=state)
        self.team_view_btn.configure(
            state="normal" if (not busy and self._selected_team_id()) else "disabled"
        )
        self.analyze_btn.configure(
            state="normal" if (not busy and self.selected_match) else "disabled"
        )
        has_analysis = self.analysis is not None
        export_state = "normal" if (not busy and has_analysis) else "disabled"
        self.export_csv_btn.configure(state=export_state)
        self.export_json_btn.configure(state=export_state)
        self.preview_btn.configure(state=export_state)
        self.simulate_btn.configure(state=export_state)
        self.sim_iterations_combo.configure(
            state="disabled" if busy else "normal"
        )
        self.sim_seed_entry.configure(state="disabled" if busy else "normal")
        self.clear_cache_btn.configure(
            state="disabled" if busy else "normal"
        )
        sim_export_state = (
            "normal" if (not busy and self.simulation_summary) else "disabled"
        )
        self.sim_csv_btn.configure(state=sim_export_state)
        self.sim_json_btn.configure(state=sim_export_state)
        try:
            self.root.configure(cursor="watch" if busy else "")
        except tk.TclError:
            pass
        if not busy:
            pending = self.pending_context_match
            self.pending_context_match = None
            if (
                pending
                and self.selected_match
                and pending.get("id") == self.selected_match.get("id")
                and pending.get("id") not in self.context_cache
            ):
                self.root.after(
                    80, lambda match=pending: self._load_match_context(match)
                )

    def _show_error(self, exc: BaseException) -> None:
        self.status_var.set("Error.")
        self.progress.stop()
        self.progress.configure(mode="determinate", maximum=1, value=0)
        messagebox.showerror("Error", str(exc), parent=self.root)

    def _on_day_error(self, exc: BaseException) -> None:
        self.loading_rest = False
        self.matches_base_text = "No se pudieron cargar los partidos."
        self.matches_count_var.set(self.matches_base_text)
        self._rebuild_league_menu()
        self._show_error(exc)
        self._set_busy(False)

    def _tz_name(self) -> str:
        return self.tz_var.get() or "local"

    # ------------------------------------------------------------------
    # Fechas y selección
    # ------------------------------------------------------------------
    def _set_date(self, offset: int) -> None:
        if self.busy:
            return
        self.date_var.set((date.today() + timedelta(days=offset)).isoformat())
        self.load_day()

    def _shift_date(self, days: int) -> None:
        if self.busy:
            return
        try:
            base = date.fromisoformat(parse_day(self.date_var.get()))
        except Exception:
            base = date.today()
        self.date_var.set((base + timedelta(days=days)).isoformat())
        self.load_day()

    def _clear_analysis_state(self) -> None:
        """Limpia el análisis anterior al cambiar de partido o de lista."""
        self.analysis = None
        self.simulation_summary = None
        if hasattr(self, "summary_tree"):
            self.summary_tree.delete(*self.summary_tree.get_children())
            for column, text in (
                ("home", "Local (media)"),
                ("home_split", "Local (en casa)"),
                ("away", "Visitante (media)"),
                ("away_split", "Visitante (fuera)"),
            ):
                self.summary_tree.heading(column, text=text)
        if hasattr(self, "home_tree"):
            self.home_tree.delete(*self.home_tree.get_children())
        if hasattr(self, "away_tree"):
            self.away_tree.delete(*self.away_tree.get_children())
        if hasattr(self, "summary_caption"):
            self.summary_caption.set(
                "Selecciona un partido y pulsa «Analizar partido»."
            )
        if hasattr(self, "home_caption"):
            self.home_caption.set("Sin análisis.")
        if hasattr(self, "away_caption"):
            self.away_caption.set("Sin análisis.")
        if hasattr(self, "sim_context_var"):
            self._reset_simulation()
        if hasattr(self, "result_notebook"):
            self.result_notebook.select(0)

    def _on_timezone_change(self, _event=None) -> None:
        if self.busy:
            return
        try:
            active_tab = self.left_notebook.index(self.left_notebook.select())
        except tk.TclError:
            active_tab = 0
        if (
            active_tab == 1
            and self.team_matches
            and self._selected_team_id() is not None
        ):
            self.view_team_matches()
        elif self.matches:
            self.load_day()
        elif self.analysis:
            self._apply_analysis(self.analysis)

    # ------------------------------------------------------------------
    # Carga de próximos partidos
    # ------------------------------------------------------------------
    def load_day(self) -> None:
        if self.busy:
            return
        try:
            day = parse_day(self.date_var.get().strip() or "hoy")
        except SofaScoreError as exc:
            messagebox.showerror("Fecha no válida", str(exc), parent=self.root)
            return

        self.date_var.set(day)
        if self.match_filter_var.get():
            self.match_filter_var.set("")
        self._reset_league_filter()
        self._reset_status_filters()
        self.loading_rest = False
        self.day_load_token += 1
        token = self.day_load_token
        region = REGION_LABELS.get(self.region_var.get(), "ambas")
        competitions = COMPETITION_LABELS.get(
            self.competition_var.get(), "principales"
        )
        timezone_name = self._tz_name()

        self.matches = []
        self.selected_match = None
        self._populate_matches(self.matches_tree, [])
        self._clear_analysis_state()
        self._update_match_header()
        self.matches_base_text = "Cargando partidos…"
        self.matches_count_var.set(self.matches_base_text)
        self._set_busy(True)
        self.progress.configure(maximum=1, value=0)
        self.status_var.set(f"Buscando partidos del {day}…")

        if competitions == "todas":

            def work_progressive() -> None:
                try:
                    initial = upcoming.list_upcoming(
                        self.extractor,
                        day,
                        region=region,
                        competitions=competitions,
                        limit=500,
                        timezone_name=timezone_name,
                        progress=self._progress_cb,
                        include_finished=True,
                        include_live=True,
                        tournament_filter=self._initial_tournament,
                    )
                except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                    self._post(self._on_day_error, exc)
                    return
                self._post(self._apply_initial_day, initial, day, token)
                try:
                    rest = upcoming.list_upcoming(
                        self.extractor,
                        day,
                        region=region,
                        competitions=competitions,
                        limit=500,
                        timezone_name=timezone_name,
                        progress=self._progress_cb,
                        include_finished=True,
                        include_live=True,
                        tournament_filter=self._remaining_tournament,
                    )
                except Exception as exc:  # noqa: BLE001 - no interrumpir
                    self._post(self._on_rest_error, exc, token)
                    return
                self._post(self._apply_rest_day, rest, day, token)

            threading.Thread(target=work_progressive, daemon=True).start()
            return

        def work() -> None:
            try:
                matches = upcoming.list_upcoming(
                    self.extractor,
                    day,
                    region=region,
                    competitions=competitions,
                    limit=500,
                    timezone_name=timezone_name,
                    progress=self._progress_cb,
                    include_finished=True,
                    include_live=True,
                )
                self._post(self._apply_matches, matches, day)
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                self._post(self._on_day_error, exc)
            finally:
                self._post(self._set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def _initial_tournament(self, entry: Dict[str, Any]) -> bool:
        try:
            tournament_id = int(entry.get("unique_tournament_id"))
        except (TypeError, ValueError):
            tournament_id = None
        return (
            tournament_id in TOP_LEAGUE_IDS
            or regions.normalize_region(entry.get("region")) == "sudamerica"
        )

    def _remaining_tournament(self, entry: Dict[str, Any]) -> bool:
        return not self._initial_tournament(entry)

    def _apply_initial_day(
        self, matches: List[Dict[str, Any]], day: str, token: int
    ) -> None:
        if token != self.day_load_token:
            return
        self.loading_rest = True
        self._apply_matches(matches, day, partial=True)

    def _apply_rest_day(
        self, matches: List[Dict[str, Any]], day: str, token: int
    ) -> None:
        if token != self.day_load_token:
            return
        self.loading_rest = False
        self._apply_matches(
            self._merge_matches(self.matches, matches), day, reset_state=False
        )

    def _merge_matches(
        self,
        existing: List[Dict[str, Any]],
        extra: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged = {match.get("id"): match for match in existing}
        for match in extra:
            merged.setdefault(match.get("id"), match)
        return [match for match in merged.values() if match.get("id") is not None]

    def _on_rest_error(self, _exc: BaseException, token: int) -> None:
        if token != self.day_load_token:
            return
        self.loading_rest = False
        self.progress.configure(maximum=1, value=1)
        self.status_var.set(
            f"Se muestran {len(self.matches)} partidos. No se pudo cargar "
            "el resto de competiciones; puedes volver a intentarlo."
        )
        self._render_matches()

    def _apply_matches(
        self,
        matches: List[Dict[str, Any]],
        day: str,
        reset_state: bool = True,
        partial: bool = False,
    ) -> None:
        self.matches = matches
        self.current_day = day
        self._save_matches_history(matches, day)
        if reset_state:
            self.context_cache.clear()
            self.context_token += 1
            self._show_match_context(None, None)
            self._clear_analysis_state()
        self._rebuild_league_menu()
        self._remember_scores(matches)
        if matches:
            live = sum(
                1
                for match in matches
                if match.get("status_type") in ("inprogress", "live", "halftime")
            )
            finished = sum(
                1 for match in matches if match.get("status_type") == "finished"
            )
            upcoming_count = len(matches) - live - finished
            self.matches_base_text = (
                f"{_plural(len(matches), 'partido', 'partidos')} · {live} en vivo · "
                f"{_plural(upcoming_count, 'próximo', 'próximos')} · "
                f"{_plural(finished, 'finalizado', 'finalizados')}"
            )
            if partial:
                self.matches_base_text += " · cargando resto…"
                self.status_var.set(
                    f"Mostrando {_plural(len(matches), 'partido', 'partidos')}. "
                    "Cargando el resto de competiciones en segundo plano…"
                )
            else:
                self.status_var.set(
                    f"{_plural(len(matches), 'partido', 'partidos')}. "
                    "Selecciona uno para analizarlo. "
                    "En vivo puedes comparar las estadísticas actuales con la simulación."
                )
        else:
            self.matches_base_text = f"Sin partidos · {day}"
            if partial:
                self.matches_base_text += " · cargando resto…"
                self.status_var.set(
                    "Cargando el resto de competiciones en segundo plano…"
                )
            else:
                self.status_var.set(
                    "No hay partidos con los filtros actuales. Prueba otro día, "
                    "«Todas» o cambia la región."
                )
        self._render_matches()
        self._refresh_favorite_menu()
        self.progress.configure(maximum=1, value=1)
        if reset_state:
            self._set_busy(False)

    def _competition_catalog(self) -> List[Dict[str, Any]]:
        """Competiciones cargadas que no pertenecen a las cinco grandes."""
        seen = set()
        catalog: List[Dict[str, Any]] = []
        for match in self.matches:
            if top_league_index(match) is not None:
                continue
            tournament = match.get("tournament") or {}
            tournament_id = tournament.get("id")
            if tournament_id is None or tournament_id in seen:
                continue
            seen.add(tournament_id)
            catalog.append(
                {
                    "id": tournament_id,
                    "name": tournament.get("name") or str(tournament_id),
                    "region": match.get("region")
                    or regions.region_for_match(match),
                }
            )
        catalog.sort(key=lambda item: normalize.normalize_text(item["name"]))
        return catalog

    def _rebuild_league_menu(self) -> None:
        """Menú de ligas: cinco grandes primero y el resto en submenús."""
        if not hasattr(self, "league_menu"):
            return
        menu = self.league_menu
        menu.delete(0, "end")
        has_matches = bool(self.matches)
        sections = {match_section(match) for match in self.matches}
        top_state = "normal" if (not has_matches or "top" in sections) else "disabled"
        other_state = (
            "normal" if (not has_matches or "other" in sections) else "disabled"
        )
        south_state = (
            "normal" if (not has_matches or "south" in sections) else "disabled"
        )

        menu.add_command(
            label="Todas las competiciones",
            command=lambda: self._set_league_filter(
                "all", "Todas las competiciones"
            ),
        )
        menu.add_command(
            label="★ Las 5 grandes",
            state=top_state,
            command=lambda: self._set_league_filter("top5", "★ Las 5 grandes"),
        )
        menu.add_command(
            label="Otras europeas",
            state=other_state,
            command=lambda: self._set_league_filter("other", "Otras europeas"),
        )
        menu.add_command(
            label="Sudamérica",
            state=south_state,
            command=lambda: self._set_league_filter("south", "Sudamérica"),
        )
        menu.add_separator()
        for tournament_id, name, _ in TOP_LEAGUES:
            menu.add_command(
                label=f"★ {name}",
                state=top_state,
                command=lambda tid=tournament_id, label=name: self._set_league_filter(
                    f"league:{tid}", f"★ {label}"
                ),
            )

        catalog = self._competition_catalog()
        if not catalog:
            return
        europe = [
            item
            for item in catalog
            if item.get("region") != regions.REGION_SOUTH_AMERICA
        ]
        south = [
            item
            for item in catalog
            if item.get("region") == regions.REGION_SOUTH_AMERICA
        ]
        more = tk.Menu(menu, tearoff=False)
        self._league_submenus = [more]
        if europe:
            europe_menu = tk.Menu(more, tearoff=False)
            for item in europe:
                europe_menu.add_command(
                    label=item["name"],
                    command=lambda tid=item["id"], label=item["name"]: (
                        self._set_league_filter(f"league:{tid}", label)
                    ),
                )
            more.add_cascade(label="Otras europeas", menu=europe_menu)
            self._league_submenus.append(europe_menu)
        if south:
            south_menu = tk.Menu(more, tearoff=False)
            for item in south:
                south_menu.add_command(
                    label=item["name"],
                    command=lambda tid=item["id"], label=item["name"]: (
                        self._set_league_filter(f"league:{tid}", label)
                    ),
                )
            more.add_cascade(label="Sudamérica", menu=south_menu)
            self._league_submenus.append(south_menu)
        menu.add_separator()
        menu.add_cascade(label="Más competiciones", menu=more)

    def _set_league_filter(self, key: str, label: str) -> None:
        self.league_filter_var.set(key)
        self.league_label_var.set(label)
        try:
            self.league_btn.configure(
                style=(
                    "Filter.TMenubutton"
                    if key == "all"
                    else "FilterActive.TMenubutton"
                )
            )
        except (AttributeError, tk.TclError):
            pass
        self._render_matches()

    def _reset_league_filter(self) -> None:
        self.league_filter_var.set("all")
        self.league_label_var.set("Todas las competiciones")
        try:
            self.league_btn.configure(style="Filter.TMenubutton")
        except (AttributeError, tk.TclError):
            pass

    def _match_in_league_filter(self, match: Dict[str, Any]) -> bool:
        key = self.league_filter_var.get()
        if key == "all":
            return True
        if key == "top5":
            return top_league_index(match) is not None
        if key == "other":
            return match_section(match) == "other"
        if key == "south":
            return match_section(match) == "south"
        if key.startswith("league:"):
            try:
                tournament_id = int(key.split(":", 1)[1])
            except (TypeError, ValueError):
                return True
            raw_id = (match.get("tournament") or {}).get("id")
            try:
                return int(raw_id) == tournament_id
            except (TypeError, ValueError):
                return False
        return True

    def _render_matches(self) -> None:
        """Aplica los filtros de liga y texto sin perder la lista completa."""
        if not hasattr(self, "matches_tree"):
            return
        league_key = self.league_filter_var.get()
        base = [
            match for match in self.matches if self._match_in_league_filter(match)
        ]
        if self.favorites_only:
            base = [match for match in base if self._match_has_favorite(match)]
        status_key = self.status_filter_var.get()
        if status_key == "live":
            base = [
                match
                for match in base
                if match.get("status_type") in ("inprogress", "live", "halftime")
            ]
        elif status_key == "upcoming":
            base = [
                match
                for match in base
                if match.get("status_type") not in (
                    "inprogress",
                    "live",
                    "halftime",
                    "finished",
                )
            ]
        elif status_key == "finished":
            base = [
                match for match in base if match.get("status_type") == "finished"
            ]
        query = normalize.normalize_text(self.match_filter_var.get())
        if query:
            shown = [
                match
                for match in base
                if query
                in normalize.normalize_text(
                    " ".join(
                        str(value or "")
                        for value in (
                            (match.get("home_team") or {}).get("name"),
                            (match.get("home_team") or {}).get("short_name"),
                            (match.get("away_team") or {}).get("name"),
                            (match.get("away_team") or {}).get("short_name"),
                            (match.get("tournament") or {}).get("name"),
                            match.get("status"),
                            self._match_score(match),
                        )
                    )
                )
            ]
        else:
            shown = base
        selected_id = (
            self.selected_match.get("id") if self.selected_match else None
        )
        self._populate_matches(
            self.matches_tree,
            shown,
            grouped=not league_key.startswith("league:"),
        )
        if selected_id is not None and self.matches_tree.exists(str(selected_id)):
            self.matches_tree.selection_set(str(selected_id))
            self.matches_tree.see(str(selected_id))
        filter_bits: List[str] = []
        if league_key != "all":
            filter_bits.append(self.league_label_var.get())
        if status_key != "all":
            filter_bits.append(STATUS_FILTER_LABELS.get(status_key, status_key))
        if self.favorites_only:
            filter_bits.append("★ Favoritos")
        if query:
            filter_bits.append(f"filtro «{self.match_filter_var.get().strip()}»")
        if filter_bits:
            self.matches_count_var.set(
                f"{len(shown)} de "
                f"{_plural(len(self.matches), 'partido', 'partidos')} · "
                + " · ".join(filter_bits)
            )
        else:
            self.matches_count_var.set(
                self.matches_base_text or "Sin partidos cargados."
            )
        self._update_status_chips()
        try:
            if shown:
                self.empty_hint_label.place_forget()
            elif not self.busy and not self.loading_rest:
                if filter_bits:
                    self.empty_hint_var.set(
                        "Sin resultados con estos filtros.\n"
                        "Pulsa Esc o el botón × para limpiarlos."
                    )
                else:
                    self.empty_hint_var.set(
                        "No hay partidos para esta fecha.\n"
                        "Prueba con otro día o cambia la región."
                    )
                self.empty_hint_label.place(
                    relx=0.5, rely=0.35, anchor="center"
                )
            else:
                self.empty_hint_label.place_forget()
        except (AttributeError, tk.TclError):
            pass
        try:
            width = self.matches_tree.winfo_width() - 8
            if width > 120:
                self.matches_count_label.configure(wraplength=width)
        except (AttributeError, tk.TclError):
            pass

    def _match_values(self, match: Dict[str, Any]) -> tuple:
        home_team = match.get("home_team") or {}
        away_team = match.get("away_team") or {}
        home = _team_label(home_team)
        away = _team_label(away_team)
        home_id = self._team_id(home_team)
        away_id = self._team_id(away_team)
        if home_id is not None and home_id in self.favorites:
            home = f"★ {home}"
        if away_id is not None and away_id in self.favorites:
            away = f"★ {away}"
        return (
            self._match_time(match),
            (match.get("tournament") or {}).get("name") or "",
            home,
            away,
            self._match_score(match),
            "—",
        )

    def _section_values(
        self, tree: ttk.Treeview, key: str, count: int
    ) -> tuple:
        try:
            wide = int(tree.column("competicion", "width")) >= 94
        except (tk.TclError, ValueError):
            wide = True
        labels = {
            "top": ("★", "LAS 5 GRANDES", "TOP 5"),
            "other": ("◆", "OTRAS LIGAS", "OTRAS"),
            "south": ("●", "SUDAMÉRICA", "SUDAM."),
        }
        icon, full, short = labels.get(key, ("•", key.upper(), key.upper()))
        return (icon, full if wide else short, str(count), "", "", "")

    def _update_section_rows(self, tree: ttk.Treeview) -> None:
        for key in ("top", "other", "south"):
            iid = f"__section__{key}"
            if not tree.exists(iid):
                continue
            values = list(tree.item(iid, "values"))
            try:
                count = int(values[2]) if len(values) > 2 else 0
            except (TypeError, ValueError):
                count = 0
            tree.item(iid, values=self._section_values(tree, key, count))

    def _populate_matches(
        self,
        tree: ttk.Treeview,
        matches: List[Dict[str, Any]],
        grouped: bool = False,
    ) -> None:
        tree.delete(*tree.get_children())
        if not grouped:
            for index, match in enumerate(matches):
                match_id = match.get("id")
                if match_id is None:
                    continue
                tree.insert(
                    "",
                    "end",
                    iid=str(match_id),
                    values=self._match_values(match),
                    image=self._row_crest(match),
                    tags=self._match_row_tags(match, index),
                )
            return
        row_index = 0
        for key, section_matches in group_matches(matches):
            tree.insert(
                "",
                "end",
                iid=f"__section__{key}",
                values=self._section_values(tree, key, len(section_matches)),
                tags=(f"section_{key}",),
            )
            for match in section_matches:
                match_id = match.get("id")
                if match_id is None:
                    continue
                tree.insert(
                    "",
                    "end",
                    iid=str(match_id),
                    values=self._match_values(match),
                    image=self._row_crest(match),
                    tags=self._match_row_tags(match, row_index),
                )
                row_index += 1

    def _match_row_tags(
        self, match: Dict[str, Any], index: int
    ) -> tuple:
        tags = ["alt"] if index % 2 else []
        status = match.get("status_type")
        if status in ("inprogress", "live", "halftime"):
            tags.append("live")
        elif status == "finished":
            tags.append("finished")
        return tuple(tags)

    def _match_time(self, match: Dict[str, Any]) -> str:
        status = match.get("status_type")
        if status == "finished":
            return "Final"
        if status in ("inprogress", "live", "halftime"):
            minute = form.match_minute(match)
            return f"● {int(minute)}'" if minute > 0 else "●"
        timestamp = match.get("start_timestamp")
        if timestamp is None:
            return "—"
        try:
            tz = resolve_timezone(self._tz_name())
            return datetime.fromtimestamp(int(timestamp), tz=tz).strftime("%H:%M")
        except Exception:
            return "—"

    def _match_score(self, match: Dict[str, Any]) -> str:
        status = match.get("status_type")
        if status not in ("finished", "inprogress", "live", "halftime"):
            return "—"
        home = match.get("home_score")
        away = match.get("away_score")
        if home is None or away is None:
            return "Final" if status == "finished" else "—"
        return f"{home}-{away}"

    def _match_status_text(self, match: Dict[str, Any]) -> str:
        status = match.get("status_type")
        if status == "finished":
            return f"Final {self._match_score(match)}"
        if status in ("inprogress", "live", "halftime"):
            minute = form.match_minute(match)
            score = self._match_score(match)
            prefix = f"En vivo {int(minute)}'" if minute > 0 else "En vivo"
            return f"{prefix} · {score}" if score != "—" else prefix
        return ""

    def _on_match_select(self, event=None) -> None:
        self._hide_tooltip()
        tree = event.widget if event is not None else None
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            return
        if str(selection[0]).startswith("__section__"):
            tree.selection_remove(*selection)
            return
        try:
            match_id = int(selection[0])
        except (TypeError, ValueError):
            return

        pool = self.matches if tree is self.matches_tree else self.team_matches
        match = next((item for item in pool if item.get("id") == match_id), None)
        if match is None:
            return
        other = self.team_matches_tree if tree is self.matches_tree else self.matches_tree
        if other.selection():
            other.selection_remove(*other.selection())
        analysis_match_id = ((self.analysis or {}).get("match") or {}).get("id")
        if analysis_match_id is not None and analysis_match_id != match_id:
            self._clear_analysis_state()
        self.selected_match = match
        self._update_match_header()
        if not self.busy:
            self._set_busy(False)
            self.pending_context_match = None
            self._load_match_context(match)
        else:
            self.pending_context_match = match

    def _update_match_header(self) -> None:
        match = self.selected_match
        if not match:
            self.root.title(APP_TITLE)
            self.match_title_var.set("Selecciona un partido de la lista")
            self.match_subtitle_var.set(
                "Los datos se obtienen de la API interna de SofaScore."
            )
            if hasattr(self, "analyze_btn"):
                self.analyze_btn.configure(text="Analizar partido")
            self._show_match_context(None, None)
            self._refresh_favorite_menu()
            self._update_header_images()
            self._update_status_badge(None)
            return

        home = (match.get("home_team") or {}).get("name") or "Local"
        away = (match.get("away_team") or {}).get("name") or "Visitante"
        self.match_title_var.set(f"{home} vs {away}")

        parts = []
        tournament = (match.get("tournament") or {}).get("name")
        if tournament:
            parts.append(tournament)
        timestamp = match.get("start_timestamp")
        if timestamp is not None:
            try:
                tz = resolve_timezone(self._tz_name())
                moment = datetime.fromtimestamp(int(timestamp), tz=tz)
                parts.append(moment.strftime("%d/%m/%Y %H:%M"))
            except Exception:
                pass
        region = match.get("region")
        if region:
            parts.append(region)
        self.match_subtitle_var.set(" · ".join(parts))
        if hasattr(self, "analyze_btn"):
            self.analyze_btn.configure(
                text=(
                    "Actualizar en vivo"
                    if match.get("status_type") in ("inprogress", "live", "halftime")
                    else "Analizar partido"
                )
            )
        self._refresh_context()
        self._refresh_favorite_menu()
        self._update_header_images()
        self._update_status_badge(match)
        self.root.title(f"{APP_TITLE} — {home} vs {away}")

    # ------------------------------------------------------------------
    # Alineaciones y árbitro del partido seleccionado
    # ------------------------------------------------------------------
    def _set_lineup_badge(self, text: str, color: str) -> None:
        try:
            self.lineup_badge.configure(text=text, background=color)
        except tk.TclError:
            pass

    def _lineup_short_label(self, lineups: Optional[Dict[str, Any]]) -> str:
        status = normalize.lineup_status(lineups)
        return {"confirmada": "Confirmada", "probable": "Probable"}.get(
            status, "—"
        )

    def _show_match_context(
        self,
        lineups: Optional[Dict[str, Any]],
        referee: Optional[Dict[str, Any]],
    ) -> None:
        status = normalize.lineup_status(lineups)
        if status == "confirmada":
            self._set_lineup_badge(
                "Alineación confirmada", self.palette["good"]
            )
        elif status == "probable":
            self._set_lineup_badge(
                "Alineación probable", self.palette["warn"]
            )
        else:
            self._set_lineup_badge(
                "Alineación: sin datos", self.palette["muted"]
            )

        name = (referee or {}).get("name")
        if not name:
            self.referee_var.set("Árbitro: por designar")
            return
        parts = [f"Árbitro: {name}"]
        cards = (referee or {}).get("cards_per_match")
        fouls = (referee or {}).get("fouls_per_match")
        try:
            if cards is not None:
                parts.append(f"{float(cards):.1f} tarjetas/partido")
            if fouls is not None:
                parts.append(f"{float(fouls):.1f} faltas/partido")
        except (TypeError, ValueError):
            pass
        self.referee_var.set(" · ".join(parts))

    def _refresh_context(self) -> None:
        selected_id = (
            self.selected_match.get("id") if self.selected_match else None
        )
        analysis_match_id = ((self.analysis or {}).get("match") or {}).get("id")
        lineups = None
        referee = None
        if self.analysis and (
            selected_id is None or selected_id == analysis_match_id
        ):
            lineups = self.analysis.get("lineups")
            referee = self.analysis.get("referee")
        elif selected_id is not None:
            cached = self.context_cache.get(selected_id) or {}
            lineups = cached.get("lineups")
            referee = cached.get("referee") or (
                self.selected_match.get("referee") if self.selected_match else None
            )
        self._show_match_context(lineups, referee)

    def _load_match_context(self, match: Dict[str, Any]) -> None:
        if self.busy or not match:
            return
        match_id = match.get("id")
        if match_id is None:
            return
        if match_id in self.context_cache:
            self._refresh_context()
            return
        self._set_lineup_badge("Alineación: comprobando…", self.palette["muted"])
        self.referee_var.set("Árbitro: consultando…")
        self.context_token += 1
        token = self.context_token

        def work() -> None:
            try:
                detail = self.extractor.get_match(
                    int(match_id), sections=["lineups"]
                )
            except Exception:  # noqa: BLE001 - se muestra como «sin datos»
                detail = None
            self._post(self._apply_match_context, int(match_id), token, detail)

        threading.Thread(target=work, daemon=True).start()

    def _apply_match_context(
        self,
        match_id: int,
        token: int,
        detail: Optional[Dict[str, Any]],
    ) -> None:
        if token != self.context_token:
            return
        if not self.selected_match or self.selected_match.get("id") != match_id:
            return
        match = (detail or {}).get("match") or {}
        lineups = (detail or {}).get("lineups")
        referee = match.get("referee") or self.selected_match.get("referee")
        self.context_cache[match_id] = {
            "lineups": lineups,
            "referee": referee,
        }
        if referee:
            self.selected_match["referee"] = referee
        self._refresh_context()
        self._update_match_row_status(match_id, lineups)

    def _update_match_row_status(
        self, match_id: Optional[int], lineups: Optional[Dict[str, Any]]
    ) -> None:
        if match_id is None:
            return
        label = self._lineup_short_label(lineups)
        for tree in (self.matches_tree, self.team_matches_tree):
            iid = str(match_id)
            if not tree.exists(iid):
                continue
            values = list(tree.item(iid, "values"))
            if len(values) >= 6:
                values[5] = label
                tree.item(iid, values=values)

    def _refresh_match_row(self, match: Dict[str, Any]) -> None:
        """Actualiza minuto, marcador y estado del partido en las dos listas."""
        match_id = match.get("id")
        if match_id is None:
            return
        iid = str(match_id)
        for tree in (self.matches_tree, self.team_matches_tree):
            if not tree.exists(iid):
                continue
            values = list(tree.item(iid, "values"))
            lineup = values[5] if len(values) >= 6 else "—"
            try:
                index = tree.index(iid)
            except tk.TclError:
                index = 0
            new_values = list(self._match_values(match))
            new_values[5] = lineup
            tree.item(
                iid,
                values=new_values,
                tags=self._match_row_tags(match, index),
            )

    def _set_sim_context_from_analysis(
        self, analysis: Optional[Dict[str, Any]]
    ) -> None:
        if not analysis:
            self.sim_context_var.set(
                "Contexto: analiza un partido para consultar alineaciones y árbitro."
            )
            return
        lineups = analysis.get("lineups")
        referee = analysis.get("referee") or {}
        status = normalize.lineup_status(lineups)
        parts = [
            {
                "confirmada": "Alineación confirmada",
                "probable": "Alineación probable",
                "sin datos": "Sin alineaciones",
            }.get(status, "Sin alineaciones")
        ]
        actual = analysis.get("actual") or {}
        if actual.get("status") == "live":
            parts.insert(
                0, f"En vivo · {float(actual.get('minute') or 0):.0f}'"
            )
        if referee.get("name"):
            text = f"Árbitro {referee['name']}"
            cards = referee.get("cards_per_match")
            if cards is not None:
                try:
                    text += f" ({float(cards):.1f} tarjetas/partido)"
                except (TypeError, ValueError):
                    pass
            parts.append(text)
        else:
            parts.append("árbitro por designar")
        self.sim_context_var.set("Contexto: " + " · ".join(parts))

    # ------------------------------------------------------------------
    # Búsqueda por equipo
    # ------------------------------------------------------------------
    def search_team(self) -> None:
        if self.busy:
            return
        query = self.team_query_var.get().strip()
        if not query:
            messagebox.showinfo(
                "Buscar equipo", "Escribe el nombre de un equipo.", parent=self.root
            )
            return

        self._set_busy(True)
        self.status_var.set(f'Buscando "{query}"…')
        self.progress.configure(maximum=1, value=0)

        def work() -> None:
            try:
                results = self.extractor.search(
                    query, type_filter="team", sport="football", limit=12
                )
                self._post(self._apply_team_results, results)
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                self._post(self._show_error, exc)
            finally:
                self._post(self._set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def _apply_team_results(self, results: List[Dict[str, Any]]) -> None:
        self.team_results = results
        self.team_tree.delete(*self.team_tree.get_children())
        for index, team in enumerate(results):
            team_id = team.get("id")
            name = team.get("name") or ""
            if self._team_id(team) in self.favorites:
                name = f"★ {name}"
            self.team_tree.insert(
                "",
                "end",
                iid=str(team_id),
                values=(
                    name,
                    team.get("country") or "",
                    team_id,
                ),
                tags=("alt",) if index % 2 else (),
            )
        if results:
            first = self.team_tree.get_children()
            if first:
                self.team_tree.selection_set(first[0])
            self.status_var.set(
                f"{_plural(len(results), 'equipo', 'equipos')}. "
                "Pulsa «Ver partidos del equipo»."
            )
        else:
            self.status_var.set("No se encontraron equipos.")
        self.progress.configure(maximum=1, value=1)

    def _selected_team_id(self) -> Optional[int]:
        selection = self.team_tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except (TypeError, ValueError):
            return None

    def _on_team_select(self, _event=None) -> None:
        if not self.busy:
            self._set_busy(False)

    def view_team_matches(self) -> None:
        if self.busy:
            return
        team_id = self._selected_team_id()
        if team_id is None:
            messagebox.showinfo(
                "Equipo",
                "Selecciona un equipo de los resultados de búsqueda.",
                parent=self.root,
            )
            return

        region = REGION_LABELS.get(self.region_var.get(), "ambas")
        timezone_name = self._tz_name()
        self._set_busy(True)
        self.status_var.set("Buscando partidos del equipo…")
        self.progress.configure(maximum=1, value=0)

        def work() -> None:
            try:
                matches = upcoming.list_team_upcoming(
                    self.extractor,
                    team_id,
                    region=region,
                    limit=40,
                    timezone_name=timezone_name,
                    include_finished=True,
                    include_live=True,
                )
                self._post(self._apply_team_matches, matches)
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                self._post(self._show_error, exc)
            finally:
                self._post(self._set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def _apply_team_matches(self, matches: List[Dict[str, Any]]) -> None:
        self.team_matches = matches
        self.selected_match = None
        if self.matches_tree.selection():
            self.matches_tree.selection_remove(*self.matches_tree.selection())
        self.context_cache.clear()
        self.context_token += 1
        self._clear_analysis_state()
        self._show_match_context(None, None)
        self._update_match_header()
        self._populate_matches(self.team_matches_tree, matches)
        if matches:
            live = sum(
                1
                for match in matches
                if match.get("status_type") in ("inprogress", "live", "halftime")
            )
            finished = sum(
                1 for match in matches if match.get("status_type") == "finished"
            )
            upcoming_count = len(matches) - live - finished
            self.status_var.set(
                f"{_plural(len(matches), 'partido', 'partidos')}: {live} en vivo, "
                f"{_plural(upcoming_count, 'próximo', 'próximos')} y "
                f"{_plural(finished, 'finalizado', 'finalizados')}. "
                "Selecciona uno para analizarlo."
            )
        else:
            self.status_var.set(
                "El equipo no tiene partidos en Europa/Sudamérica "
                "con los filtros actuales."
            )
            messagebox.showinfo(
                "Sin partidos",
                "No se encontraron partidos del equipo en las "
                "competiciones admitidas.",
                parent=self.root,
            )
        self.progress.configure(maximum=1, value=1)

    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def analyze(self) -> None:
        if self.busy or not self.selected_match:
            return
        window_value = self.window_var.get()
        window: Any = None if window_value == "all" else int(window_value)

        self.analysis = None
        self._clear_analysis_state()
        self._set_busy(True)
        self.status_var.set("Analizando la forma de ambos equipos…")
        self.progress.configure(maximum=1, value=0)

        def work() -> None:
            try:
                analysis = form.analyze_match(
                    self.extractor,
                    self.selected_match,
                    window=window,
                    progress=self._progress_cb,
                    include_lineups=True,
                    include_referee=True,
                    include_context=True,
                )
                self._post(self._apply_analysis, analysis)
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                self._post(self._show_error, exc)
            finally:
                self._post(self._set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def _apply_analysis(self, analysis: Dict[str, Any]) -> None:
        incoming_id = (analysis.get("match") or {}).get("id")
        if not self.selected_match or self.selected_match.get("id") != incoming_id:
            self.status_var.set(
                "Análisis descartado: cambiaste de partido mientras se cargaba."
            )
            return
        self.analysis = analysis
        self._reset_simulation()
        self._save_analysis_history(analysis)
        match = analysis.get("match") or {}
        if self.selected_match and self.selected_match.get("id") == match.get("id"):
            for key, value in match.items():
                self.selected_match[key] = value
            self._remember_scores(self.matches)
            self._save_match_history(self.selected_match)
        home = (match.get("home_team") or {}).get("name") or "Local"
        away = (match.get("away_team") or {}).get("name") or "Visitante"

        self.match_title_var.set(f"{home} vs {away}")
        parts = []
        tournament = (match.get("tournament") or {}).get("name")
        if tournament:
            parts.append(tournament)
        timestamp = match.get("start_timestamp")
        if timestamp is not None:
            try:
                tz = resolve_timezone(self._tz_name())
                moment = datetime.fromtimestamp(int(timestamp), tz=tz)
                parts.append(moment.strftime("%d/%m/%Y %H:%M"))
            except Exception:
                pass
        window = analysis.get("window")
        parts.append(
            "toda la temporada" if window == "all" else f"últimos {window} partidos"
        )
        self.match_subtitle_var.set(" · ".join(parts))
        if hasattr(self, "analyze_btn"):
            self.analyze_btn.configure(
                text=(
                    "Actualizar en vivo"
                    if match.get("status_type") in ("inprogress", "live", "halftime")
                    else "Analizar partido"
                )
            )

        lineups = analysis.get("lineups")
        referee = analysis.get("referee")
        match_id = match.get("id")
        if match_id is not None:
            self.context_cache[match_id] = {
                "lineups": lineups,
                "referee": referee,
            }
        self._refresh_context()
        self._update_match_row_status(match_id, lineups)
        self._refresh_match_row(match)
        self._update_header_images()
        self._update_status_badge(match)
        self.root.title(f"{APP_TITLE} — {home} vs {away}")
        self._set_sim_context_from_analysis(analysis)
        home_block = (analysis.get("teams") or {}).get("home") or {}
        away_block = (analysis.get("teams") or {}).get("away") or {}

        home_name = (home_block.get("team") or {}).get("name") or "Local"
        away_name = (away_block.get("team") or {}).get("name") or "Visitante"
        home_label = (home_block.get("split") or {}).get("label") or "en casa"
        away_label = (away_block.get("split") or {}).get("label") or "fuera"
        home_short = _short_text(home_name, 11)
        away_short = _short_text(away_name, 11)
        home_split = "casa" if home_label in ("en casa", "casa") else home_label
        away_split = "fuera" if away_label in ("fuera", "de visitante") else away_label

        self.summary_tree.heading("home", text=f"{home_short} (media)")
        self.summary_tree.heading("home_split", text=f"{home_short} ({home_split})")
        self.summary_tree.heading("away", text=f"{away_short} (media)")
        self.summary_tree.heading("away_split", text=f"{away_short} ({away_split})")

        self.summary_tree.delete(*self.summary_tree.get_children())
        for index, row in enumerate(analysis.get("comparison") or []):
            self.summary_tree.insert(
                "",
                "end",
                values=(
                    row.get("label"),
                    _format_number(row.get("home")),
                    _format_number(row.get("home_split")),
                    _format_number(row.get("away")),
                    _format_number(row.get("away_split")),
                    _format_difference(row.get("difference")),
                ),
                tags=("alt",) if index % 2 else (),
            )

        self.summary_caption.set(
            f"{home_name}: {home_block.get('sample_size', 0)} partidos "
            f"({home_block.get('stats_sample_size', 0)} con estadísticas) · "
            f"forma {home_block.get('form') or '—'}   |   "
            f"{away_name}: {away_block.get('sample_size', 0)} partidos "
            f"({away_block.get('stats_sample_size', 0)} con estadísticas) · "
            f"forma {away_block.get('form') or '—'}"
        )

        self._fill_team_table(self.home_tree, home_block)
        self._fill_team_table(self.away_tree, away_block)
        self.home_caption.set(self._team_caption(home_block))
        self.away_caption.set(self._team_caption(away_block))

        self.result_notebook.select(0)
        self.progress.configure(maximum=1, value=1)
        total = home_block.get("sample_size", 0) + away_block.get("sample_size", 0)
        self.status_var.set(
            f"Análisis listo: {total} partidos de ambos equipos. "
            "Puedes exportar el resultado."
        )
        self._set_busy(False)

    def _team_caption(self, block: Dict[str, Any]) -> str:
        team = (block.get("team") or {}).get("name") or "Equipo"
        sample = block.get("sample_size", 0)
        stats = block.get("stats_sample_size", 0)
        form_text = block.get("form") or "—"
        split = block.get("split") or {}
        return (
            f"{team}: {_plural(sample, 'partido', 'partidos')} · "
            f"{stats} con estadísticas · "
            f"forma {form_text} · {split.get('sample_size', 0)} "
            f"{split.get('label', '')}".strip()
        )

    def _fill_team_table(
        self, tree: ttk.Treeview, block: Dict[str, Any]
    ) -> None:
        tree.delete(*tree.get_children())
        for index, row in enumerate(block.get("matches") or []):
            outcome = row.get("outcome")
            score = row.get("score")
            tree.insert(
                "",
                "end",
                values=(
                    _short_day(row.get("date")),
                    row.get("tournament") or "",
                    "Casa" if row.get("home") else "Fuera",
                    row.get("opponent") or "",
                    outcome or "—",
                    score or "—",
                    _format_int(row.get("corners")),
                    _format_int(row.get("cards")),
                    _format_int(row.get("shots")),
                    _format_int(row.get("shots_on_target")),
                    _format_int(row.get("fouls")),
                    _format_int(row.get("saves")),
                ),
                tags=("alt",) if index % 2 else (),
            )

    # ------------------------------------------------------------------
    # Simulación Monte Carlo
    # ------------------------------------------------------------------
    def run_simulation(self) -> None:
        """Lanza la simulación en un hilo para no congelar Tkinter."""
        if self.busy or not self.analysis:
            return
        raw = (
            str(self.sim_iterations_var.get())
            .strip()
            .replace(".", "")
            .replace(",", "")
            .replace(" ", "")
        )
        try:
            iterations = int(raw)
        except ValueError:
            messagebox.showerror(
                "Valor no válido",
                "El número de simulaciones debe ser un entero, por ejemplo 50000.",
                parent=self.root,
            )
            return
        if not (
            simulation.MIN_ITERATIONS
            <= iterations
            <= simulation.MAX_ITERATIONS
        ):
            messagebox.showerror(
                "Valor fuera de rango",
                (
                    f"Usa entre {simulation.MIN_ITERATIONS:,} y "
                    f"{simulation.MAX_ITERATIONS:,} simulaciones."
                ).replace(",", "."),
                parent=self.root,
            )
            return
        seed_text = self.sim_seed_var.get().strip()
        if seed_text:
            try:
                seed: Optional[int] = int(seed_text)
            except ValueError:
                messagebox.showerror(
                    "Semilla no válida",
                    "La semilla debe ser un número entero o quedar vacía para "
                    "usar una aleatoria.",
                    parent=self.root,
                )
                return
        else:
            seed = None

        analysis = self.analysis
        cached = simulation_cache.load_simulation(
            analysis, iterations, seed
        )
        if cached is not None:
            if analysis.get("actual") is not None:
                cached = dict(cached)
                cached["actual"] = analysis["actual"]
            self._reset_simulation()
            self._apply_simulation(cached)
            cached_meta = cached.get("meta") or {}
            cached_iterations = int(cached_meta.get("iterations") or 0)
            self.status_var.set(
                "Simulación cargada desde caché: "
                f"{cached_iterations:,} escenarios · "
                f"{cached_meta.get('elapsed_seconds')} s ahorrados.".replace(
                    ",", "."
                )
            )
            return

        self._reset_simulation()
        self._set_busy(True)
        self.status_var.set(
            f"Simulando {iterations:,} partidos con NumPy…".replace(",", ".")
        )
        self.progress.stop()
        self.progress.configure(mode="indeterminate")
        self.progress.start(15)

        def work() -> None:
            try:
                summary = simulation.simulate_match(
                    analysis, iterations=iterations, seed=seed
                )
                simulation_cache.save_simulation(
                    summary, analysis, iterations, seed
                )
                self._post(self._apply_simulation, summary)
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                self._post(self._show_error, exc)
            finally:
                self._post(self._stop_sim_progress)
                self._post(self._set_busy, False)

        threading.Thread(target=work, daemon=True).start()

    def clear_simulation_cache(self) -> None:
        """Borra las simulaciones guardadas en disco."""
        try:
            count = simulation_cache.cache_count()
        except OSError:
            count = 0
        if count and not messagebox.askyesno(
            "Vaciar caché",
            (
                f"¿Eliminar {_plural(count, 'simulación guardada', 'simulaciones guardadas')}?"
                "\n\nSe volverán a calcular cuando las necesites."
            ),
            parent=self.root,
        ):
            return
        try:
            count = simulation_cache.clear_simulation_cache()
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror(
                "Caché", f"No se pudo vaciar la caché:\n{exc}", parent=self.root
            )
            return
        if count:
            message = (
                "Se eliminó 1 simulación guardada."
                if count == 1
                else f"Se eliminaron {count} simulaciones guardadas."
            )
        else:
            message = "No había simulaciones guardadas."
        self.status_var.set(message)
        messagebox.showinfo(
            "Caché de simulaciones",
            f"{message}\n\n{simulation_cache.cache_dir()}",
            parent=self.root,
        )
        self._update_cache_button()

    def _update_cache_button(self) -> None:
        try:
            count = simulation_cache.cache_count()
        except OSError:
            count = 0
        self.clear_cache_btn.configure(
            text=f"Vaciar caché ({count})" if count else "Vaciar caché"
        )

    def _stop_sim_progress(self) -> None:
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        self.progress.configure(mode="determinate", maximum=1, value=1)

    def _reset_simulation(self) -> None:
        """Borra el resultado anterior al analizar otro partido o simular."""
        self.simulation_summary = None
        for chart in getattr(self, "chart_widgets", []):
            chart.clear()
        if hasattr(self, "kpi_strip"):
            self.kpi_strip.set_cards(self._empty_kpi_cards())
        if hasattr(self, "sim_hist_caption"):
            self.sim_hist_caption.set(
                "Media, mediana y rango P10–P90 de la métrica elegida."
            )
        if hasattr(self, "sim_validation_tree"):
            self.sim_validation_tree.delete(
                *self.sim_validation_tree.get_children()
            )
            actual = (self.analysis or {}).get("actual")
            if actual:
                if actual.get("status") == "live":
                    self.sim_validation_caption.set(
                        f"En vivo · {float(actual.get('minute') or 0):.0f}' · "
                        "Ejecuta la simulación para comparar el estado actual."
                    )
                else:
                    self.sim_validation_caption.set(
                        f"Resultado real: {actual.get('score')}. "
                        "Ejecuta la simulación para comparar."
                    )
            else:
                self.sim_validation_caption.set(
                    "Disponible para partidos finalizados o en vivo."
                )
        if hasattr(self, "sim_csv_btn"):
            self.sim_csv_btn.configure(state="disabled")
            self.sim_json_btn.configure(state="disabled")
        if hasattr(self, "sim_context_var"):
            self._set_sim_context_from_analysis(self.analysis)

    def _empty_kpi_cards(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "GOLES",
                "value": "—",
                "subtitle": "esperados",
                "color": self.palette["accent"],
            },
            {
                "title": "RESULTADO",
                "value": "—",
                "subtitle": "más probable",
                "color": self.palette["home"],
            },
            {
                "title": "AMBOS MARCAN",
                "value": "—",
                "subtitle": "sí / no",
                "color": self.palette["good"],
            },
            {
                "title": "OVER 2,5",
                "value": "—",
                "subtitle": "goles",
                "color": self.palette["warn"],
            },
            {
                "title": "CÓRNERS",
                "value": "—",
                "subtitle": "esperados",
                "color": self.palette["accent2"],
            },
        ]

    def _apply_simulation(self, summary: Dict[str, Any]) -> None:
        incoming_id = (summary.get("meta") or {}).get("match_id")
        current_id = ((self.analysis or {}).get("match") or {}).get("id")
        if incoming_id is not None and current_id != incoming_id:
            self.status_var.set(
                "Simulación descartada: cambiaste de partido mientras se calculaba."
            )
            return
        self.simulation_summary = summary
        analysis = self.analysis or {}
        self._save_prediction_history(summary, analysis)
        teams = summary.get("teams") or {}
        home_block = teams.get("home") or {}
        away_block = teams.get("away") or {}
        home_name = home_block.get("name") or "Local"
        away_name = away_block.get("name") or "Visitante"
        home_expected = home_block.get("expected") or {}
        away_expected = away_block.get("expected") or {}

        totals = summary.get("totals") or {}
        totals_mean = totals.get("mean") or {}
        totals_percentiles = totals.get("percentiles") or {}
        probabilities = summary.get("probabilities") or {}
        winner = probabilities.get("winner") or {}
        over_under = probabilities.get("over_under") or {}
        btts = float(probabilities.get("btts") or 0.0)
        over_25 = float(
            ((over_under.get("goals") or {}).get("2.5") or {}).get("over") or 0.0
        )

        top_side = max(
            ("home", "draw", "away"),
            key=lambda side: float(winner.get(side) or 0.0),
        )
        top_label = {
            "home": home_name,
            "draw": "Empate",
            "away": away_name,
        }[top_side]
        top_probability = float(winner.get(top_side) or 0.0)

        corners_pct = totals_percentiles.get("corners") or {}
        self.kpi_strip.set_cards(
            [
                {
                    "title": "GOLES",
                    "value": _format_number(totals_mean.get("goals")),
                    "subtitle": (
                        f"L {_format_number(home_expected.get('goals_for'))} · "
                        f"V {_format_number(away_expected.get('goals_for'))}"
                    ),
                    "color": self.palette["accent"],
                },
                {
                    "title": "RESULTADO",
                    "value": f"{top_probability * 100:.0f}%",
                    "subtitle": f"gana {_short_text(top_label, 18)}",
                    "color": self.palette["home"],
                },
                {
                    "title": "AMBOS MARCAN",
                    "value": f"{btts * 100:.0f}%",
                    "subtitle": "sí",
                    "color": self.palette["good"],
                },
                {
                    "title": "OVER 2,5",
                    "value": f"{over_25 * 100:.0f}%",
                    "subtitle": "goles",
                    "color": self.palette["warn"],
                },
                {
                    "title": "CÓRNERS",
                    "value": _format_number(totals_mean.get("corners")),
                    "subtitle": (
                        f"P10–P90 {_format_int(corners_pct.get('p10'))}–"
                        f"{_format_int(corners_pct.get('p90'))}"
                    ),
                    "color": self.palette["accent2"],
                },
            ]
        )

        self.sim_compare_chart.set_data(
            [
                {
                    "label": "Goles",
                    "home": home_expected.get("goals_for"),
                    "away": away_expected.get("goals_for"),
                },
                {
                    "label": "Remates",
                    "home": home_expected.get("shots"),
                    "away": away_expected.get("shots"),
                },
                {
                    "label": "Rem. al arco",
                    "home": home_expected.get("shots_on_target"),
                    "away": away_expected.get("shots_on_target"),
                },
                {
                    "label": "Córners",
                    "home": home_expected.get("corners"),
                    "away": away_expected.get("corners"),
                },
                {
                    "label": "Tarjetas",
                    "home": home_expected.get("cards"),
                    "away": away_expected.get("cards"),
                },
                {
                    "label": "Faltas",
                    "home": home_expected.get("fouls"),
                    "away": away_expected.get("fouls"),
                },
                {
                    "label": "Paradas",
                    "home": home_expected.get("saves"),
                    "away": away_expected.get("saves"),
                },
            ],
            title="Esperado por equipo",
            home_name=home_name,
            away_name=away_name,
        )

        self.sim_donut_chart.set_data(
            [
                {
                    "label": home_name,
                    "value": float(winner.get("home") or 0.0),
                    "color": self.palette["home"],
                },
                {
                    "label": "Empate",
                    "value": float(winner.get("draw") or 0.0),
                    "color": self.palette["chart_axis"],
                },
                {
                    "label": away_name,
                    "value": float(winner.get("away") or 0.0),
                    "color": self.palette["away"],
                },
            ],
            center_value=f"{top_probability * 100:.0f}%",
            center_label=f"gana {top_label}",
        )

        scorelines = summary.get("scorelines") or []
        self.sim_scores_chart.set_data(
            [
                {
                    "label": str(item.get("score", "")),
                    "value": float(item.get("probability") or 0.0),
                    "color": (
                        self.palette["accent"]
                        if index == 0
                        else self.palette["accent_soft"]
                    ),
                }
                for index, item in enumerate(scorelines[:6])
            ],
            title="Marcadores más probables",
        )

        matrix = summary.get("score_matrix") or {}
        self.sim_heatmap.set_data(
            matrix.get("labels") or [],
            matrix.get("probabilities") or [],
            title="Matriz de marcadores (%)",
            home_name=home_name,
            away_name=away_name,
        )

        self._update_sim_histogram()
        self._update_sim_market()
        self._update_validation(summary)
        self._update_cache_button()

        model = summary.get("model") or {}
        lineup_info = model.get("lineups") or {}
        referee_info = model.get("referee") or {}
        lineup_status = lineup_info.get("status")
        lineup_text = {
            "confirmada": "Alineación confirmada",
            "probable": "Alineación probable",
            "sin datos": "Sin alineaciones",
        }.get(lineup_status, "Sin alineaciones")
        if lineup_info.get("applied"):
            lineup_text += " aplicada"
            if lineup_status == "probable":
                lineup_text += " al 45 %"
        elif lineup_status == "confirmada":
            lineup_text += " (sin datos de temporada)"
        elif lineup_status == "probable":
            lineup_text += " (sin datos suficientes)"
        context_parts = [lineup_text]
        if referee_info.get("name"):
            referee_text = f"Árbitro {referee_info['name']}"
            if referee_info.get("applied"):
                try:
                    referee_text += (
                        f" (tarjetas x{float(referee_info.get('cards_factor')):.2f}, "
                        f"faltas x{float(referee_info.get('fouls_factor')):.2f})"
                    )
                except (TypeError, ValueError):
                    pass
            context_parts.append(referee_text)
        else:
            context_parts.append("árbitro por designar")
        actual = summary.get("actual") or (self.analysis or {}).get("actual") or {}
        if actual.get("status") == "live":
            context_parts.insert(
                0, f"En vivo · {float(actual.get('minute') or 0):.0f}'"
            )
        context_info = model.get("context") or {}
        if context_info.get("applied"):
            context_parts.append(
                "Fuerza contextual "
                f"L x{float(context_info.get('goal_factor_home', 1)):.2f} / "
                f"V x{float(context_info.get('goal_factor_away', 1)):.2f}"
            )
        neural_info = model.get("neural") or {}
        if neural_info.get("applied"):
            context_parts.append("Red neuronal aplicada")
        self.sim_context_var.set("Contexto: " + " · ".join(context_parts))
        if summary.get("actual"):
            self.sim_notebook.select(self.sim_validation_tab)

        meta = summary.get("meta") or {}
        iterations = int(meta.get("iterations") or 0)
        elapsed = float(meta.get("elapsed_seconds") or 0.0)
        seed = meta.get("seed")
        seed_text = "aleatoria" if seed is None else str(seed)
        self.status_var.set(
            f"Simulación lista: {iterations:,} escenarios en {elapsed:.2f} s "
            f"(semilla {seed_text}).".replace(",", ".")
        )
        self.progress.configure(mode="determinate", maximum=1, value=1)
        self._set_busy(False)

    def _update_validation(self, summary: Dict[str, Any]) -> None:
        """Compara el resultado real de un partido finalizado con la simulación."""
        self.sim_validation_tree.delete(
            *self.sim_validation_tree.get_children()
        )
        actual = summary.get("actual") or (self.analysis or {}).get("actual")
        if not actual:
            self.sim_validation_caption.set(
                "Disponible para partidos finalizados."
            )
            self.sim_validation_chart.clear()
            return

        actual_totals = actual.get("totals") or {}
        simulate_totals = (summary.get("totals") or {}).get("mean") or {}
        percentiles = (summary.get("totals") or {}).get("percentiles") or {}
        live = actual.get("status") == "live"
        minute = float(actual.get("minute") or 0.0)
        scale = min(1.0, max(0.0, minute / 90.0)) if live else 1.0
        metrics = (
            ("goals", "Goles"),
            ("corners", "Córners"),
            ("cards", "Tarjetas"),
            ("shots", "Remates"),
            ("shots_on_target", "Remates al arco"),
            ("fouls", "Faltas"),
            ("saves", "Paradas"),
        )
        chart_items: List[Dict[str, Any]] = []
        for index, (key, label) in enumerate(metrics):
            real = actual_totals.get(key)
            simulated = simulate_totals.get(key)
            if real is None or simulated is None:
                continue
            expected = float(simulated) * scale
            distribution = percentiles.get(key) or {}
            p10 = distribution.get("p10")
            p90 = distribution.get("p90")
            scaled_p10 = float(p10) * scale if p10 is not None else None
            scaled_p90 = float(p90) * scale if p90 is not None else None
            error = float(real) - expected
            inside = (
                "Sí"
                if scaled_p10 is not None
                and scaled_p90 is not None
                and scaled_p10 <= float(real) <= scaled_p90
                else "No"
            )
            self.sim_validation_tree.insert(
                "",
                "end",
                values=(
                    label,
                    _format_int(real),
                    _format_number(expected),
                    _format_difference(round(error, 2)),
                    (
                        f"{_format_int(scaled_p10)}–{_format_int(scaled_p90)}"
                        if scaled_p10 is not None and scaled_p90 is not None
                        else "—"
                    ),
                    inside,
                ),
                tags=("alt",) if index % 2 else (),
            )
            chart_items.append(
                {
                    "label": label,
                    "home": float(real),
                    "away": expected,
                }
            )

        self.sim_validation_chart.set_data(
            chart_items,
            title=(
                "Actual vs esperado al minuto"
                if live
                else "Real vs simulado (totales)"
            ),
            home_name="Actual" if live else "Real",
            away_name="Esperado" if live else "Simulado",
        )
        self.sim_validation_tree.yview_moveto(0)
        score = actual.get("score") or "—"
        detail = (
            ""
            if actual.get("stats_available", True)
            else " · sin estadísticas detalladas"
        )
        if live:
            goals = _format_number(simulate_totals.get("goals"))
            corners = _format_number(simulate_totals.get("corners"))
            cards = _format_number(simulate_totals.get("cards"))
            fouls = _format_number(simulate_totals.get("fouls"))
            self.sim_validation_caption.set(
                f"En vivo · {minute:.0f}' · Marcador actual {score} · "
                f"Actual vs esperado al minuto · Proyección final: "
                f"{goals} goles, {corners} córners, {cards} tarjetas y "
                f"{fouls} faltas · El partido objetivo se excluye del "
                f"entrenamiento{detail}. Pulsa «Analizar partido» para "
                "actualizar."
            )
        else:
            probability = self._actual_score_probability(summary, actual)
            probability_text = (
                f"{probability * 100:.2f}%"
                if probability is not None
                else "—"
            )
            self.sim_validation_caption.set(
                f"Resultado real: {score} · Probabilidad simulada del "
                f"marcador: {probability_text} · El partido objetivo se "
                f"excluye del entrenamiento{detail}."
            )

    def _actual_score_probability(
        self, summary: Dict[str, Any], actual: Dict[str, Any]
    ) -> Optional[float]:
        matrix = summary.get("score_matrix") or {}
        labels = matrix.get("labels") or []
        probabilities = matrix.get("probabilities") or []
        if not labels or not probabilities:
            return None
        home = actual.get("home") or {}
        away = actual.get("away") or {}
        try:
            home_goals = int(home.get("goals_for"))
            away_goals = int(away.get("goals_for"))
        except (TypeError, ValueError):
            return None
        limit = len(labels) - 1
        row = min(max(home_goals, 0), limit)
        column = min(max(away_goals, 0), limit)
        try:
            return float(probabilities[row][column])
        except (IndexError, TypeError, ValueError):
            return None

    def _simulation_percentiles(
        self, key: str, scope: str
    ) -> Dict[str, Any]:
        summary = self.simulation_summary or {}
        if scope == "total":
            return (
                ((summary.get("totals") or {}).get("percentiles") or {}).get(key)
                or {}
            )
        team = (summary.get("teams") or {}).get(scope) or {}
        percentile_key = "goals" if key.startswith("goals") else key
        return (team.get("percentiles") or {}).get(percentile_key) or {}

    def _on_sim_histogram_change(self, _event: Any = None) -> None:
        self._update_sim_histogram()

    def _update_sim_histogram(self) -> None:
        if not self.simulation_summary:
            self.sim_hist_chart.clear()
            return
        selected = self.sim_hist_var.get()
        option = next(
            (
                item
                for item in SIM_HISTOGRAM_OPTIONS
                if item[0] == selected
            ),
            SIM_HISTOGRAM_OPTIONS[0],
        )
        label, key, scope = option
        histogram = (self.simulation_summary.get("histograms") or {}).get(key) or {}
        percentiles = self._simulation_percentiles(key, scope)
        self.sim_hist_chart.set_data(
            histogram.get("labels") or [],
            histogram.get("percent") or [],
            title=f"{label} · % de simulaciones",
            marker=percentiles.get("mean"),
            step=int(histogram.get("step", 1)),
        )
        if percentiles:
            iterations = int(
                (self.simulation_summary.get("meta") or {}).get("iterations") or 0
            )
            overflow = float(histogram.get("overflow_percent") or 0.0)
            overflow_text = ""
            if overflow:
                overflow_text = (
                    f" · cola {histogram.get('overflow_label')} {overflow:.1f}%"
                )
            self.sim_hist_caption.set(
                f"Media {_format_number(percentiles.get('mean'))} · "
                f"mediana {_format_number(percentiles.get('median'))} · "
                f"P10–P90 {_format_int(percentiles.get('p10'))}–"
                f"{_format_int(percentiles.get('p90'))} · "
                f"P99 {_format_int(percentiles.get('p99'))} · "
                f"{iterations:,} escenarios{overflow_text}".replace(",", ".")
            )
        else:
            self.sim_hist_caption.set("Sin percentiles disponibles.")

    def _on_sim_market_change(self, _event: Any = None) -> None:
        self._update_sim_market()

    def _update_sim_market(self) -> None:
        if not self.simulation_summary:
            self.sim_market_chart.clear()
            return
        selected = self.sim_market_var.get()
        option = next(
            (item for item in SIM_MARKET_OPTIONS if item[0] == selected),
            SIM_MARKET_OPTIONS[0],
        )
        label, key = option
        items: List[Dict[str, Any]] = []
        if key == "saves":
            teams = self.simulation_summary.get("teams") or {}
            for side, header in (("home", "Arquero local"), ("away", "Arquero visitante")):
                team = teams.get(side) or {}
                expected = float((team.get("expected") or {}).get("saves") or 0.0)
                items.append(
                    {
                        "label": f"{header} · {expected:.1f} esperadas",
                        "header": True,
                    }
                )
                lines = ((team.get("over_under") or {}).get("saves")) or {}
                for line in sorted(lines, key=lambda value: float(value)):
                    values = lines[line]
                    items.append(
                        {
                            "label": f"Más de {line}",
                            "value": float(values.get("over") or 0.0),
                            "color": self.palette["accent"],
                        }
                    )
                    items.append(
                        {
                            "label": f"Menos de {line}",
                            "value": float(values.get("under") or 0.0),
                            "color": self.palette["accent2"],
                        }
                    )
            self.sim_market_chart.set_data(
                items, title=f"Over/Under · {label} por arquero"
            )
            return

        lines = (
            ((self.simulation_summary.get("probabilities") or {}).get("over_under"))
            or {}
        ).get(key) or {}
        for line in sorted(lines, key=lambda value: float(value)):
            values = lines[line]
            items.append(
                {"label": f"Línea {line}", "header": True}
            )
            items.append(
                {
                    "label": f"Más de {line}",
                    "value": float(values.get("over") or 0.0),
                    "color": self.palette["accent"],
                }
            )
            items.append(
                {
                    "label": f"Menos de {line}",
                    "value": float(values.get("under") or 0.0),
                    "color": self.palette["accent2"],
                }
            )
        self.sim_market_chart.set_data(
            items, title=f"Over/Under · {label}"
        )

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def export_csv(self) -> None:
        if self.busy or not self.analysis:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar resumen en CSV",
            defaultextension=".csv",
            filetypes=(("CSV", "*.csv"), ("Todos los archivos", "*.*")),
            initialfile="analisis_forma.csv",
        )
        if not path:
            return
        try:
            summary_path = Path(path)
            export.write_csv(self.analysis.get("comparison") or [], summary_path)
            matches_path = summary_path.with_name(
                f"{summary_path.stem}_partidos.csv"
            )
            export.write_csv(form.match_rows(self.analysis), matches_path)
            self.status_var.set(f"Datos guardados en {summary_path} y {matches_path}")
            messagebox.showinfo(
                "Exportado",
                f"Resumen:\n{summary_path}\n\nPartidos por equipo:\n{matches_path}",
                parent=self.root,
            )
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror("Error al exportar", str(exc), parent=self.root)

    def export_json(self) -> None:
        if self.busy or not self.analysis:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar análisis en JSON",
            defaultextension=".json",
            filetypes=(("JSON", "*.json"), ("Todos los archivos", "*.*")),
            initialfile="analisis_forma.json",
        )
        if not path:
            return
        try:
            export.write_output(self.analysis, "json", Path(path))
            self.status_var.set(f"Análisis guardado en {path}")
            messagebox.showinfo(
                "Exportado", f"Análisis guardado en:\n{path}", parent=self.root
            )
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror("Error al exportar", str(exc), parent=self.root)

    def export_simulation_csv(self) -> None:
        if self.busy or not self.simulation_summary:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar simulación en CSV",
            defaultextension=".csv",
            filetypes=(("CSV", "*.csv"), ("Todos los archivos", "*.*")),
            initialfile="simulacion_partido.csv",
        )
        if not path:
            return
        try:
            rows = simulation.summary_rows(self.simulation_summary)
            export.write_csv(rows, Path(path))
            self.status_var.set(f"Simulación guardada en {path}")
            messagebox.showinfo(
                "Exportado",
                f"Simulación guardada en:\n{path}",
                parent=self.root,
            )
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror("Error al exportar", str(exc), parent=self.root)

    def export_simulation_json(self) -> None:
        if self.busy or not self.simulation_summary:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar simulación en JSON",
            defaultextension=".json",
            filetypes=(("JSON", "*.json"), ("Todos los archivos", "*.*")),
            initialfile="simulacion_partido.json",
        )
        if not path:
            return
        try:
            export.write_output(self.simulation_summary, "json", Path(path))
            self.status_var.set(f"Simulación guardada en {path}")
            messagebox.showinfo(
                "Exportado",
                f"Simulación guardada en:\n{path}",
                parent=self.root,
            )
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror("Error al exportar", str(exc), parent=self.root)


def run_gui(
    client: Optional[SofaScoreClient] = None,
    workers: int = 6,
    timezone_name: str = "local",
    theme: str = "auto",
) -> int:
    _enable_dpi_awareness()
    root = tk.Tk()
    SofaScoreApp(
        root,
        client=client,
        workers=workers,
        timezone_name=timezone_name,
        auto_load=True,
        theme=theme,
    )
    root.mainloop()
    return 0


def main() -> int:
    return run_gui()
