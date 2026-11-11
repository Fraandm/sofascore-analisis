"""Historial local de partidos y predicciones en SQLite.

Se usa desde la interfaz para el cuaderno de predicciones, la sala de
directo y el explorador de datos. No depende de Tkinter ni de la red.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


def default_history_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "sofascore-gui" / "history.db"


def _side_from_score(score: Optional[str]) -> Optional[str]:
    if not score or "-" not in str(score):
        return None
    try:
        home, away = str(score).split("-", 1)
        home_i, away_i = int(home), int(away)
    except (TypeError, ValueError):
        return None
    if home_i > away_i:
        return "home"
    if away_i > home_i:
        return "away"
    return "draw"


def _score_parts(score: Optional[str]) -> tuple:
    if not score or "-" not in str(score):
        return None, None
    try:
        home, away = str(score).split("-", 1)
        return int(home), int(away)
    except (TypeError, ValueError):
        return None, None


class HistoryStore:
    """Acceso sencillo a un archivo SQLite local."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else default_history_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY,
                    day TEXT,
                    status TEXT,
                    start_timestamp INTEGER,
                    tournament_id INTEGER,
                    tournament TEXT,
                    region TEXT,
                    home_id INTEGER,
                    home_name TEXT,
                    away_id INTEGER,
                    away_name TEXT,
                    home_score INTEGER,
                    away_score INTEGER,
                    payload TEXT,
                    updated_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_matches_day ON matches(day);
                CREATE INDEX IF NOT EXISTS idx_matches_names ON matches(home_name, away_name);
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    created_at REAL,
                    model_version TEXT,
                    iterations INTEGER,
                    seed INTEGER,
                    window TEXT,
                    home_name TEXT,
                    away_name TEXT,
                    tournament TEXT,
                    day TEXT,
                    start_timestamp INTEGER,
                    prob_home REAL,
                    prob_draw REAL,
                    prob_away REAL,
                    btts REAL,
                    over25 REAL,
                    expected_home REAL,
                    expected_away REAL,
                    expected_goals REAL,
                    actual_home INTEGER,
                    actual_away INTEGER,
                    actual_status TEXT,
                    actual_score TEXT,
                    payload TEXT,
                    UNIQUE(match_id, iterations, seed, model_version)
                );
                CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id);
                CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    created_at REAL,
                    window TEXT,
                    payload TEXT
                );
                """
            )

    # ------------------------------------------------------------------
    # Partidos
    # ------------------------------------------------------------------
    def save_match(self, match: Dict[str, Any], day: Optional[str] = None) -> None:
        match_id = match.get("id")
        if match_id is None:
            return
        tournament = match.get("tournament") or {}
        home = match.get("home_team") or {}
        away = match.get("away_team") or {}
        if day is None:
            local = str(match.get("start_time_local") or "")
            day = local[:10] if len(local) >= 10 else ""
        values = (
            int(match_id),
            day,
            match.get("status_type"),
            match.get("start_timestamp"),
            tournament.get("id"),
            tournament.get("name"),
            match.get("region"),
            home.get("id"),
            home.get("name"),
            away.get("id"),
            away.get("name"),
            match.get("home_score"),
            match.get("away_score"),
            json.dumps(match, ensure_ascii=False),
            time.time(),
        )
        with self._write_lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO matches (
                    id, day, status, start_timestamp, tournament_id, tournament,
                    region, home_id, home_name, away_id, away_name,
                    home_score, away_score, payload, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    day=COALESCE(NULLIF(excluded.day, ''), matches.day),
                    status=excluded.status,
                    start_timestamp=excluded.start_timestamp,
                    tournament_id=excluded.tournament_id,
                    tournament=excluded.tournament,
                    region=excluded.region,
                    home_id=excluded.home_id,
                    home_name=excluded.home_name,
                    away_id=excluded.away_id,
                    away_name=excluded.away_name,
                    home_score=excluded.home_score,
                    away_score=excluded.away_score,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                values,
            )

    def save_matches(
        self, matches: Iterable[Dict[str, Any]], day: str = ""
    ) -> None:
        with self._write_lock, self._connection() as connection:
            for match in matches:
                match_id = match.get("id")
                if match_id is None:
                    continue
                tournament = match.get("tournament") or {}
                home = match.get("home_team") or {}
                away = match.get("away_team") or {}
                connection.execute(
                    """
                    INSERT INTO matches (
                        id, day, status, start_timestamp, tournament_id, tournament,
                        region, home_id, home_name, away_id, away_name,
                        home_score, away_score, payload, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        day=COALESCE(NULLIF(excluded.day, ''), matches.day),
                        status=excluded.status,
                        start_timestamp=excluded.start_timestamp,
                        tournament_id=excluded.tournament_id,
                        tournament=excluded.tournament,
                        region=excluded.region,
                        home_id=excluded.home_id,
                        home_name=excluded.home_name,
                        away_id=excluded.away_id,
                        away_name=excluded.away_name,
                        home_score=excluded.home_score,
                        away_score=excluded.away_score,
                        payload=excluded.payload,
                        updated_at=excluded.updated_at
                    """,
                    (
                        int(match_id),
                        day,
                        match.get("status_type"),
                        match.get("start_timestamp"),
                        tournament.get("id"),
                        tournament.get("name"),
                        match.get("region"),
                        home.get("id"),
                        home.get("name"),
                        away.get("id"),
                        away.get("name"),
                        match.get("home_score"),
                        match.get("away_score"),
                        json.dumps(match, ensure_ascii=False),
                        time.time(),
                    ),
                )

    def update_match_result(self, match: Dict[str, Any]) -> None:
        match_id = match.get("id")
        if match_id is None:
            return
        with self._write_lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE matches SET status=?, home_score=?, away_score=?,
                    payload=?, updated_at=?
                WHERE id=?
                """,
                (
                    match.get("status_type"),
                    match.get("home_score"),
                    match.get("away_score"),
                    json.dumps(match, ensure_ascii=False),
                    time.time(),
                    int(match_id),
                ),
            )
            actual_score = self._match_score(match)
            if actual_score not in (None, "—"):
                connection.execute(
                    """
                    UPDATE predictions SET actual_home=?, actual_away=?,
                        actual_status=?, actual_score=?
                    WHERE match_id=?
                    """,
                    (
                        match.get("home_score"),
                        match.get("away_score"),
                        match.get("status_type"),
                        actual_score,
                        int(match_id),
                    ),
                )

    @staticmethod
    def _match_score(match: Dict[str, Any]) -> Optional[str]:
        home = match.get("home_score")
        away = match.get("away_score")
        if home is None or away is None:
            return None
        return f"{home}-{away}"

    def list_matches(
        self,
        query: str = "",
        status: str = "",
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []
        if query:
            clauses.append(
                "(LOWER(home_name) LIKE ? OR LOWER(away_name) LIKE ? "
                "OR LOWER(tournament) LIKE ?)"
            )
            needle = f"%{query.casefold()}%"
            params.extend([needle, needle, needle])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, int(limit)))
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, day, status, start_timestamp, tournament, region,
                       home_name, away_name, home_score, away_score
                FROM matches
                {where}
                ORDER BY COALESCE(start_timestamp, 0) DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Predicciones y análisis
    # ------------------------------------------------------------------
    def save_analysis(self, analysis: Dict[str, Any]) -> None:
        match = analysis.get("match") or {}
        match_id = match.get("id")
        if match_id is None:
            return
        with self._write_lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO analyses (match_id, created_at, window, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(match_id),
                    time.time(),
                    str(analysis.get("window") or ""),
                    json.dumps(analysis, ensure_ascii=False),
                ),
            )

    def save_prediction(
        self, summary: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Optional[int]:
        meta = summary.get("meta") or {}
        match_id = meta.get("match_id")
        if match_id is None:
            return None
        probabilities = summary.get("probabilities") or {}
        winner = probabilities.get("winner") or {}
        over_under = probabilities.get("over_under") or {}
        over25 = (
            ((over_under.get("goals") or {}).get("2.5") or {}).get("over")
        )
        teams = summary.get("teams") or {}
        home_expected = (teams.get("home") or {}).get("expected") or {}
        away_expected = (teams.get("away") or {}).get("expected") or {}
        totals = (summary.get("totals") or {}).get("mean") or {}
        actual = summary.get("actual") or analysis.get("actual") or {}
        actual_score = actual.get("score")
        actual_home, actual_away = _score_parts(actual_score)
        model_version = str(
            meta.get("model_version")
            or summary.get("model", {}).get("version")
            or "local"
        )
        now = time.time()
        values = (
            int(match_id),
            now,
            model_version,
            int(meta.get("iterations") or 0),
            int(meta.get("seed")) if meta.get("seed") is not None else -1,
            str(meta.get("window") or ""),
            meta.get("home_team"),
            meta.get("away_team"),
            meta.get("tournament"),
            str(meta.get("start_time") or "")[:10],
            None,
            float(winner.get("home") or 0.0),
            float(winner.get("draw") or 0.0),
            float(winner.get("away") or 0.0),
            float(probabilities.get("btts") or 0.0),
            float(over25 or 0.0),
            float(home_expected.get("goals_for") or 0.0),
            float(away_expected.get("goals_for") or 0.0),
            float(totals.get("goals") or 0.0),
            actual_home,
            actual_away,
            actual.get("status"),
            actual_score,
            json.dumps(summary, ensure_ascii=False),
        )
        with self._write_lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO predictions (
                    match_id, created_at, model_version, iterations, seed, window,
                    home_name, away_name, tournament, day, start_timestamp,
                    prob_home, prob_draw, prob_away, btts, over25,
                    expected_home, expected_away, expected_goals,
                    actual_home, actual_away, actual_status, actual_score, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, iterations, seed, model_version) DO UPDATE SET
                    created_at=excluded.created_at,
                    prob_home=excluded.prob_home,
                    prob_draw=excluded.prob_draw,
                    prob_away=excluded.prob_away,
                    btts=excluded.btts,
                    over25=excluded.over25,
                    expected_home=excluded.expected_home,
                    expected_away=excluded.expected_away,
                    expected_goals=excluded.expected_goals,
                    actual_home=COALESCE(excluded.actual_home, predictions.actual_home),
                    actual_away=COALESCE(excluded.actual_away, predictions.actual_away),
                    actual_status=COALESCE(excluded.actual_status, predictions.actual_status),
                    actual_score=COALESCE(excluded.actual_score, predictions.actual_score),
                    payload=excluded.payload
                """,
                values,
            )
            row = connection.execute(
                "SELECT id FROM predictions WHERE match_id=? AND iterations=? "
                "AND seed=? AND model_version=?",
                (int(match_id), values[3], values[4], model_version),
            ).fetchone()
        return int(row["id"]) if row else None

    def latest_predictions(
        self, match_ids: Optional[Sequence[int]] = None
    ) -> Dict[int, Dict[str, Any]]:
        clauses = ""
        params: List[Any] = []
        if match_ids:
            placeholders = ",".join("?" for _ in match_ids)
            clauses = f"WHERE match_id IN ({placeholders})"
            params = [int(item) for item in match_ids]
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM predictions {clauses}
                ORDER BY created_at DESC, id DESC
                """,
                params,
            ).fetchall()
        result: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            item.pop("payload", None)
            result.setdefault(int(item["match_id"]), item)
        return result

    def list_predictions(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM predictions
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item.pop("payload", None)
            result.append(item)
        return result

    def latest_prediction_payload(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Resumen completo de la predicción más reciente de un partido."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM predictions
                WHERE match_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (int(match_id),),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload"] or "{}")
        except (TypeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    def accuracy(self) -> Dict[str, Any]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM predictions
                WHERE actual_home IS NOT NULL AND actual_away IS NOT NULL
                  AND actual_status = 'finished'
                """
            ).fetchall()
        total = 0
        correct = 0
        brier_sum = 0.0
        log_loss_sum = 0.0
        goal_error_sum = 0.0
        goal_count = 0
        by_tournament: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            total += 1
            probs = [
                float(row["prob_home"] or 0.0),
                float(row["prob_draw"] or 0.0),
                float(row["prob_away"] or 0.0),
            ]
            if max(probs) <= 0:
                total -= 1
                continue
            actual_side = _side_from_score(row["actual_score"])
            if actual_side is None:
                total -= 1
                continue
            actual_index = {"home": 0, "draw": 1, "away": 2}[actual_side]
            predicted_index = max(range(3), key=lambda index: probs[index])
            hit = predicted_index == actual_index
            correct += int(hit)
            brier_sum += sum(
                (probability - (1.0 if index == actual_index else 0.0)) ** 2
                for index, probability in enumerate(probs)
            )
            log_loss_sum += -math.log(max(1e-15, probs[actual_index]))
            actual_home = int(row["actual_home"])
            actual_away = int(row["actual_away"])
            expected_goals = float(row["expected_goals"] or 0.0)
            goal_error_sum += abs(expected_goals - (actual_home + actual_away))
            goal_count += 1
            tournament = str(row["tournament"] or "Sin competición")
            bucket = by_tournament.setdefault(
                tournament, {"total": 0, "correct": 0}
            )
            bucket["total"] += 1
            bucket["correct"] += int(hit)
        by_list = [
            {
                "tournament": name,
                "total": data["total"],
                "accuracy": data["correct"] / data["total"]
                if data["total"]
                else 0.0,
            }
            for name, data in sorted(
                by_tournament.items(), key=lambda item: (-item[1]["total"], item[0])
            )
        ]
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else 0.0,
            "brier": brier_sum / total if total else 0.0,
            "log_loss": log_loss_sum / total if total else 0.0,
            "goal_mae": goal_error_sum / goal_count if goal_count else 0.0,
            "by_tournament": by_list,
        }

    def count_predictions(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()
        return int(row["n"]) if row else 0

    def clear(self) -> None:
        with self._write_lock, self._connection() as connection:
            connection.execute("DELETE FROM analyses")
            connection.execute("DELETE FROM predictions")
            connection.execute("DELETE FROM matches")

    def recent_days(self, limit: int = 30) -> List[str]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT day FROM matches WHERE day IS NOT NULL AND day != ''
                ORDER BY day DESC LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [str(row["day"]) for row in rows]



