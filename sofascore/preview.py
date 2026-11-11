"""Generación de previas y reportes de partido.

No usa servicios externos: construye Markdown y HTML autocontenido a
partir del análisis y, opcionalmente, del resumen de simulación.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import normalize


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.{digits}f}".replace(".", ",")


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.1f} %".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _team_name(block: Dict[str, Any], fallback: str) -> str:
    return (block.get("team") or {}).get("name") or fallback


def _date_text(match: Dict[str, Any]) -> str:
    raw = match.get("start_time")
    if not raw:
        return ""
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return moment.strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(raw)


def build_preview(
    analysis: Dict[str, Any], summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Devuelve un diccionario con los datos y el texto de la previa."""
    match = analysis.get("match") or {}
    teams = analysis.get("teams") or {}
    home_block = teams.get("home") or {}
    away_block = teams.get("away") or {}
    home = _team_name(home_block, "Local")
    away = _team_name(away_block, "Visitante")
    tournament = (match.get("tournament") or {}).get("name") or "Competición"
    window = analysis.get("window")
    window_text = (
        "toda la temporada" if window == "all" else f"últimos {window} partidos"
    )
    actual = analysis.get("actual") or {}
    lineups = analysis.get("lineups") or {}
    referee = analysis.get("referee") or {}
    comparison = analysis.get("comparison") or []
    probabilities = (summary or {}).get("probabilities") or {}
    winner = probabilities.get("winner") or {}
    totals = (summary or {}).get("totals") or {}
    totals_mean = totals.get("mean") or {}
    over_under = probabilities.get("over_under") or {}
    over25 = (
        ((over_under.get("goals") or {}).get("2.5") or {}).get("over")
    )
    btts = probabilities.get("btts")

    lines: List[str] = []
    lines.append(f"# {home} vs {away}")
    lines.append("")
    lines.append(f"**{tournament}** · {_date_text(match)}")
    lines.append("")
    if actual.get("score"):
        actual_status = actual.get("status") or "finalizado"
        actual_status = {
            "finished": "finalizado",
            "live": "en vivo",
            "inprogress": "en vivo",
        }.get(actual_status, actual_status)
        lines.append(
            f"**Resultado real:** {actual.get('score')} "
            f"({actual_status})"
        )
        lines.append("")
    lines.append("## Forma reciente")
    lines.append("")
    for block in (home_block, away_block):
        name = _team_name(block, "Equipo")
        lines.append(
            f"- **{name}**: {block.get('sample_size', 0)} partidos "
            f"({block.get('stats_sample_size', 0)} con estadísticas), "
            f"forma **{block.get('form') or '—'}**."
        )
    lines.append("")
    lines.append(
        f"Ventana analizada: {window_text}. "
        "Los datos se obtienen de la API interna de SofaScore."
    )
    lines.append("")

    if comparison:
        lines.append("## Comparación")
        lines.append("")
        lines.append(f"| Métrica | {home} | {away} | Diferencia |")
        lines.append("| --- | ---: | ---: | ---: |")
        for row in comparison[:12]:
            lines.append(
                f"| {row.get('label') or '—'} | {_fmt(row.get('home'))} | "
                f"{_fmt(row.get('away'))} | {_fmt(row.get('difference'))} |"
            )
        lines.append("")

    if summary:
        lines.append("## Probabilidades simuladas")
        lines.append("")
        lines.append(
            f"- **Gana {home}:** {_pct(winner.get('home'))}"
        )
        lines.append(f"- **Empate:** {_pct(winner.get('draw'))}")
        lines.append(f"- **Gana {away}:** {_pct(winner.get('away'))}")
        lines.append(f"- **Ambos marcan:** {_pct(btts)}")
        lines.append(f"- **Más de 2,5 goles:** {_pct(over25)}")
        lines.append(f"- **Goles esperados:** {_fmt(totals_mean.get('goals'))}")
        lines.append(f"- **Córners esperados:** {_fmt(totals_mean.get('corners'))}")
        lines.append("")
        top_side = max(
            ("home", "draw", "away"),
            key=lambda side: float(winner.get(side) or 0.0),
        )
        top_name = {"home": home, "draw": "el empate", "away": away}[top_side]
        lines.append(
            f"El modelo sitúa a **{top_name}** como resultado más probable, "
            f"con un {_pct(winner.get(top_side))} de probabilidad."
        )
        lines.append("")
    else:
        lines.append(
            "## Probabilidades\n\nEjecuta la simulación Monte Carlo para "
            "incorporar probabilidades y marcadores esperados.\n"
        )

    if lineups:
        status = normalize.lineup_status(lineups)
        lines.append("## Alineaciones")
        lines.append("")
        lines.append(f"Estado: **{status}**.")
        for block, name in ((home_block, home), (away_block, away)):
            side = "home" if block is home_block else "away"
            lineup_side = lineups.get(side) or {}
            formation = lineup_side.get("formation")
            if formation:
                lines.append(f"- **{name}**: formación {formation}.")
        lines.append("")

    if referee.get("name"):
        lines.append("## Arbitraje")
        lines.append("")
        referee_line = f"Árbitro: **{referee['name']}**"
        cards = referee.get("cards_per_match")
        fouls = referee.get("fouls_per_match")
        if cards is not None:
            referee_line += f" · {_fmt(cards)} tarjetas/partido"
        if fouls is not None:
            referee_line += f" · {_fmt(fouls)} faltas/partido"
        lines.append(referee_line)
        lines.append("")

    lines.append("---")
    lines.append(
        "_Previa generada automáticamente a partir de datos de SofaScore. "
        "No es una predicción garantizada._"
    )
    return {
        "home": home,
        "away": away,
        "tournament": tournament,
        "markdown": "\n".join(lines).strip() + "\n",
    }


def _inline_html(text: str) -> str:
    """Escapa HTML y conserva negritas y cursivas sencillas."""
    rendered = html.escape(text)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", rendered)
    return rendered


def render_markdown(analysis: Dict[str, Any], summary: Optional[Dict[str, Any]] = None) -> str:
    return str(build_preview(analysis, summary)["markdown"])


def render_html(analysis: Dict[str, Any], summary: Optional[Dict[str, Any]] = None) -> str:
    preview = build_preview(analysis, summary)
    markdown = preview["markdown"]
    title = html.escape(f"{preview['home']} vs {preview['away']}")
    body: List[str] = []
    in_table = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line:
            if in_table:
                body.append("</tbody></table>")
                in_table = False
            body.append("")
            continue
        if line.startswith("# "):
            body.append(f"<h1>{_inline_html(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            if in_table:
                body.append("</tbody></table>")
                in_table = False
            body.append(f"<h2>{_inline_html(line[3:])}</h2>")
            continue
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                continue
            if not in_table:
                body.append("<table><thead>")
                body.append(
                    "<tr>" + "".join(f"<th>{_inline_html(c)}</th>" for c in cells) + "</tr>"
                )
                body.append("</thead><tbody>")
                in_table = True
            else:
                body.append(
                    "<tr>" + "".join(f"<td>{_inline_html(c)}</td>" for c in cells) + "</tr>"
                )
            continue
        if in_table:
            body.append("</tbody></table>")
            in_table = False
        if line.startswith("- "):
            body.append(f"<p class=\"bullet\">{_inline_html(line[2:])}</p>")
            continue
        body.append(f"<p>{_inline_html(line)}</p>")
    if in_table:
        body.append("</tbody></table>")
    content = "\n".join(body)
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Previa</title>
<style>
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       max-width: 900px; margin: 36px auto; padding: 0 20px;
       color: #1b1f24; line-height: 1.55; background: #f7f9fb; }}
main {{ background: #fff; padding: 34px 42px; border-radius: 14px;
        box-shadow: 0 10px 30px rgba(20, 40, 70, .08); }}
h1 {{ margin: 0 0 8px; font-size: 2rem; }}
h2 {{ margin-top: 28px; padding-top: 14px; border-top: 1px solid #e4e9ef;
      font-size: 1.15rem; color: #0a66c2; }}
p {{ margin: 8px 0; }}
.bullet {{ padding-left: 18px; position: relative; }}
.bullet::before {{ content: "•"; position: absolute; left: 2px; color: #0a66c2; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 18px;
         font-size: .92rem; }}
th {{ background: #eef4fc; color: #0a4f9e; text-align: left; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #e4e9ef; }}
td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
footer {{ color: #6a7480; font-size: .8rem; margin-top: 26px; }}
</style>
</head>
<body>
<main>
{content}
<footer>Generado el {generated} · SofaScore · Análisis de forma</footer>
</main>
</body>
</html>
"""
