/* ==========================================================================
   SofaScore · interfaz web local
   Vanilla JS, sin dependencias. Todo se sirve desde 127.0.0.1.
   ========================================================================== */

"use strict";

/* --------------------------------------------------------------------------
   Iconos
   -------------------------------------------------------------------------- */
const ICONS = {
  ball: '<circle cx="12" cy="12" r="9"/><path d="m12 7 3.1 2.25-1.18 3.64h-3.84L8.9 9.25 12 7Z"/><path d="M12 7V3.4M14.9 18.2l2.4 2.3M9.1 18.2l-2.4 2.3M4.1 9.6 1.5 8.3M19.9 9.6l2.6-1.3"/>',
  live: '<circle cx="12" cy="12" r="2.6" fill="currentColor" stroke="none"/><path d="M7.4 7.4a6.5 6.5 0 0 0 0 9.2M16.6 7.4a6.5 6.5 0 0 1 0 9.2M4.6 4.6a10.4 10.4 0 0 0 0 14.8M19.4 4.6a10.4 10.4 0 0 1 0 14.8"/>',
  notebook: '<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 3v18M12 8h4M12 12h4M12 16h2"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.8 8.2-2.2 5.4-5.4 2.2 2.2-5.4z"/>',
  brain: '<path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v.5A3.5 3.5 0 0 0 4.5 15 3.5 3.5 0 0 0 8 19.5h1.5M14.5 4.5A3.5 3.5 0 0 1 18 8v.5a3.5 3.5 0 0 1 1.5 6.5 3.5 3.5 0 0 1-3.5 4.5h-1.5"/><path d="M9.5 4.5V19.5M14.5 4.5V19.5M9.5 9h-2M14.5 9h2M9.5 15h-2M14.5 15h2"/>',
  moon: '<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.7 9a2.4 2.4 0 1 1 3.5 2.1c-.8.5-1.2 1-1.2 1.9"/><path d="M12 17h.01"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  "chevron-left": '<path d="m14.5 6-6 6 6 6"/>',
  "chevron-right": '<path d="m9.5 6 6 6-6 6"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  refresh: '<path d="M20 11a8 8 0 1 0 .5 4"/><path d="M20 4v7h-7"/>',
  sliders: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="7" cy="17" r="2"/>',
  filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
  star: '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z"/>',
  "star-filled": '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z" fill="currentColor"/>',
  check: '<path d="m5 12 4.5 4.5L19 7"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  api: '<path d="M8 9 4 12l4 3M16 9l4 3-4 3M13.5 6l-3 12"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  play: '<path d="m8 5 11 7-11 7z"/>',
  x: '<path d="m6 6 12 12M18 6 6 18"/>',
  alert: '<path d="M10.3 3.7 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 6H4v2a4 4 0 0 0 4 4M16 6h4v2a4 4 0 0 1-4 4M12 13v5M8 21h8M9 18h6"/>',
  shield: '<path d="M12 3 4.5 6v5c0 4.6 3.2 8.6 7.5 10 4.3-1.4 7.5-5.4 7.5-10V6z"/>',
  "arrow-left": '<path d="M20 12H4M10 6l-6 6 6 6"/>',
  "arrow-right": '<path d="M4 12h16M14 6l6 6-6 6"/>',
  zap: '<path d="M13 2 3 14h7l-1 8 10-12h-7z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.6"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18h1.5a2.2 2.2 0 0 0 0-4.4H12a1.8 1.8 0 0 1 0-3.6h4.2A4.8 4.8 0 0 0 21 8.2 5.2 5.2 0 0 0 15.8 3Z"/><circle cx="7.5" cy="10.5" r="1" fill="currentColor" stroke="none"/><circle cx="10" cy="7.2" r="1" fill="currentColor" stroke="none"/><circle cx="14.2" cy="6.8" r="1" fill="currentColor" stroke="none"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  sparkles: '<path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4zM19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8zM5 14l.6 1.7 1.7.6-1.7.6L5 18.6l-.6-1.7-1.7-.6 1.7-.6z"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2z"/><path d="M4 17h15M8 7h7M8 11h5"/>',
  whistle: '<path d="M4 12a5 5 0 0 0 5 5h4l6 3v-6a5 5 0 0 0-5-5H9a5 5 0 0 0-5 3Z"/><path d="M9 8V5M13 8V4"/>',
  percent: '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  "rotate-ccw": '<path d="M3 4v6h6"/><path d="M3.5 15a9 9 0 1 0 2-9.4L3 10"/>',
};

function icon(name, className = "") {
  const body = ICONS[name] || ICONS.ball;
  return `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((element) => {
    if (!element.querySelector("svg")) {
      element.innerHTML = icon(element.dataset.icon);
    }
  });
}

/* --------------------------------------------------------------------------
   Temas
   -------------------------------------------------------------------------- */
const THEMES = [
  {
    key: "light",
    label: "Claro",
    description: "Limpio, luminoso y azul.",
    dark: false,
    preview: ["#f2f5fb", "#ffffff", "#2563eb"],
  },
  {
    key: "dark",
    label: "Oscuro",
    description: "Azul noche, suave y familiar.",
    dark: true,
    preview: ["#070d19", "#111b2e", "#60a5fa"],
  },
  {
    key: "midnight",
    label: "Medianoche",
    description: "Índigo profundo con cian.",
    dark: true,
    preview: ["#070a18", "#121830", "#818cf8"],
  },
  {
    key: "forest",
    label: "Bosque",
    description: "Verde profundo y menta.",
    dark: true,
    preview: ["#06120e", "#0f241b", "#34d399"],
  },
  {
    key: "ocean",
    label: "Océano",
    description: "Turquesa fresco y luminoso.",
    dark: false,
    preview: ["#eef8fb", "#ffffff", "#0e7490"],
  },
  {
    key: "sunset",
    label: "Atardecer",
    description: "Crema cálida, coral y ámbar.",
    dark: false,
    preview: ["#fdf3ea", "#fffaf5", "#c2410c"],
  },
  {
    key: "contrast",
    label: "Alto contraste",
    description: "Negro, blanco y amarillo.",
    dark: true,
    preview: ["#000000", "#0a0a0a", "#facc15"],
  },
];

function themeDefinition(key) {
  return THEMES.find((theme) => theme.key === key) || THEMES[0];
}

/* --------------------------------------------------------------------------
   Estado
   -------------------------------------------------------------------------- */
const state = {
  boot: null,
  prefs: {},
  theme: "light",
  favorites: {},
  timezone: "local",
  region: "ambas",
  competitions: "principales",
  date: "",
  matches: [],
  matchesById: new Map(),
  liveExtras: {},
  selectedId: null,
  selectedMatch: null,
  analysis: null,
  analysisWindow: 10,
  analysisJob: null,
  analysisToken: 0,
  simulation: null,
  simJob: null,
  simToken: 0,
  simMetric: "goals",
  simMarket: "goals",
  advice: null,
  detailTab: "overview",
  detailOpen: false,
  loadingDay: false,
  loadingRest: false,
  dayToken: 0,
  listScroll: 0,
  league: "all",
  status: "all",
  query: "",
  activeView: "matches",
  liveFilter: "live",
  liveLoading: false,
  lastLiveAt: 0,
  lastScores: {},
  predictions: [],
  accuracy: {},
  latestPredictions: {},
  journalLoaded: false,
  explorerLoaded: false,
  explorerMatches: [],
  explorerQuery: "",
  explorerStatus: "",
  preview: null,
  model: null,
  settingsNeedsReload: false,
  busy: 0,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

/* --------------------------------------------------------------------------
   Utilidades
   -------------------------------------------------------------------------- */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function normalizeText(value) {
  return String(value ?? "")
    .toLocaleLowerCase("es")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return number.toLocaleString("es-ES", {
    maximumFractionDigits: digits,
    minimumFractionDigits: Number.isInteger(number) ? 0 : Math.min(digits, 2),
  });
}

function fmtInt(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return Math.round(number).toLocaleString("es-ES");
}

function pct(value, digits = 0) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${(number * 100).toLocaleString("es-ES", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}%`;
}

function signed(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${number > 0 ? "+" : ""}${fmt(number, digits)}`;
}

function shortName(name, limit = 22) {
  const text = String(name || "Equipo");
  return text.length <= limit ? text : `${text.slice(0, Math.max(1, limit - 1))}…`;
}

function initials(team) {
  const raw = String(team?.short_name || team?.name || team?.code || "?");
  return raw
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function fallbackCrest(label) {
  const safe = esc(label || "?").replace(/[<>]/g, "");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" rx="16" fill="#e8eef8"/><text x="16" y="20" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="10" font-weight="700" fill="#63738b">${safe}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function crest(team, className = "crest") {
  const label = initials(team);
  if (!team || team.id === null || team.id === undefined) {
    return `<span class="crest-fallback">${esc(label)}</span>`;
  }
  const fallback = fallbackCrest(label);
  return `<img class="${className}" src="/api/image?kind=team&id=${encodeURIComponent(team.id)}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${fallback}'">`;
}

function flag(categoryId, name = "") {
  if (!categoryId) {
    return `<span class="league-flag" title="${esc(name)}"></span>`;
  }
  return `<img class="league-flag" src="/api/image?kind=category&id=${encodeURIComponent(categoryId)}" alt="" loading="lazy" title="${esc(name)}" onerror="this.style.visibility='hidden'">`;
}

function teamName(team) {
  return String(team?.short_name || team?.name || "Equipo");
}

function teamFullName(team) {
  return String(team?.name || team?.short_name || "Equipo");
}

function isLive(match) {
  return ["inprogress", "live", "halftime"].includes(match?.status_type);
}

function isFinished(match) {
  return match?.status_type === "finished";
}

function isUpcoming(match) {
  return !isLive(match) && !isFinished(match);
}

function statusRank(match) {
  if (isLive(match)) return 0;
  if (isFinished(match)) return 2;
  return 1;
}

function tzOptions() {
  return state.timezone && state.timezone !== "local"
    ? { timeZone: state.timezone }
    : {};
}

function formatTime(timestamp) {
  if (timestamp === null || timestamp === undefined) return "—";
  try {
    return new Intl.DateTimeFormat("es-ES", {
      hour: "2-digit",
      minute: "2-digit",
      ...tzOptions(),
    }).format(new Date(Number(timestamp) * 1000));
  } catch {
    return "—";
  }
}

function formatDateTime(timestamp) {
  if (timestamp === null || timestamp === undefined) return "—";
  try {
    return new Intl.DateTimeFormat("es-ES", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      ...tzOptions(),
    }).format(new Date(Number(timestamp) * 1000));
  } catch {
    return "—";
  }
}

function formatDate(isoDate) {
  if (!isoDate) return "—";
  try {
    const date = new Date(`${String(isoDate).slice(0, 10)}T12:00:00`);
    return new Intl.DateTimeFormat("es-ES", {
      weekday: "short",
      day: "2-digit",
      month: "short",
    }).format(date);
  } catch {
    return String(isoDate);
  }
}

function formatLongDate(isoDate) {
  if (!isoDate) return "";
  try {
    const date = new Date(`${String(isoDate).slice(0, 10)}T12:00:00`);
    return new Intl.DateTimeFormat("es-ES", {
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(date);
  } catch {
    return String(isoDate);
  }
}

function dayKeyFromDate(isoDate) {
  const date = new Date(`${isoDate}T12:00:00`);
  date.setDate(date.getDate());
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function shiftDate(isoDate, days) {
  const date = new Date(`${isoDate}T12:00:00`);
  date.setDate(date.getDate() + days);
  return dayKeyFromDate(date.toISOString().slice(0, 10));
}

function matchDay(match) {
  if (!match) return "";
  if (match.start_time_local) return String(match.start_time_local).slice(0, 10);
  if (match.start_timestamp === null || match.start_timestamp === undefined) {
    return "";
  }
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      ...tzOptions(),
    }).formatToParts(new Date(Number(match.start_timestamp) * 1000));
    const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${lookup.year}-${lookup.month}-${lookup.day}`;
  } catch {
    return "";
  }
}

function scoreText(match) {
  if (!match) return "—";
  if (!isLive(match) && !isFinished(match)) return "VS";
  if (match.home_score === null || match.home_score === undefined) {
    return isFinished(match) ? "Final" : "—";
  }
  if (match.away_score === null || match.away_score === undefined) {
    return isFinished(match) ? "Final" : "—";
  }
  return `${match.home_score} - ${match.away_score}`;
}

function scoreShort(match) {
  if (
    match?.home_score === null ||
    match?.home_score === undefined ||
    match?.away_score === null ||
    match?.away_score === undefined
  ) {
    return "—";
  }
  return `${match.home_score}-${match.away_score}`;
}

function statusInfo(match) {
  if (!match) return { label: "—", short: "—", className: "" };
  if (isLive(match)) {
    const minute = Number(match.minute || match.status_time?.initial || 0);
    const halftime = match.status_type === "halftime" || match.status === "Halftime";
    const label = halftime
      ? "Descanso"
      : minute > 0
        ? `En vivo · ${Math.round(minute)}'`
        : "En vivo";
    return {
      label,
      short: halftime ? "Desc." : minute > 0 ? `${Math.round(minute)}'` : "Vivo",
      className: "live",
    };
  }
  if (isFinished(match)) {
    return { label: "Finalizado", short: "Final", className: "finished" };
  }
  if (match.status_type === "delayed") {
    return { label: "Aplazado", short: "Apl.", className: "upcoming" };
  }
  return {
    label: "Próximo",
    short: formatTime(match.start_timestamp),
    className: "upcoming",
  };
}

function matchTimeLabel(match) {
  if (isLive(match)) {
    const minute = Math.round(Number(match.minute || 0));
    return minute > 0 ? `${minute}'` : "Vivo";
  }
  if (isFinished(match)) return "Final";
  if (match.status_type === "delayed") return "Apl.";
  return formatTime(match.start_timestamp);
}

function teamMatchesFavorite(match, favorites = state.favorites) {
  return [match?.home_team, match?.away_team].some(
    (team) => team && favorites[String(team.id)] !== undefined,
  );
}

function favoriteName(match) {
  for (const team of [match?.home_team, match?.away_team]) {
    if (team && state.favorites[String(team.id)] !== undefined) {
      return state.favorites[String(team.id)] || teamName(team);
    }
  }
  return null;
}

function winnerSide(match) {
  if (!isFinished(match)) return null;
  const home = Number(match.home_score);
  const away = Number(match.away_score);
  if (!Number.isFinite(home) || !Number.isFinite(away)) return null;
  if (home > away) return "home";
  if (away > home) return "away";
  return "draw";
}

function mergeMatches(base, extra) {
  const map = new Map();
  base.forEach((match) => map.set(match.id, { ...match }));
  extra.forEach((match) => {
    map.set(match.id, { ...(map.get(match.id) || {}), ...match });
  });
  return Array.from(map.values());
}

function allLiveMatches() {
  const combined = mergeMatches(state.matches, Object.values(state.liveExtras || {}));
  return combined.filter(isLive);
}

function debounce(fn, delay = 250) {
  let timeout = null;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "descarga";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2500);
}

async function downloadFrom(path, fallbackName) {
  const response = await fetch(path);
  if (!response.ok) {
    let message = `No se pudo descargar (${response.status}).`;
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = /filename="([^"]+)"/i.exec(disposition);
  downloadBlob(blob, match ? match[1] : fallbackName);
}

/* --------------------------------------------------------------------------
   API
   -------------------------------------------------------------------------- */
async function api(path, options = {}) {
  const request = { ...options };
  request.headers = { ...(options.headers || {}) };
  if (request.body && typeof request.body !== "string") {
    request.body = JSON.stringify(request.body);
    request.headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { cache: "no-store", ...request });
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }
  if (!response.ok) {
    const message =
      (payload && (payload.error || payload.detail)) ||
      `Error ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

/* --------------------------------------------------------------------------
   Estado visual y avisos
   -------------------------------------------------------------------------- */
function updateControlStates() {
  $$("#statusChips .chip").forEach((chip) => {
    const key = chip.dataset.status;
    const active = key === "all" ? state.status === "all" : state.status === key;
    chip.classList.toggle("is-active", active);
    chip.setAttribute("aria-pressed", String(active));
  });
  $$("#liveFilters button").forEach((button) => {
    const active = state.liveFilter === button.dataset.liveFilter;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function setStatus(message, kind = "ok") {
  const text = $("#statusText");
  const dot = $("#statusDot");
  if (text) text.textContent = message;
  if (dot) {
    dot.className = "status-dot";
    if (kind === "busy") dot.classList.add("busy");
    if (kind === "error") dot.classList.add("error");
  }
}

function setBusy(delta) {
  state.busy = Math.max(0, state.busy + delta);
  if (state.busy > 0) setStatus("Trabajando…", "busy");
}

function setDetailBusy(busy) {
  $("#detailPane")?.setAttribute("aria-busy", String(Boolean(busy)));
}

function setMatchListBusy(busy) {
  $("#matchList")?.setAttribute("aria-busy", String(Boolean(busy)));
}

function toast(title, message = "", kind = "info", timeout = 4600) {
  const root = $("#toastRoot");
  if (!root) return;
  const element = document.createElement("div");
  element.className = `toast ${kind}`;
  const iconName =
    kind === "success" ? "check" : kind === "error" ? "alert" : kind === "warn" ? "alert" : "info";  element.innerHTML = `
    <span class="toast-icon">${icon(iconName)}</span>
    <div class="toast-copy"><strong>${esc(title)}</strong>${message ? `<p>${esc(message)}</p>` : ""}</div>
    <button class="toast-close" type="button" aria-label="Cerrar">${icon("x")}</button>
  `;
  root.appendChild(element);
  const close = () => {
    if (!element.isConnected) return;
    element.classList.add("is-leaving");
    setTimeout(() => element.remove(), 220);
  };
  element.querySelector(".toast-close").addEventListener("click", close);
  setTimeout(close, timeout);
}

function setTheme(theme, persist = true) {
  if (typeof theme === "boolean") theme = theme ? "dark" : "light";
  const definition = themeDefinition(theme);
  document.documentElement.dataset.theme = definition.key;
  document.documentElement.dataset.mode = definition.dark ? "dark" : "light";
  document.documentElement.style.colorScheme = definition.dark ? "dark" : "light";
  state.theme = definition.key;
  state.prefs.theme = definition.key;
  state.prefs.dark = definition.dark;
  const button = $("#themeToggle");
  if (button) {
    button.innerHTML = `${icon("palette")}<span class="theme-label">Tema: ${esc(definition.label)}</span>`;
    button.title = `Tema actual: ${definition.label}. Pulsa para cambiar.`;
    button.setAttribute("aria-label", `Tema actual: ${definition.label}. Cambiar tema`);
  }
  if (persist) {
    api("/api/preferences", {
      method: "POST",
      body: { theme: definition.key, dark: definition.dark },
    }).catch(() => {});
  }
}

function cycleTheme() {
  const index = THEMES.findIndex((theme) => theme.key === state.theme);
  const next = THEMES[(index + 1) % THEMES.length];
  setTheme(next.key);
  toast("Tema aplicado", next.label, "info", 1800);
}

function renderThemeCards(selected) {
  return THEMES.map(
    (theme) => `<button class="theme-card ${theme.key === selected ? "is-active" : ""}" type="button" data-theme-key="${esc(theme.key)}" aria-pressed="${theme.key === selected}">
      <span class="theme-swatch" style="background:${theme.preview[0]}">
        <span style="background:${theme.preview[1]}"></span>
        <span style="background:${theme.preview[2]}"></span>
      </span>
      <span class="theme-copy"><strong>${esc(theme.label)}</strong><small>${esc(theme.description)}</small></span>
      <span class="theme-check">${icon("check")}</span>
    </button>`,
  ).join("");
}

function bindThemeCards(root) {
  root.querySelectorAll("[data-theme-key]").forEach((card) => {
    card.addEventListener("click", () => {
      const key = card.dataset.themeKey;
      setTheme(key);
      root.querySelectorAll("[data-theme-key]").forEach((other) => {
        const active = other === card;
        other.classList.toggle("is-active", active);
        other.setAttribute("aria-pressed", String(active));
      });
      toast("Tema aplicado", themeDefinition(key).label, "info", 1800);
    });
  });
}

function openThemePicker() {
  const modal = openModal({
    title: "Temas",
    subtitle: "Elige el estilo visual. El cambio se aplica al instante y se guarda.",
    body: `<div class="theme-grid" id="themePickerGrid">${renderThemeCards(state.theme)}</div>
      <div class="theme-preview-note">${icon("info")}<span>Los temas también ajustan los gráficos, las tarjetas, los escudos y el contraste del texto. Puedes cambiar con <strong>Ctrl + D</strong>.</span></div>`,
    footer: `<button class="primary-button" type="button" data-close-modal>Listo</button>`,
  });
  bindThemeCards($("#themePickerGrid", modal));
}

/* --------------------------------------------------------------------------
   Modales
   -------------------------------------------------------------------------- */
const MODAL_FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

let lastFocusedElement = null;

function modalFocusable(modal) {
  return Array.from(modal.querySelectorAll(MODAL_FOCUSABLE)).filter(
    (element) =>
      element.getClientRects().length > 0 &&
      getComputedStyle(element).visibility !== "hidden",
  );
}

function openModal({ title, subtitle = "", body = "", footer = "", wide = false, flush = false }) {
  const root = $("#modalRoot");
  const wasOpen = !root.hidden;
  if (!wasOpen) {
    lastFocusedElement =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const shell = $(".app-shell");
    if (shell) {
      shell.setAttribute("inert", "");
      shell.setAttribute("aria-hidden", "true");
    }
  }
  root.hidden = false;
  root.innerHTML = `
    <div class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-label="${esc(title)}" tabindex="-1">
      <div class="modal-head">
        <div>
          <h2>${esc(title)}</h2>
          ${subtitle ? `<p>${esc(subtitle)}</p>` : ""}
        </div>
        <button class="icon-button modal-close" type="button" data-close-modal aria-label="Cerrar">${icon("x")}</button>
      </div>
      <div class="modal-body ${flush ? "flush" : ""}">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>
  `;
  const modal = $(".modal", root);
  root.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  const focusFirst = () => {
    if (!root.contains(modal)) return;
    const focusable = modalFocusable(modal);
    (focusable[0] || modal).focus();
  };
  focusFirst();
  setTimeout(focusFirst, 0);
  return modal;
}

function closeModal() {
  const root = $("#modalRoot");
  if (!root) return;
  root.hidden = true;
  root.innerHTML = "";
  const shell = $(".app-shell");
  if (shell) {
    shell.removeAttribute("inert");
    shell.removeAttribute("aria-hidden");
  }
  if (lastFocusedElement?.isConnected) {
    lastFocusedElement.focus();
  }
  lastFocusedElement = null;
  if (state.settingsNeedsReload) {
    state.settingsNeedsReload = false;
    loadDay({ refresh: true }).catch(() => {});
  }
}

function setSidebarOpen(open) {
  const sidebar = $("#sidebar");
  const backdrop = $("#sidebarBackdrop");
  const button = $("#menuToggle");
  if (!sidebar) return;
  sidebar.classList.toggle("is-open", open);
  if (backdrop) backdrop.hidden = !open;
  button?.setAttribute("aria-expanded", String(open));
  if (!open && window.innerWidth <= 820 && sidebar.contains(document.activeElement)) {
    button?.focus();
  }
}

/* --------------------------------------------------------------------------
   Arranque
   -------------------------------------------------------------------------- */
async function boot() {
  hydrateIcons();
  bindEvents();
  try {
    const data = await api("/api/bootstrap");
    state.boot = data;
    state.prefs = { ...(data.preferences || {}) };
    state.favorites = { ...(state.prefs.favorites || {}) };
    state.timezone = state.prefs.timezone || "local";
    state.region = state.prefs.region || "ambas";
    state.competitions = state.prefs.competitions || "principales";
    state.date = data.today;
    state.model = data.model;
    state.lastScores = safeParse(localStorage.getItem("sofascore:lastScores"), {});
    const storedTheme = state.prefs.theme;
    const initialTheme =
      THEMES.some((theme) => theme.key === storedTheme)
        ? storedTheme
        : state.prefs.dark
          ? "dark"
          : "light";
    setTheme(initialTheme, false);
    const version = $("#brandVersion");
    if (version) version.textContent = `v${data.version}`;
    const dateInput = $("#dateInput");
    if (dateInput) dateInput.value = state.date;
    buildStaticSelects();
    updateDayCaption();
    updateModelMini();
    updateStatusMeta();
    setView("matches", { silent: true });
    await loadDay();
    startLiveLoop();
    setStatus("Listo. Datos de SofaScore cargados.");
  } catch (error) {
    console.error(error);
    setStatus("No se pudo iniciar la interfaz.", "error");
    openModal({
      title: "No se pudo iniciar",
      subtitle: "La interfaz web no pudo conectar con el servidor local.",
      body: `<div class="warning-box">${icon("alert")}<div>${esc(error.message || String(error))}</div></div><p class="page-subtitle">Cierra la aplicación y vuelve a abrirla. Si el problema continúa, revisa que el puerto 8765 esté libre.</p>`,
      footer: `<button class="primary-button" type="button" data-close-modal>Cerrar</button>`,
    });
  }
}

function safeParse(text, fallback) {
  try {
    const value = JSON.parse(text);
    return value && typeof value === "object" ? value : fallback;
  } catch {
    return fallback;
  }
}

function buildStaticSelects() {
  const boot = state.boot || {};
  const regionSelect = $("#regionSelect");
  if (regionSelect) {
    regionSelect.innerHTML = (boot.regions || [])
      .map(
        (item) =>
          `<option value="${esc(item.key)}">${esc(item.label)}</option>`,
      )
      .join("");
    regionSelect.value = state.region;
  }
  const competitionSelect = $("#competitionSelect");
  if (competitionSelect) {
    competitionSelect.innerHTML = (boot.competitions || [])
      .map(
        (item) =>
          `<option value="${esc(item.key)}">${esc(item.label)}</option>`,
      )
      .join("");
    competitionSelect.value = state.competitions;
  }
  renderLeagueOptions();
}

function updateDayCaption() {
  const caption = $("#dayCaption");
  if (caption) {
    const label = formatLongDate(state.date);
    caption.textContent = label.charAt(0).toUpperCase() + label.slice(1);
  }
}

function updateModelMini() {
  const model = state.model || state.boot?.model;
  if (!model) return;
  const version = $("#sidebarModelVersion");
  if (version) version.textContent = `v${String(model.version || "—").split(":")[0]}`;
  const targets = model.targets || [];
  const goals = targets.filter((target) => target.key.includes("goals"));
  const values = goals
    .map((target) => Number(target.neural))
    .filter((value) => Number.isFinite(value));
  const mae = $("#sidebarModelMae");
  if (mae) {
    mae.textContent = values.length
      ? fmt(values.reduce((sum, value) => sum + value, 0) / values.length, 2)
      : "—";
  }
}

function updateStatusMeta() {
  const model = state.model || state.boot?.model;
  const storage = state.boot?.storage;
  const parts = [];
  if (model?.version) parts.push(`Modelo ${String(model.version).split(":")[0]}`);
  if (storage?.path) parts.push(storage.path);
  const meta = $("#statusMeta");
  if (meta) meta.textContent = parts.join(" · ");
}

/* --------------------------------------------------------------------------
   Carga de la jornada
   -------------------------------------------------------------------------- */
async function loadDay({ refresh = false } = {}) {
  if (!state.date) return;
  const token = ++state.dayToken;
  state.analysisToken += 1;
  state.simToken += 1;
  state.loadingDay = true;
  setMatchListBusy(true);
  state.loadingRest = false;
  state.matches = [];
  state.matchesById = new Map();
  state.liveExtras = {};
  state.selectedId = null;
  state.selectedMatch = null;
  state.analysis = null;
  state.analysisJob = null;
  state.simulation = null;
  state.simJob = null;
  state.preview = null;
  state.detailOpen = false;
  $("#view-matches")?.classList.remove("detail-open");
  state.listScroll = 0;
  renderDetail();
  renderMatchesSkeleton();
  const loadingLine = $("#loadingLine");
  if (loadingLine) loadingLine.hidden = false;
  const restBanner = $("#restBanner");
  if (restBanner) restBanner.hidden = true;
  setStatus(`Cargando partidos del ${state.date}…`, "busy");

  const params = new URLSearchParams({
    date: state.date,
    region: state.region,
    competitions: state.competitions,
    timezone: state.timezone,
    stage: "initial",
  });
  if (refresh) params.set("refresh", "1");

  try {
    const data = await api(`/api/day?${params.toString()}`);
    if (token !== state.dayToken) return;
    state.matches = data.matches || [];
    state.matchesById = new Map(state.matches.map((match) => [match.id, match]));
    renderLeagueOptions();
    renderMatches();
    const count = state.matches.length;
    setStatus(
      count
        ? `${count} partido${count === 1 ? "" : "s"} cargado${count === 1 ? "" : "s"}.`
        : "No hay partidos para esta fecha.",
    );
  } catch (error) {
    if (token !== state.dayToken) return;
    state.loadingDay = false;
    setMatchListBusy(false);
    setStatus("Error al cargar la fecha.", "error");
    toast("No se pudo cargar la fecha", error.message, "error");
    renderMatchesError(error.message);
    return;
  } finally {
    if (token === state.dayToken) {
      state.loadingDay = false;
      setMatchListBusy(false);
      if (loadingLine) loadingLine.hidden = true;
    }
  }

  state.loadingRest = true;
  setMatchListBusy(true);
  const restBanner2 = $("#restBanner");
  if (restBanner2) restBanner2.hidden = false;
  try {
    const restParams = new URLSearchParams({
      date: state.date,
      region: state.region,
      competitions: state.competitions,
      timezone: state.timezone,
      stage: "rest",
    });
    if (refresh) restParams.set("refresh", "1");
    const rest = await api(`/api/day?${restParams.toString()}`);
    if (token !== state.dayToken) return;
    const merged = mergeMatches(state.matches, rest.matches || []);
    const before = state.matches.length;
    state.matches = merged;
    state.matchesById = new Map(state.matches.map((match) => [match.id, match]));
    renderLeagueOptions();
    renderMatches();
    if (state.matches.length > before) {
      setStatus(
        `${state.matches.length} partidos cargados (${state.matches.length - before} del resto de competiciones).`,
      );
    }
  } catch (error) {
    if (token === state.dayToken) {
      console.warn("No se pudo cargar el resto:", error);
    }
  } finally {
    if (token === state.dayToken) {
      state.loadingRest = false;
      setMatchListBusy(false);
      const banner = $("#restBanner");
      if (banner) banner.hidden = true;
      renderMatches();
    }
  }
}

function renderMatchesSkeleton() {
  const list = $("#matchList");
  if (!list) return;
  const row = `
    <div class="skeleton-row">
      <div class="skeleton w60"></div>
      <div>
        <div class="skeleton w60" style="margin-bottom:6px"></div>
        <div class="skeleton w40"></div>
      </div>
      <div class="skeleton" style="height:20px"></div>
    </div>`;
  list.innerHTML = `<div class="match-group"><div class="match-group-head"><div class="skeleton" style="width:110px"></div></div>${row.repeat(6)}</div>`;
  const empty = $("#listEmpty");
  if (empty) empty.hidden = true;
}

function renderMatchesError(message) {
  const list = $("#matchList");
  if (list) list.innerHTML = "";
  const empty = $("#listEmpty");
  if (!empty) return;
  empty.hidden = false;
  const title = empty.querySelector("h2");
  const text = empty.querySelector("p");
  if (title) title.textContent = "No se pudo cargar la fecha";
  if (text) text.textContent = message || "Revisa la conexión e inténtalo de nuevo.";
}

/* --------------------------------------------------------------------------
   Lista de partidos
   -------------------------------------------------------------------------- */
function filteredMatches() {
  let matches = state.matches.slice();
  if (state.league === "top5") {
    matches = matches.filter((match) => match.section === "top");
  } else if (state.league === "other") {
    matches = matches.filter((match) => match.section === "other");
  } else if (state.league === "south") {
    matches = matches.filter((match) => match.section === "south");
  } else if (state.league.startsWith("league:")) {
    const id = state.league.slice(7);
    matches = matches.filter(
      (match) => String(match.league_id) === String(id),
    );
  }
  if (state.status === "favorites") {
    matches = matches.filter((match) => teamMatchesFavorite(match));
  } else if (state.status === "live") {
    matches = matches.filter(isLive);
  } else if (state.status === "upcoming") {
    matches = matches.filter(isUpcoming);
  } else if (state.status === "finished") {
    matches = matches.filter(isFinished);
  }
  const query = normalizeText(state.query);
  if (query) {
    matches = matches.filter((match) =>
      normalizeText(
        [
          match.home_team?.name,
          match.home_team?.short_name,
          match.away_team?.name,
          match.away_team?.short_name,
          match.tournament?.name,
          match.tournament?.category,
          scoreShort(match),
        ].join(" "),
      ).includes(query),
    );
  }
  return matches;
}

function groupedMatches(matches) {
  const groups = { top: [], other: [], south: [] };
  matches.forEach((match) => {
    const section = match.section || "other";
    (groups[section] || groups.other).push(match);
  });
  const leagueName = (match) =>
    normalizeText(match.tournament?.name || match.tournament?.category || "");
  groups.top.sort(
    (a, b) =>
      statusRank(a) - statusRank(b) ||
      (a.top_index ?? 9) - (b.top_index ?? 9) ||
      (a.start_timestamp || 0) - (b.start_timestamp || 0) ||
      leagueName(a).localeCompare(leagueName(b), "es"),
  );
  ["other", "south"].forEach((key) => {
    groups[key].sort(
      (a, b) =>
        statusRank(a) - statusRank(b) ||
        leagueName(a).localeCompare(leagueName(b), "es") ||
        (a.start_timestamp || 0) - (b.start_timestamp || 0),
    );
  });
  return ["top", "other", "south"]
    .filter((key) => groups[key].length)
    .map((key) => [key, groups[key]]);
}

function renderLeagueOptions() {
  const select = $("#leagueSelect");
  if (!select) return;
  const leagues = new Map();
  state.matches.forEach((match) => {
    const id = match.league_id;
    if (id === null || id === undefined) return;
    if (!leagues.has(String(id))) {
      leagues.set(String(id), {
        id: String(id),
        name: match.tournament?.name || "Competición",
        section: match.section || "other",
      });
    }
  });
  const options = [];
  options.push(`<option value="all">Todas las competiciones</option>`);
  options.push(
    `<optgroup label="Destacadas">
      <option value="top5">Top 5 · Ligas principales</option>
      <option value="other">Otras competiciones</option>
      <option value="south">Sudamérica</option>
    </optgroup>`,
  );
  const top = Array.from(leagues.values())
    .filter((league) => league.section === "top")
    .sort((a, b) => a.name.localeCompare(b.name, "es"));
  const other = Array.from(leagues.values())
    .filter((league) => league.section !== "top")
    .sort((a, b) => a.name.localeCompare(b.name, "es"));
  if (top.length) {
    options.push(
      `<optgroup label="Top 5">${top
        .map(
          (league) =>
            `<option value="league:${esc(league.id)}">${esc(league.name)}</option>`,
        )
        .join("")}</optgroup>`,
    );
  }
  if (other.length) {
    options.push(
      `<optgroup label="Resto">${other
        .map(
          (league) =>
            `<option value="league:${esc(league.id)}">${esc(league.name)}</option>`,
        )
        .join("")}</optgroup>`,
    );
  }
  select.innerHTML = options.join("");
  const available = new Set(["all", "top5", "other", "south"]);
  leagues.forEach((league) => available.add(`league:${league.id}`));
  select.value = available.has(state.league) ? state.league : "all";
  if (select.value !== state.league) state.league = "all";
}

function renderMatches() {
  const list = $("#matchList");
  if (!list) return;
  const previousScroll = list.scrollTop || state.listScroll || 0;
  const matches = filteredMatches();
  const grouped = groupedMatches(matches);
  const liveCount = allLiveMatches().length;
  const dateLiveCount = state.matches.filter(isLive).length;
  const favoritesCount = state.matches.filter((match) => teamMatchesFavorite(match)).length;

  $("#navMatchCount").textContent = state.matches.length ? String(state.matches.length) : "—";
  const navMatches = document.querySelector('.nav-item[data-view="matches"]');
  navMatches?.setAttribute(
    "aria-label",
    state.matches.length
      ? `Partidos, ${state.matches.length} partidos cargados`
      : "Partidos",
  );
  const navLive = document.querySelector('.nav-item[data-view="live"]');
  navLive?.setAttribute(
    "aria-label",
    liveCount
      ? `Sala de directo, ${liveCount} partido${liveCount === 1 ? "" : "s"} en vivo`
      : "Sala de directo",
  );
  const navDot = $("#navLiveDot");
  if (navDot) navDot.hidden = liveCount === 0;
  const livePill = $("#livePill");
  if (livePill) {
    livePill.classList.toggle("is-idle", liveCount === 0);
    const text = $("#livePillText");
    if (text) text.textContent = liveCount ? `${liveCount} en vivo` : "En vivo";
    livePill.setAttribute(
      "aria-label",
      liveCount
        ? `${liveCount} partido${liveCount === 1 ? "" : "s"} en vivo. Abrir sala de directo`
        : "No hay partidos en vivo. Abrir sala de directo",
    );
  }
  const count = $("#matchesCount");
  if (count) {
    const total = state.matches.length;
    const bits = [];
    if (state.league !== "all") bits.push($("#leagueSelect")?.selectedOptions[0]?.textContent || "Liga");
    if (state.status !== "all") {
      bits.push(
        {
          all: "Todos",
          live: "En vivo",
          upcoming: "Próximos",
          finished: "Finalizados",
          favorites: "Favoritos",
        }[state.status] || state.status,
      );
    }
    if (state.query) bits.push(`«${state.query}»`);
    count.textContent = bits.length
      ? `${matches.length} de ${total} partidos · ${bits.join(" · ")}`
      : `${total} partido${total === 1 ? "" : "s"}`;
  }
  const listTitle = $("#listTitle");
  if (listTitle) {
    listTitle.textContent =
      state.status === "live"
        ? "En vivo"
        : state.status === "favorites"
          ? "Favoritos"
          : state.status === "finished"
            ? "Finalizados"
            : state.status === "upcoming"
              ? "Próximos"
              : "Partidos";
  }
  const subtitle = $("#listSubtitle");
  if (subtitle) {
    subtitle.textContent = dateLiveCount
      ? `${dateLiveCount} partido${dateLiveCount === 1 ? "" : "s"} en directo · ${formatLongDate(state.date)}`
      : `Selecciona un partido para analizarlo · ${formatLongDate(state.date)}`;
  }
  const labels = {
    top: "Top 5 · Ligas principales",
    other: "Otras competiciones",
    south: "Sudamérica",
  };
  list.innerHTML = grouped
    .map(([key, items]) => {
      const rows = items.map(renderMatchRow).join("");
      return `<div class="match-group">
        <div class="match-group-head">
          <h3>${labels[key]}</h3>
          <span class="group-count">${items.length}</span>
        </div>
        ${rows}
      </div>`;
    })
    .join("");
  const empty = $("#listEmpty");
  if (empty) {
    empty.hidden = matches.length > 0 || state.loadingDay || state.loadingRest;
    if (matches.length === 0 && state.matches.length > 0) {
      const title = empty.querySelector("h2");
      const text = empty.querySelector("p");
      if (title) title.textContent = "Sin resultados con estos filtros";
      if (text) text.textContent = "Pulsa Esc o cambia la liga, el estado o la búsqueda.";
    } else {
      const title = empty.querySelector("h2");
      const text = empty.querySelector("p");
      if (title) title.textContent = "No hay partidos";
      if (text) text.textContent = "Prueba con otra fecha, región o competición.";
    }
  }
  list.scrollTop = previousScroll;
  state.listScroll = previousScroll;
  document.querySelectorAll(".match-row").forEach((row) => {
    row.classList.toggle("is-selected", Number(row.dataset.matchId) === state.selectedId);
  });
  updateControlStates();
}

function renderMatchRow(match) {
  const live = isLive(match);
  const finished = isFinished(match);
  const winner = winnerSide(match);
  const homeFavorite = state.favorites[String(match.home_team?.id)] !== undefined;
  const awayFavorite = state.favorites[String(match.away_team?.id)] !== undefined;
  const homeLoser = finished && winner && winner !== "home";
  const awayLoser = finished && winner && winner !== "away";
  const time = matchTimeLabel(match);
  const statusWord = live
    ? "En vivo"
    : finished
      ? ""
      : match.status_type === "delayed"
        ? "Aplazado"
        : "Próximo";
  const score = scoreText(match);
  const tooltip = `${teamFullName(match.home_team)} vs ${teamFullName(match.away_team)} · ${match.tournament?.name || "Competición"} · ${statusInfo(match).label}${isLive(match) || isFinished(match) ? ` · ${scoreShort(match)}` : ""}`;
  return `<div class="match-row ${live ? "is-live" : ""}" data-match-id="${esc(match.id)}" role="listitem" tabindex="0" title="${esc(tooltip)}">
    <div class="match-time">
      <span>${esc(time)}</span>
      <span class="status-word">${esc(statusWord)}</span>
    </div>
    <div class="match-teams">
      <div class="team-line ${homeLoser ? "is-loser" : ""} ${finished && winner === "home" ? "is-winner" : ""}">
        ${crest(match.home_team)}
        <span class="team-name">${esc(teamName(match.home_team))}</span>
        <button class="fav-star ${homeFavorite ? "is-fav" : ""}" type="button" data-fav-team="${esc(match.home_team?.id)}" data-fav-name="${esc(teamFullName(match.home_team))}" title="Favorito" aria-pressed="${homeFavorite}" aria-label="${homeFavorite ? "Quitar" : "Marcar"} ${esc(teamFullName(match.home_team))} ${homeFavorite ? "de" : "como"} favorito">${icon(homeFavorite ? "star-filled" : "star")}</button>
      </div>
      <div class="team-line ${awayLoser ? "is-loser" : ""} ${finished && winner === "away" ? "is-winner" : ""}">
        ${crest(match.away_team)}
        <span class="team-name">${esc(teamName(match.away_team))}</span>
        <button class="fav-star ${awayFavorite ? "is-fav" : ""}" type="button" data-fav-team="${esc(match.away_team?.id)}" data-fav-name="${esc(teamFullName(match.away_team))}" title="Favorito" aria-pressed="${awayFavorite}" aria-label="${awayFavorite ? "Quitar" : "Marcar"} ${esc(teamFullName(match.away_team))} ${awayFavorite ? "de" : "como"} favorito">${icon(awayFavorite ? "star-filled" : "star")}</button>
      </div>
    </div>
    <div class="match-score">
      <span class="score-value">${esc(score)}</span>
      <span class="league-tag">${flag(match.tournament?.category_id, match.tournament?.category)}${esc(shortName(match.tournament?.name || "—", 18))}</span>
    </div>
  </div>`;
}

/* --------------------------------------------------------------------------
   Selección y detalle
   -------------------------------------------------------------------------- */
function selectMatch(matchId) {
  const match = state.matchesById.get(Number(matchId)) || state.matches.find((item) => Number(item.id) === Number(matchId));
  if (!match) return;
  selectMatchObject(match);
}

function selectMatchObject(match, { autoAnalyze = true } = {}) {
  state.analysisToken += 1;
  state.simToken += 1;
  setDetailBusy(false);
  state.selectedId = match.id;
  state.selectedMatch = match;
  state.analysis = null;
  state.analysisJob = null;
  state.simulation = null;
  state.simJob = null;
  state.analysisWindow = 10;
  state.detailTab = "overview";
  state.preview = null;
  state.detailOpen = true;
  $("#view-matches")?.classList.add("detail-open");
  renderDetail({ scrollTop: 0 });
  document.querySelectorAll(".match-row").forEach((row) => {
    row.classList.toggle("is-selected", Number(row.dataset.matchId) === Number(match.id));
  });
  const pane = $("#detailPane");
  if (pane && window.innerWidth <= 1120) pane.scrollIntoView({ block: "start" });
  if (autoAnalyze && state.prefs.auto_analyze !== false) {
    analyzeMatch();
  }
}

function clearSelection() {
  state.analysisToken += 1;
  state.simToken += 1;
  setDetailBusy(false);
  state.selectedId = null;
  state.selectedMatch = null;
  state.analysis = null;
  state.analysisJob = null;
  state.simulation = null;
  state.simJob = null;
  state.detailOpen = false;
  state.preview = null;
  $("#view-matches")?.classList.remove("detail-open");
  renderDetail();
  document.querySelectorAll(".match-row").forEach((row) => row.classList.remove("is-selected"));
}

async function openMatchById(matchId, { switchDate = true } = {}) {
  if (matchId === null || matchId === undefined || matchId === "") return;
  setStatus("Cargando partido…", "busy");
  try {
    const detail = await api(`/api/match?id=${encodeURIComponent(matchId)}`);
    const match = detail.match;
    if (!match) throw new Error("Partido no disponible.");
    const day = matchDay(match);
    setStatus(`Partido cargado: ${teamName(match.home_team)} vs ${teamName(match.away_team)}.`);
    if (switchDate && day && day !== state.date) {
      state.date = day;
      const input = $("#dateInput");
      if (input) input.value = day;
      updateDayCaption();
      const pending = loadDay();
      selectMatchObject({ ...match });
      await pending;
    } else {
      selectMatchObject({ ...(state.matchesById.get(match.id) || {}), ...match });
    }
  } catch (error) {
    toast("No se pudo abrir el partido", error.message, "error");
    setStatus("Error al abrir el partido.", "error");
  }
}

function renderDetail({ scrollTop = null } = {}) {
  const pane = $("#detailPane");
  const empty = $("#detailEmpty");
  const content = $("#detailContent");
  if (!pane || !empty || !content) return;
  const preserve = scrollTop === null ? pane.scrollTop : scrollTop;
  if (!state.selectedMatch) {
    empty.hidden = false;
    content.hidden = true;
    content.innerHTML = "";
    pane.scrollTop = 0;
    return;
  }
  empty.hidden = true;
  content.hidden = false;
  content.innerHTML = renderHero(state.selectedMatch) + renderTabs() + `<div class="tab-panel" id="tab-panel-${state.detailTab}" role="tabpanel" tabindex="0" aria-labelledby="tab-${state.detailTab}">${renderTabContent()}</div>`;
  pane.scrollTop = preserve;
}

function renderHero(match) {
  const live = isLive(match);
  const finished = isFinished(match);
  const status = statusInfo(match);
  const homeFavorite = state.favorites[String(match.home_team?.id)] !== undefined;
  const awayFavorite = state.favorites[String(match.away_team?.id)] !== undefined;
  const sameDay = matchDay(match) === state.date;
  const windowLabel = state.analysis?.window === "all" ? "toda la temporada" : `últimos ${state.analysis?.window || state.analysisWindow} partidos`;
  return `<div class="detail-hero">
    <div class="hero-topline">
      <span class="hero-league">${flag(match.tournament?.category_id, match.tournament?.category)}${esc(match.tournament?.name || "Competición")}${match.round ? ` · Jornada ${esc(match.round)}` : ""}</span>
      <span class="hero-date">${esc(formatDateTime(match.start_timestamp))}</span>
      <button class="icon-button hero-close" type="button" data-action="close-detail" title="Volver a la lista">${icon("arrow-left")}</button>
    </div>
    <div class="hero-main">
      <div class="hero-team home">
        ${match.home_team?.id ? crest(match.home_team, "hero-crest") : `<span class="hero-crest-fallback">${esc(initials(match.home_team))}</span>`}
        <div class="hero-team-name">${esc(teamFullName(match.home_team))}</div>
        <div class="hero-team-sub">
          <button class="fav-star ${homeFavorite ? "is-fav" : ""}" type="button" data-fav-team="${esc(match.home_team?.id)}" data-fav-name="${esc(teamFullName(match.home_team))}" title="Favorito" aria-pressed="${homeFavorite}" aria-label="${homeFavorite ? "Quitar" : "Marcar"} ${esc(teamFullName(match.home_team))} ${homeFavorite ? "de" : "como"} favorito">${icon(homeFavorite ? "star-filled" : "star")}</button>
          <span>${esc(match.home_team?.country || "Local")}</span>
        </div>
      </div>
      <div class="hero-center">
        <div class="hero-score ${live ? "is-live" : ""}">${esc(scoreText(match))}</div>
        <div class="hero-status ${status.className}">${live ? '<span class="live-dot"></span>' : ""}${esc(status.label)}</div>
      </div>
      <div class="hero-team away">
        ${match.away_team?.id ? crest(match.away_team, "hero-crest") : `<span class="hero-crest-fallback">${esc(initials(match.away_team))}</span>`}
        <div class="hero-team-name">${esc(teamFullName(match.away_team))}</div>
        <div class="hero-team-sub">
          <span>${esc(match.away_team?.country || "Visitante")}</span>
          <button class="fav-star ${awayFavorite ? "is-fav" : ""}" type="button" data-fav-team="${esc(match.away_team?.id)}" data-fav-name="${esc(teamFullName(match.away_team))}" title="Favorito" aria-pressed="${awayFavorite}" aria-label="${awayFavorite ? "Quitar" : "Marcar"} ${esc(teamFullName(match.away_team))} ${awayFavorite ? "de" : "como"} favorito">${icon(awayFavorite ? "star-filled" : "star")}</button>
        </div>
      </div>
    </div>
    <div class="hero-actions">
      <button class="primary-button" type="button" data-action="analyze" ${state.analysisJob?.status === "running" ? "disabled" : ""}>${icon(state.analysisJob?.status === "running" ? "refresh" : state.analysis ? "refresh" : "sparkles")}${state.analysisJob?.status === "running" ? "Analizando…" : state.analysis ? "Actualizar análisis" : "Analizar partido"}</button>
      <button class="soft-button" type="button" data-action="simulate" ${state.analysis ? "" : "disabled"} title="${state.analysis ? "Ejecutar la simulación Monte Carlo" : "Analiza primero el partido"}">${icon("play")}Simular</button>
      <button class="soft-button" type="button" data-action="preview" ${state.analysis ? "" : "disabled"} title="${state.analysis ? "Generar la previa" : "Analiza primero el partido"}">${icon("file")}Previa</button>
      ${!sameDay ? `<button class="soft-button" type="button" data-action="go-day">${icon("calendar")}Ver su fecha</button>` : ""}
      <span class="spacer"></span>
      <span class="hero-action-note">${icon("clock")}${esc(windowLabel)}</span>
    </div>
    ${state.simulation || state.analysisJob?.status === "running" ? "" : ""}
  </div>`;
}

function renderTabs() {
  const tabs = [
    ["overview", "Resumen"],
    ["simulation", "Simulación"],
    ["lineups", "Alineaciones"],
    ["context", "Contexto"],
  ];
  const lineupCount = (state.analysis?.lineups?.home?.players || []).filter((player) => !player.substitute).length +
    (state.analysis?.lineups?.away?.players || []).filter((player) => !player.substitute).length;
  return `<div class="tabs" role="tablist" aria-label="Detalle del partido">
    ${tabs
      .map(
        ([key, label]) =>
          `<button class="tab ${state.detailTab === key ? "is-active" : ""}" id="tab-${key}" type="button" data-action="tab" data-tab="${key}" role="tab" aria-selected="${state.detailTab === key}" aria-controls="tab-panel-${key}" tabindex="${state.detailTab === key ? "0" : "-1"}">${label}${key === "lineups" && lineupCount ? `<span class="tab-badge">${lineupCount}</span>` : ""}${key === "context" && state.analysis?.warnings?.length ? `<span class="tab-badge">${state.analysis.warnings.length}</span>` : ""}</button>`,
      )
      .join("")}
  </div>`;
}

function renderTabContent() {
  if (state.analysisJob?.status === "running" && !state.analysis) {
    return renderAnalysisCTA(true);
  }
  if (state.analysisJob?.status === "error" && !state.analysis) {
    return `${renderAnalysisError()}`;
  }
  if (!state.analysis) {
    return renderAnalysisCTA(false);
  }
  if (state.detailTab === "simulation") return renderSimulation();
  if (state.detailTab === "lineups") return renderLineups();
  if (state.detailTab === "context") return renderContext();
  return renderOverview();
}

/* --------------------------------------------------------------------------
   Análisis
   -------------------------------------------------------------------------- */
function windowOptions(selected) {
  return [
    [5, "Últimos 5 partidos"],
    [10, "Últimos 10 partidos"],
    [15, "Últimos 15 partidos"],
    ["all", "Toda la temporada"],
  ]
    .map(
      ([value, label]) =>
        `<option value="${value}" ${String(value) === String(selected) ? "selected" : ""}>${label}</option>`,
    )
    .join("");
}

function renderAnalysisCTA(running = false) {
  if (running) {
    const progress = state.analysisJob?.progress || {};
    const percent = progress.total
      ? Math.min(100, Math.round((progress.done / progress.total) * 100))
      : 8;
    return `<div class="sim-progress" id="analysisProgress" role="status" aria-live="polite">
      <div class="sim-progress-top"><span>${esc(progress.message || "Analizando la forma de ambos equipos…")}</span><span>${percent}%</span></div>
      <div class="progress-track" role="progressbar" aria-label="Progreso del análisis" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><div class="progress-fill" style="width:${Math.max(6, percent)}%"></div></div>
    </div>
    <div class="sim-empty">${icon("sparkles")}<div style="margin-top:8px">Consultando partidos, estadísticas, alineaciones y árbitro. Suele tardar unos segundos.</div></div>`;
  }
  return `<div class="card card-pad" style="text-align:center;padding:30px 22px">
    <div class="empty-icon" style="margin:0 auto 12px">${icon("sparkles")}</div>
    <h3 style="margin:0;font-family:var(--font-display);font-size:20px;letter-spacing:-.035em">Analiza este partido</h3>
    <p style="color:var(--muted);font-size:12px;max-width:380px;margin:7px auto 15px">Verás la forma reciente, la comparación de estadísticas, las alineaciones y el árbitro. Después podrás simular el resultado.</p>
    <div style="display:flex;gap:8px;justify-content:center;align-items:center;flex-wrap:wrap">
      <label class="select-field inline">Ventana <select id="analysisWindowSelect" aria-label="Ventana de análisis">${windowOptions(state.analysisWindow)}</select></label>
      <button class="primary-button" type="button" data-action="analyze">${icon("sparkles")}Analizar partido</button>
    </div>
  </div>`;
}

function renderAnalysisError() {
  return `<div class="warning-box">${icon("alert")}<div><strong>No se pudo completar el análisis.</strong><br>${esc(state.analysisJob?.error || "Error desconocido.")}</div></div>
    <div style="margin-top:12px"><button class="primary-button" type="button" data-action="analyze">${icon("refresh")}Reintentar</button></div>`;
}

async function analyzeMatch(force = false) {
  if (!state.selectedMatch) return null;
  const matchId = state.selectedMatch.id;
  const token = ++state.analysisToken;
  state.analysis = null;
  state.simulation = null;
  state.preview = null;
  state.simJob = null;
  state.analysisJob = {
    status: "running",
    progress: { done: 0, total: 1, message: "Iniciando el análisis…" },
  };
  setDetailBusy(true);
  renderDetail();
  setStatus("Analizando la forma de ambos equipos…", "busy");
  try {
    const { job } = await api("/api/jobs/analysis", {
      method: "POST",
      body: {
        match_id: matchId,
        window: state.analysisWindow,
        force,
      },
    });
    const result = await pollJob(
      job.id,
      (current) => {
        if (token !== state.analysisToken) return;
        state.analysisJob = current;
        updateAnalysisProgress(current);
      },
      () => token === state.analysisToken,
    );
    if (token !== state.analysisToken) return null;
    state.analysis = result;
    state.analysisJob = null;
    setDetailBusy(false);
    if (result?.match) {
      state.selectedMatch = { ...state.selectedMatch, ...result.match };
      state.matchesById.set(result.match.id, {
        ...(state.matchesById.get(result.match.id) || {}),
        ...result.match,
      });
      const index = state.matches.findIndex((match) => match.id === result.match.id);
      if (index >= 0) state.matches[index] = { ...state.matches[index], ...result.match };
    }
    state.analysisWindow = result.window ?? state.analysisWindow;
    renderDetail();
    setStatus(
      `Análisis listo: ${result.teams?.home?.sample_size || 0} + ${result.teams?.away?.sample_size || 0} partidos revisados.`,
    );
    return result;
  } catch (error) {
    if (token !== state.analysisToken) return null;
    state.analysisJob = { status: "error", error: error.message };
    setDetailBusy(false);
    renderDetail();
    setStatus("No se pudo analizar el partido.", "error");
    toast("No se pudo analizar", error.message, "error");
    return null;
  }
}

function updateAnalysisProgress(job) {
  const banner = $("#analysisProgress");
  if (!banner) {
    renderDetail();
    return;
  }
  const progress = job.progress || {};
  const percent = progress.total
    ? Math.min(100, Math.round((progress.done / progress.total) * 100))
    : 8;
  const text = banner.querySelector(".sim-progress-top span:first-child");
  const value = banner.querySelector(".sim-progress-top span:last-child");
  const fill = banner.querySelector(".progress-fill");
  if (text) text.textContent = progress.message || "Analizando…";
  if (value) value.textContent = `${percent}%`;
  if (fill) fill.style.width = `${Math.max(6, percent)}%`;
  const track = banner.querySelector(".progress-track");
  track?.setAttribute("aria-valuenow", String(percent));
}

async function pollJob(jobId, onUpdate, active) {
  for (let attempt = 0; attempt < 900; attempt += 1) {
    if (!active()) return null;
    const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
    onUpdate(job);
    if (job.status === "done") return job.result;
    if (job.status === "error") throw new Error(job.error || "El trabajo falló.");
    await sleep(600);
  }
  throw new Error("La operación está tardando demasiado. Inténtalo de nuevo.");
}

/* --------------------------------------------------------------------------
   Resumen del análisis
   -------------------------------------------------------------------------- */
function renderOverview() {
  const analysis = state.analysis;
  const match = state.selectedMatch;
  const teams = analysis.teams || {};
  const home = teams.home || {};
  const away = teams.away || {};
  const comparison = analysis.comparison || [];
  const homeName = teamName(home.team || match?.home_team);
  const awayName = teamName(away.team || match?.away_team);
  const homeGoals = averageStat(home, "goals_for");
  const awayGoals = averageStat(away, "goals_for");
  const homeXg = averageStat(home, "xg_for");
  const awayXg = averageStat(away, "xg_for");
  const windowText = analysis.window === "all" ? "toda la temporada" : `últimos ${analysis.window} partidos`;
  return `
    <div class="overview-toolbar" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px">
      <span class="inline-note">${icon("clock")}Ventana: ${esc(windowText)} · ${esc(analysis.generated_at ? new Date(analysis.generated_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) : "")}</span>
      <span style="flex:1"></span>
      <label class="select-field inline">Cambiar <select id="analysisWindowSelect" aria-label="Cambiar ventana de análisis">${windowOptions(analysis.window)}</select></label>
      <button class="soft-button" type="button" data-action="export-analysis-json">${icon("download")}JSON</button>
      <button class="soft-button" type="button" data-action="export-analysis-csv">${icon("download")}CSV</button>
    </div>
    <div class="kpi-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">
      ${kpiCard("Partidos analizados", `${fmtInt(home.sample_size)} + ${fmtInt(away.sample_size)}`, "local y visitante", "var(--accent)")}
      ${kpiCard("Goles a favor", `${fmt(homeGoals)} · ${fmt(awayGoals)}`, "media por partido", "var(--home)")}
      ${kpiCard("xG a favor", `${fmt(homeXg)} · ${fmt(awayXg)}`, homeXg === null && awayXg === null ? "sin datos de xG" : "media por partido", "var(--accent-2)")}
      ${kpiCard("Forma reciente", `${home.form || "—"} · ${away.form || "—"}`, "últimos resultados", "var(--good)")}
    </div>
    <div class="grid-2" style="align-items:start">
      <div class="card card-pad">
        <div class="section-title">${icon("chart")}Comparación de forma</div>
        ${renderComparison(comparison)}
      </div>
      <div class="card card-pad">
        <div class="section-title">${icon("info")}Contexto del partido</div>
        <div class="info-list">
          ${infoRow("Competición", `${flag(match?.tournament?.category_id, match?.tournament?.category)} ${esc(match?.tournament?.name || "—")}`)}
          ${infoRow("Fecha", esc(formatDateTime(match?.start_timestamp)))}
          ${infoRow("Estadio", esc(match?.venue?.name || "Sin datos"))}
          ${infoRow("Árbitro", esc(analysis.referee?.name || "Por designar"))}
          ${infoRow("Alineación", esc(lineupStatusLabel(analysis.lineups)))}
          ${analysis.actual ? infoRow("Resultado real", `<strong>${esc(analysis.actual.score || "—")}</strong> · ${esc(analysis.actual.status === "live" ? `En vivo ${Math.round(analysis.actual.minute || 0)}'` : "finalizado")}`) : ""}
        </div>
        ${renderActualSummary(analysis.actual)}
      </div>
    </div>
    <div class="grid-2" style="margin-top:10px;align-items:start">
      ${renderTeamBlock(home, homeName, "home")}
      ${renderTeamBlock(away, awayName, "away")}
    </div>
    ${renderWarnings(analysis.warnings)}
  `;
}

function kpiCard(label, value, sub, color) {
  return `<div class="kpi-card" style="--kpi-color:${color}">
    <div class="kpi-label">${esc(label)}</div>
    <div class="kpi-value">${value}</div>
    <div class="kpi-sub">${esc(sub)}</div>
  </div>`;
}

function infoRow(label, value) {
  return `<div class="info-row">${icon("info")}<div><strong>${esc(label)}</strong>${value}</div></div>`;
}

function averageStat(block, key) {
  const value = block?.averages?.[key];
  return value === null || value === undefined ? null : Number(value);
}

function renderComparison(comparison) {
  const wanted = [
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "shots",
    "shots_on_target",
    "corners",
    "cards",
    "fouls",
    "saves",
  ];
  const rows = comparison.filter(
    (row) => wanted.includes(row.stat) && (row.home !== null || row.away !== null),
  );
  if (!rows.length) {
    return `<div class="empty-state compact"><p>No hay estadísticas suficientes para comparar.</p></div>`;
  }
  return `<div class="comparison-list">${rows
    .map((row) => {
      const home = Number(row.home || 0);
      const away = Number(row.away || 0);
      const total = Math.max(home + away, 0.01);
      return `<div class="comparison-row">
        <div class="comparison-value">${esc(fmt(row.home))}</div>
        <div class="comparison-center">
          <div class="comparison-label">${esc(row.label)}</div>
          <div class="comparison-bar">
            <div class="home-fill" style="width:${(home / total) * 100}%"></div>
            <div class="away-fill" style="width:${(away / total) * 100}%"></div>
          </div>
        </div>
        <div class="comparison-value away">${esc(fmt(row.away))}</div>
      </div>`;
    })
    .join("")}</div>`;
}

function lineupStatusLabel(lineups) {
  if (!lineups) return "Sin datos";
  const players = ["home", "away"].reduce(
    (sum, side) => sum + (lineups[side]?.players || []).filter((player) => !player.substitute).length,
    0,
  );
  if (!players) return "Sin datos";
  return lineups.confirmed ? "Confirmada" : "Probable";
}

function renderActualSummary(actual) {
  if (!actual) return "";
  const totals = actual.totals || {};
  const rows = [
    ["Goles", totals.goals],
    ["Remates", totals.shots],
    ["Al arco", totals.shots_on_target],
    ["Córners", totals.corners],
    ["Tarjetas", totals.cards],
    ["Faltas", totals.fouls],
  ].filter(([, value]) => value !== null && value !== undefined);
  if (!rows.length) return "";
  return `<div class="actual-summary" style="margin-top:10px;padding-top:9px;border-top:1px solid var(--border)">
    <div class="section-title" style="margin-bottom:6px">${icon("target")}Datos reales</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px">
      ${rows.map(([label, value]) => `<div style="font-size:10px;color:var(--muted)">${esc(label)} <strong style="float:right;color:var(--text-soft)">${esc(fmtInt(value))}</strong></div>`).join("")}
    </div>
  </div>`;
}

function renderTeamBlock(block, name, side) {
  const team = block.team || {};
  const averages = block.averages || {};
  const labels = {
    goals_for: "Goles a favor",
    goals_against: "Goles en contra",
    xg_for: "xG a favor",
    xg_against: "xG en contra",
    shots: "Remates",
    shots_on_target: "Al arco",
    corners: "Córners",
    cards: "Tarjetas",
    fouls: "Faltas",
    saves: "Paradas",
  };
  const rows = Object.entries(labels)
    .filter(([key]) => averages[key] !== null && averages[key] !== undefined)
    .slice(0, 8)
    .map(
      ([key, label]) =>
        `<tr><td>${esc(label)}</td><td class="num">${esc(fmt(averages[key]))}</td></tr>`,
    )
    .join("");
  const matches = block.matches || [];
  const recent = matches
    .slice(0, 6)
    .map((row) => {
      const outcome = row.outcome || "E";
      const score = row.score || scoreShort(row);
      return `<div class="match-mini-row" data-open-match="${esc(row.event_id || row.id || "")}" tabindex="0" role="button" aria-label="Abrir ${esc(row.opponent || row.team || "partido")} ${esc(score)}" style="cursor:pointer">
        <span class="match-mini-date">${esc(String(row.date || "").slice(5))}</span>
        <span class="match-mini-teams">${esc(row.home ? "" : "vs ")}${esc(row.opponent || row.team || "—")}</span>
        <span class="match-mini-score">${esc(score)}</span>
        <span class="outcome ${esc(outcome)}">${esc(outcome)}</span>
      </div>`;
    })
    .join("");
  return `<div class="team-block">
    <div class="team-block-head">
      ${crest(team)}
      <strong>${esc(name)}</strong>
      <span class="mini-meta">${esc(block.sample_size || 0)} PJ · ${esc(block.stats_sample_size || 0)} con datos</span>
      <span class="form-pills">${renderForm(block.form)}</span>
    </div>
    <table class="mini-table">${rows || '<tr><td>Sin estadísticas disponibles.</td></tr>'}</table>
    ${recent ? `<div class="team-matches"><div class="section-title" style="padding:8px 10px 0">${icon("list")}Últimos partidos</div>${recent}</div>` : ""}
  </div>`;
}

function renderForm(form) {
  if (!form) return "";
  return String(form)
    .slice(-5)
    .split("")
    .map((result) => {
      const key = result.toUpperCase();
      const className = key === "W" || key === "G" ? "w" : key === "L" || key === "P" ? "l" : "d";
      const label = key === "W" || key === "G" ? "G" : key === "L" || key === "P" ? "P" : "E";
      return `<span class="form-pill ${className}">${label}</span>`;
    })
    .join("");
}

function renderWarnings(warnings) {
  if (!warnings || !warnings.length) return "";
  const unique = [...new Set(warnings)].slice(0, 5);
  return `<div class="warning-box" style="margin-top:10px">${icon("alert")}<div>${unique.map((warning) => esc(warning)).join("<br>")}</div></div>`;
}

/* --------------------------------------------------------------------------
   Simulación
   -------------------------------------------------------------------------- */
function renderSimulation() {
  if (!state.analysis) {
    return renderAnalysisCTA(state.analysisJob?.status === "running");
  }
  const analysis = state.analysis;
  const iterationOptions = [1000, 5000, 10000, 25000, 50000, 100000];
  const currentIterations = state.simulation?.meta?.iterations || 10000;
  const seed = state.simulation?.meta?.seed ?? 42;
  const running = state.simJob?.status === "running";
  const controls = `<div class="sim-controls">
    <label class="control-field"><span>Simulaciones</span><select id="simIterations" aria-label="Número de simulaciones" ${running ? "disabled" : ""}>${iterationOptions.map((value) => `<option value="${value}" ${value === currentIterations ? "selected" : ""}>${value.toLocaleString("es-ES")}</option>`).join("")}</select></label>
    <label class="control-field" style="width:86px"><span>Semilla</span><input id="simSeed" type="number" value="${esc(seed)}" aria-label="Semilla aleatoria" ${running ? "disabled" : ""}></label>
    <label class="control-field"><span>Ventana</span><select id="simWindow" aria-label="Ventana de análisis para la simulación" ${running ? "disabled" : ""}>${windowOptions(analysis.window)}</select></label>
    <button class="primary-button" type="button" data-action="run-simulation" ${running ? "disabled" : ""}>${icon(running ? "refresh" : "play")}${running ? "Simulando…" : state.simulation ? "Volver a simular" : "Simular partido"}</button>
    <button class="soft-button" type="button" data-action="clear-cache" ${running ? "disabled" : ""}>${icon("trash")}Vaciar caché</button>
  </div>
  <div class="sim-context">${icon("info")}<span>${esc(simulationContext())}</span></div>
  ${running ? renderSimulationProgress() : ""}
  ${state.simJob?.status === "error" ? `<div class="warning-box" style="margin-top:10px">${icon("alert")}<div><strong>No se pudo simular.</strong><br>${esc(state.simJob.error || "Error desconocido.")}</div></div>` : ""}`;
  if (!state.simulation) {
    return `${controls}
      <div class="sim-empty">
        <div class="empty-icon" style="margin:0 auto 10px">${icon("chart")}</div>
        <strong style="color:var(--text)">Monte Carlo con NumPy</strong>
        <div style="margin-top:5px">Genera miles de escenarios para obtener probabilidades, marcadores y mercados. No es una predicción garantizada.</div>
        <button class="primary-button" type="button" data-action="run-simulation" style="margin-top:14px">${icon("play")}Ejecutar simulación</button>
      </div>`;
  }
  return `${controls}${renderSimulationResults(state.simulation)}`;
}

function simulationContext() {
  const analysis = state.analysis || {};
  const parts = [];
  const status = lineupStatusLabel(analysis.lineups);
  parts.push(status === "Sin datos" ? "Sin alineaciones" : `Alineación ${status.toLowerCase()}`);
  if (analysis.referee?.name) {
    let referee = `Árbitro ${analysis.referee.name}`;
    if (analysis.referee.cards_per_match !== null && analysis.referee.cards_per_match !== undefined) {
      referee += ` (${fmt(analysis.referee.cards_per_match, 1)} tarjetas/partido)`;
    }
    parts.push(referee);
  } else {
    parts.push("árbitro por designar");
  }
  const actual = analysis.actual;
  if (actual?.status === "live") {
    parts.unshift(`En vivo · ${Math.round(actual.minute || 0)}'`);
  }
  return `Contexto: ${parts.join(" · ")}`;
}

function renderSimulationProgress() {
  const progress = state.simJob?.progress || {};
  const percent = progress.total ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 8;
  return `<div class="sim-progress" id="simulationProgress" role="status" aria-live="polite">
    <div class="sim-progress-top"><span>${esc(progress.message || "Simulando…")}</span><span>${percent}%</span></div>
    <div class="progress-track" role="progressbar" aria-label="Progreso de la simulación" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><div class="progress-fill" style="width:${Math.max(6, percent)}%"></div></div>
  </div>`;
}

function renderSimulationResults(summary) {
  const teams = summary.teams || {};
  const home = teams.home || {};
  const away = teams.away || {};
  const homeExpected = home.expected || {};
  const awayExpected = away.expected || {};
  const totals = summary.totals || {};
  const mean = totals.mean || {};
  const percentiles = totals.percentiles || {};
  const probabilities = summary.probabilities || {};
  const winner = probabilities.winner || {};
  const overUnder = probabilities.over_under || {};
  const btts = Number(probabilities.btts || 0);
  const over25 = Number(overUnder.goals?.["2.5"]?.over || 0);
  const homeName = home.name || "Local";
  const awayName = away.name || "Visitante";
  const topSide = ["home", "draw", "away"].reduce((best, side) =>
    Number(winner[side] || 0) > Number(winner[best] || 0) ? side : best,
  );
  const topLabel = topSide === "home" ? homeName : topSide === "away" ? awayName : "Empate";
  const topProbability = Number(winner[topSide] || 0);
  const cornersPercentiles = percentiles.corners || {};
  const kpis = `
    <div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(155px,1fr))">
      ${kpiCard("Goles", fmt(mean.goals), `L ${fmt(homeExpected.goals_for)} · V ${fmt(awayExpected.goals_for)}`, "var(--accent)")}
      ${kpiCard("Resultado", pct(topProbability), `gana ${shortName(topLabel, 12)}`, "var(--home)")}
      ${kpiCard("Ambos marcan", pct(btts), "sí / no", "var(--good)")}
      ${kpiCard("Over 2,5", pct(over25), "goles", "var(--warn)")}
      ${kpiCard("Córners", fmt(mean.corners), `P10–P90 ${fmtInt(cornersPercentiles.p10)}–${fmtInt(cornersPercentiles.p90)}`, "var(--accent-2)")}
    </div>`;
  const grouped = [
    { label: "Goles", home: homeExpected.goals_for, away: awayExpected.goals_for },
    { label: "Remates", home: homeExpected.shots, away: awayExpected.shots },
    { label: "Al arco", home: homeExpected.shots_on_target, away: awayExpected.shots_on_target },
    { label: "Córners", home: homeExpected.corners, away: awayExpected.corners },
    { label: "Tarjetas", home: homeExpected.cards, away: awayExpected.cards },
    { label: "Faltas", home: homeExpected.fouls, away: awayExpected.fouls },
    { label: "Paradas", home: homeExpected.saves, away: awayExpected.saves },
  ];
  const donutSegments = [
    { label: "Local", value: Number(winner.home || 0), color: "var(--home)" },
    { label: "Empate", value: Number(winner.draw || 0), color: "var(--faint)" },
    { label: "Visitante", value: Number(winner.away || 0), color: "var(--away)" },
  ];
  const histogram = summary.histograms?.[state.simMetric] || summary.histograms?.goals;
  const market = overUnder[state.simMarket] || overUnder.goals || {};
  const actual = summary.actual || state.analysis?.actual;
  const validation = renderValidation(actual, summary);
  return `${kpis}
    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-head"><h4>Esperado por equipo</h4><div class="chart-legend"><span><span class="legend-dot" style="background:var(--home)"></span>${esc(shortName(homeName, 14))}</span><span><span class="legend-dot" style="background:var(--away)"></span>${esc(shortName(awayName, 14))}</span></div></div>
        ${renderGroupedBars(grouped)}
      </div>
      <div class="chart-card">
        <div class="chart-head"><h4>Probabilidad 1X2</h4></div>
        ${renderDonut(donutSegments, pct(topProbability), `gana ${shortName(topLabel, 16)}`)}
        <div class="section-title" style="margin-top:4px">${icon("target")}Marcadores más probables</div>
        ${renderBarList((summary.scorelines || []).slice(0, 6).map((item) => ({ label: item.score, value: Number(item.probability || 0) })), "percentage")}
      </div>
      <div class="chart-card">
        <div class="chart-head"><h4>Distribución</h4>
          <select class="settings-select" id="simHistogramSelect" aria-label="Métrica de la distribución" style="margin-left:auto;height:28px;font-size:10px">
            ${histogramOptions(state.simMetric)}
          </select>
        </div>
        ${renderHistogram(histogram)}
        <div class="inline-note" style="margin-top:5px">${icon("info")}Media ${fmt(histogramMean(histogram))} · mediana ${fmt(histogramMedian(histogram))} · P10–P90 ${fmtInt(histogramPercentile(histogram, 0.1))}–${fmtInt(histogramPercentile(histogram, 0.9))}</div>
      </div>
      <div class="chart-card">
        <div class="chart-head"><h4>Mercados over/under</h4>
          <select class="settings-select" id="simMarketSelect" aria-label="Mercado over/under" style="margin-left:auto;height:28px;font-size:10px">
            ${marketOptions(state.simMarket)}
          </select>
        </div>
        ${renderOverUnder(market)}
      </div>
      <div class="chart-card">
        <div class="chart-head"><h4>Matriz de marcadores</h4><span class="chart-legend">Local / visitante</span></div>
        ${renderHeatmap(summary.score_matrix, homeName, awayName)}
      </div>
      <div class="chart-card">
        <div class="chart-head"><h4>Validación</h4><span class="chart-legend">${actual ? esc(actual.status === "live" ? "En vivo" : "Finalizado") : "Sin resultado"}</span></div>
        ${validation}
      </div>
    </div>
    <div style="display:flex;gap:7px;justify-content:flex-end;margin-top:10px;flex-wrap:wrap">
      <button class="soft-button" type="button" data-action="export-sim-json">${icon("download")}JSON</button>
      <button class="soft-button" type="button" data-action="export-sim-csv">${icon("download")}CSV</button>
    </div>`;
}

function histogramOptions(selected) {
  return [
    ["goals", "Goles totales"],
    ["goals_home", "Goles local"],
    ["goals_away", "Goles visitante"],
    ["shots", "Remates"],
    ["shots_on_target", "Remates al arco"],
    ["corners", "Córners"],
    ["cards", "Tarjetas"],
    ["fouls", "Faltas"],
    ["saves", "Paradas"],
  ]
    .map(
      ([key, label]) =>
        `<option value="${key}" ${key === selected ? "selected" : ""}>${label}</option>`,
    )
    .join("");
}

function marketOptions(selected) {
  return [
    ["goals", "Goles"],
    ["corners", "Córners"],
    ["cards", "Tarjetas"],
    ["shots", "Remates"],
    ["shots_on_target", "Remates al arco"],
    ["fouls", "Faltas"],
    ["saves", "Paradas"],
  ]
    .map(
      ([key, label]) =>
        `<option value="${key}" ${key === selected ? "selected" : ""}>${label}</option>`,
    )
    .join("");
}

function renderGroupedBars(items) {
  const max = Math.max(
    1,
    ...items.flatMap((item) => [Number(item.home || 0), Number(item.away || 0)]),
  );
  return `<div class="grouped-bars">${items
    .map(
      (item) => `<div class="grouped-row">
        <span class="grouped-label">${esc(item.label)}</span>
        <div class="grouped-tracks">
          <div class="grouped-track"><div class="bar-track"><div class="bar-fill home-bar" style="width:${(Number(item.home || 0) / max) * 100}%"></div></div><span class="grouped-value">${esc(fmt(item.home))}</span></div>
          <div class="grouped-track"><div class="bar-track"><div class="bar-fill away-bar" style="width:${(Number(item.away || 0) / max) * 100}%"></div></div><span class="grouped-value">${esc(fmt(item.away))}</span></div>
        </div>
      </div>`,
    )
    .join("")}</div>`;
}

function renderBarList(items, mode = "percentage") {
  if (!items.length) return `<div class="chart-empty">Sin datos.</div>`;
  const max = Math.max(0.0001, ...items.map((item) => Number(item.value || 0)));
  return `<div class="bar-list">${items
    .map(
      (item) => `<div class="bar-row">
        <span class="bar-label">${esc(item.label)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(Number(item.value || 0) / max) * 100}%"></div></div>
        <span class="bar-value">${mode === "percentage" ? esc(pct(item.value, 1)) : esc(fmt(item.value))}</span>
      </div>`,
    )
    .join("")}</div>`;
}

function renderDonut(segments, centerValue, centerLabel) {
  const total = segments.reduce((sum, segment) => sum + Math.max(0, Number(segment.value || 0)), 0) || 1;
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  const circles = segments
    .map((segment) => {
      const length = (Math.max(0, Number(segment.value || 0)) / total) * circumference;
      const circle = `<circle cx="56" cy="56" r="${radius}" fill="none" stroke="${segment.color}" stroke-width="12" stroke-dasharray="${length} ${circumference - length}" stroke-dashoffset="${-offset}"><title>${esc(segment.label)}: ${pct(segment.value, 1)}</title></circle>`;
      offset += length;
      return circle;
    })
    .join("");
  return `<div class="donut-wrap">
    <div class="donut"><svg viewBox="0 0 112 112" aria-hidden="true"><circle cx="56" cy="56" r="${radius}" fill="none" stroke="var(--surface-3)" stroke-width="12"/>${circles}</svg><div class="donut-center"><strong>${esc(centerValue)}</strong><span>${esc(centerLabel)}</span></div></div>
    <div class="legend-list">${segments
      .map(
        (segment) => `<div class="legend-row"><span class="legend-dot" style="background:${segment.color}"></span><span class="legend-label">${esc(segment.label)}</span><strong>${esc(pct(segment.value, 1))}</strong></div>`,
      )
      .join("")}</div>
  </div>`;
}

function renderHistogram(histogram) {
  if (!histogram || !histogram.labels?.length) {
    return `<div class="chart-empty">Ejecuta la simulación para ver la distribución.</div>`;
  }
  const labels = histogram.labels;
  const counts = histogram.counts || [];
  const max = Math.max(1, ...counts);
  const width = 320;
  const height = 145;
  const bottom = 22;
  const top = 8;
  const left = 5;
  const usable = width - left * 2;
  const barWidth = usable / labels.length;
  const bars = counts
    .map((count, index) => {
      const barHeight = Math.max(1, (count / max) * (height - bottom - top));
      const x = left + index * barWidth + 1;
      const y = height - bottom - barHeight;
      const label = labels[index];
      const labelEvery = labels.length > 12 ? 2 : 1;
      return `<rect class="hist-bar" x="${x}" y="${y}" width="${Math.max(2, barWidth - 2)}" height="${barHeight}" rx="2"><title>${esc(label)}: ${esc(pct((histogram.percent || [])[index] || 0, 1))}</title></rect>${index % labelEvery === 0 ? `<text class="hist-label" x="${x + barWidth / 2}" y="${height - 5}" text-anchor="middle">${esc(label)}</text>` : ""}`;
    })
    .join("");
  return `<svg class="histogram" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Distribución">
    <defs><linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent-2)" stop-opacity=".55"/></linearGradient></defs>
    ${bars}
  </svg>`;
}

function histogramMean(histogram) {
  if (!histogram) return null;
  const counts = histogram.counts || [];
  const total = counts.reduce((sum, value) => sum + value, 0) || 1;
  return counts.reduce((sum, value, index) => sum + index * value, 0) / total;
}

function histogramMedian(histogram) {
  if (!histogram) return null;
  const counts = histogram.counts || [];
  const total = counts.reduce((sum, value) => sum + value, 0) || 1;
  let accumulated = 0;
  for (let index = 0; index < counts.length; index += 1) {
    accumulated += counts[index];
    if (accumulated >= total / 2) return index;
  }
  return null;
}

function histogramPercentile(histogram, percentile) {
  if (!histogram) return null;
  const counts = histogram.counts || [];
  const total = counts.reduce((sum, value) => sum + value, 0) || 1;
  let accumulated = 0;
  for (let index = 0; index < counts.length; index += 1) {
    accumulated += counts[index];
    if (accumulated >= total * percentile) return index;
  }
  return counts.length - 1;
}

function renderOverUnder(market) {
  const entries = Object.entries(market || {});
  if (!entries.length) return `<div class="chart-empty">Sin líneas disponibles.</div>`;
  return `<div class="bar-list" style="gap:9px">${entries
    .map(([line, values]) => {
      const over = Number(values?.over || 0);
      const under = Number(values?.under || 0);
      return `<div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="font-size:10px;font-weight:750;color:var(--text-soft)">Línea ${esc(line)}</span><span style="margin-left:auto;font-size:9px;color:var(--muted)">más ${esc(pct(over, 0))} · menos ${esc(pct(under, 0))}</span></div>
        <div class="comparison-bar" style="height:8px"><div class="home-fill" style="width:${over * 100}%"></div><div class="away-fill" style="width:${under * 100}%"></div></div>
      </div>`;
    })
    .join("")}</div>`;
}

function renderHeatmap(matrix, homeName, awayName) {
  if (!matrix || !matrix.probabilities?.length) {
    return `<div class="chart-empty">Sin matriz de marcadores.</div>`;
  }
  const labels = matrix.labels || [];
  const probabilities = matrix.probabilities || [];
  const max = Math.max(0.0001, ...probabilities.flat().map((value) => Number(value || 0)));
  const header = `<div class="heatmap-cell" style="background:transparent"></div>${labels.map((label) => `<div class="heatmap-cell" style="background:transparent;color:var(--faint);font-size:8px">${esc(label)}</div>`).join("")}`;
  const rows = probabilities
    .map((row, rowIndex) => {
      const rowLabel = `<div class="heatmap-cell" style="background:transparent;color:var(--faint);font-size:8px">${esc(labels[rowIndex] || rowIndex)}</div>`;
      const cells = row
        .map((value, columnIndex) => {
          const probability = Number(value || 0) / max;
          const alpha = 0.05 + probability * 0.86;
          const color = probability > 0.55 ? "#fff" : "var(--text)";
          return `<div class="heatmap-cell" style="background:color-mix(in srgb, var(--accent) ${Math.round(alpha * 100)}%, var(--surface-3));color:${color}" title="${esc(labels[rowIndex])}-${esc(labels[columnIndex])}: ${pct(value, 1)}">${value >= 0.005 ? (Number(value) * 100).toFixed(0) : "·"}</div>`;
        })
        .join("");
      return rowLabel + cells;
    })
    .join("");
  return `<div class="heatmap-wrap"><div class="heatmap" style="grid-template-columns:24px repeat(${labels.length},minmax(24px,1fr))">${header}${rows}</div>
    <div class="heatmap-axis"><span>${esc(shortName(homeName, 15))} ↓</span><span>${esc(shortName(awayName, 15))} →</span></div></div>`;
}

function renderValidation(actual, summary) {
  if (!actual) {
    return `<div class="chart-empty">Disponible para partidos finalizados o en vivo.</div>`;
  }
  const actualTotals = actual.totals || {};
  const mean = summary.totals?.mean || {};
  const percentiles = summary.totals?.percentiles || {};
  const live = actual.status === "live";
  const scale = live ? Math.min(1, Math.max(0, Number(actual.minute || 0) / 90)) : 1;
  const metrics = [
    ["goals", "Goles"],
    ["corners", "Córners"],
    ["cards", "Tarjetas"],
    ["shots", "Remates"],
    ["shots_on_target", "Al arco"],
    ["fouls", "Faltas"],
    ["saves", "Paradas"],
  ];
  const rows = metrics
    .map(([key, label]) => {
      const real = actualTotals[key];
      const simulated = mean[key];
      if (real === null || real === undefined || simulated === null || simulated === undefined) return "";
      const expected = Number(simulated) * scale;
      const p10 = percentiles[key]?.p10;
      const p90 = percentiles[key]?.p90;
      const low = p10 !== null && p10 !== undefined ? Number(p10) * scale : null;
      const high = p90 !== null && p90 !== undefined ? Number(p90) * scale : null;
      const inside = low !== null && high !== null && Number(real) >= low && Number(real) <= high;
      return `<tr><td>${esc(label)}</td><td class="num">${esc(fmtInt(real))}</td><td class="num">${esc(fmt(expected, 1))}</td><td class="num">${esc(signed(Number(real) - expected, 1))}</td><td class="num">${low !== null ? `${fmtInt(low)}–${fmtInt(high)}` : "—"}</td><td class="num"><span class="inside ${inside ? "yes" : "no"}">${inside ? "Sí" : "No"}</span></td></tr>`;
    })
    .join("");
  return `<div style="font-size:10.5px;color:var(--muted);margin-bottom:7px">${live ? `En vivo · minuto ${Math.round(actual.minute || 0)} · marcador ${esc(actual.score || "—")}` : `Resultado real: ${esc(actual.score || "—")}`}</div>
    <div style="overflow-x:auto"><table class="validation-table"><thead><tr><th scope="col">Métrica</th><th scope="col" class="num">Real</th><th scope="col" class="num">Esperado</th><th scope="col" class="num">Error</th><th scope="col" class="num">P10–P90</th><th scope="col" class="num">Dentro</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function runSimulation() {
  if (!state.selectedMatch || !state.analysis) return;
  const matchId = state.selectedMatch.id;
  const iterations = Number($("#simIterations")?.value || 10000);
  const seedValue = $("#simSeed")?.value?.trim();
  const seed = seedValue === "" ? null : Number(seedValue);
  if (!Number.isInteger(seed) && seed !== null) {
    toast("Semilla no válida", "Usa un número entero o deja el campo vacío.", "error");
    return;
  }
  const token = ++state.simToken;
  state.simulation = null;
  state.simJob = {
    status: "running",
    progress: { done: 0, total: 3, message: "Preparando la simulación…" },
  };
  setDetailBusy(true);
  renderDetail();
  setStatus(`Simulando ${iterations.toLocaleString("es-ES")} escenarios…`, "busy");
  try {
    const { job } = await api("/api/jobs/simulation", {
      method: "POST",
      body: {
        match_id: matchId,
        window: state.analysis.window ?? state.analysisWindow,
        iterations,
        seed,
        use_cache: true,
      },
    });
    const result = await pollJob(
      job.id,
      (current) => {
        if (token !== state.simToken) return;
        state.simJob = current;
        updateSimulationProgress(current);
      },
      () => token === state.simToken,
    );
    if (token !== state.simToken) return;
    state.simulation = result.summary;
    state.simJob = null;
    setDetailBusy(false);
    state.simMetric = "goals";
    state.simMarket = "goals";
    state.preview = null;
    renderDetail();
    setStatus(
      result.cached
        ? "Simulación cargada desde la caché."
        : "Simulación completada y guardada en el cuaderno.",
    );
    toast(
      result.cached ? "Simulación recuperada" : "Simulación completada",
      result.cached
        ? "Se reutilizó una simulación idéntica guardada en disco."
        : "El pronóstico se ha guardado automáticamente en el cuaderno.",
      "success",
    );
    state.journalLoaded = false;
    const summary = result.summary || {};
    const meta = summary.meta || {};
    const winner = summary.probabilities?.winner || {};
    if (meta.match_id !== null && meta.match_id !== undefined) {
      state.latestPredictions[String(meta.match_id)] = {
        match_id: meta.match_id,
        home_name: meta.home_team,
        away_name: meta.away_team,
        tournament: meta.tournament,
        day: String(meta.start_time || "").slice(0, 10),
        prob_home: winner.home,
        prob_draw: winner.draw,
        prob_away: winner.away,
        actual_status: summary.actual?.status || null,
        actual_score: summary.actual?.score || null,
      };
    }
    if (state.activeView === "live") renderLive();
  } catch (error) {
    if (token !== state.simToken) return;
    state.simJob = { status: "error", error: error.message };
    setDetailBusy(false);
    renderDetail();
    setStatus("No se pudo completar la simulación.", "error");
    toast("No se pudo simular", error.message, "error");
  }
}

function updateSimulationProgress(job) {
  const banner = $("#simulationProgress");
  if (!banner) return;
  const progress = job.progress || {};
  const percent = progress.total ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 8;
  const text = banner.querySelector(".sim-progress-top span:first-child");
  const value = banner.querySelector(".sim-progress-top span:last-child");
  const fill = banner.querySelector(".progress-fill");
  if (text) text.textContent = progress.message || "Simulando…";
  if (value) value.textContent = `${percent}%`;
  if (fill) fill.style.width = `${Math.max(6, percent)}%`;
  const track = banner.querySelector(".progress-track");
  track?.setAttribute("aria-valuenow", String(percent));
}

/* --------------------------------------------------------------------------
   Alineaciones y contexto
   -------------------------------------------------------------------------- */
function renderLineups() {
  const lineups = state.analysis?.lineups;
  const match = state.selectedMatch;
  if (!lineups) {
    return `<div class="empty-state compact"><div class="empty-icon">${icon("users")}</div><h2>Sin alineaciones</h2><p>El partido todavía no tiene alineaciones disponibles. Vuelve a analizarlo cuando se publiquen.</p><button class="soft-button" type="button" data-action="analyze">${icon("refresh")}Actualizar análisis</button></div>`;
  }
  const home = lineups.home || {};
  const away = lineups.away || {};
  const homePlayers = (home.players || []).filter((player) => !player.substitute);
  const awayPlayers = (away.players || []).filter((player) => !player.substitute);
  if (!homePlayers.length && !awayPlayers.length) {
    return `<div class="empty-state compact"><div class="empty-icon">${icon("users")}</div><h2>Alineaciones no publicadas</h2><p>Cuando el partido esté más cerca, aparecerán aquí.</p></div>`;
  }
  return `<div class="inline-note" style="margin-bottom:10px">${icon(lineups.confirmed ? "check" : "clock")}Alineación ${esc(lineups.confirmed ? "confirmada" : "probable")}</div>
    <div class="lineup-grid">
      ${renderLineupTeam(home, match?.home_team, homePlayers)}
      ${renderLineupTeam(away, match?.away_team, awayPlayers)}
    </div>`;
}

function renderLineupTeam(side, team, players) {
  const formation = side.formation || "—";
  return `<div class="lineup-team">
    <div class="lineup-team-head">${crest(team)}<strong>${esc(teamFullName(team))}</strong><span class="formation">${esc(formation)}</span></div>
    <div class="lineup-list">${players
      .map(
        (player) => `<div class="player-row"><span class="player-number">${esc(player.shirt_number ?? "—")}</span><span class="player-name">${esc(player.name || player.short_name || "Jugador")}${player.captain ? " ©" : ""}</span><span class="player-rating">${player.rating !== null && player.rating !== undefined ? esc(fmt(player.rating, 1)) : "—"}</span></div>`,
      )
      .join("")}</div>
  </div>`;
}

function renderContext() {
  const analysis = state.analysis || {};
  const match = state.selectedMatch || {};
  const referee = analysis.referee || {};
  const standings = analysis.standings || {};
  const h2h = analysis.h2h;
  const actual = analysis.actual;
  return `<div class="grid-2" style="align-items:start">
    <div class="card card-pad">
      <div class="section-title">${icon("whistle")}Arbitraje</div>
      <div class="info-list">
        ${infoRow("Árbitro", esc(referee.name || "Por designar"))}
        ${infoRow("Tarjetas/partido", esc(referee.cards_per_match !== null && referee.cards_per_match !== undefined ? fmt(referee.cards_per_match, 2) : "—"))}
        ${infoRow("Faltas/partido", esc(referee.fouls_per_match !== null && referee.fouls_per_match !== undefined ? fmt(referee.fouls_per_match, 2) : "—"))}
        ${infoRow("Partidos analizados", esc(referee.matches ?? "—"))}
      </div>
    </div>
    <div class="card card-pad">
      <div class="section-title">${icon("trophy")}Clasificación</div>
      ${standings.home || standings.away ? renderStandings(standings, match) : `<div class="empty-state compact"><p>No hay clasificación disponible para este partido.</p></div>`}
    </div>
  </div>
  <div class="grid-2" style="margin-top:10px;align-items:start">
    <div class="card card-pad">
      <div class="section-title">${icon("layers")}Historial directo</div>
      ${h2h ? `<div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:0">
        ${kpiCard("Gana local", fmtInt(h2h.home_wins), "veces", "var(--home)")}
        ${kpiCard("Empates", fmtInt(h2h.draws), "veces", "var(--faint)")}
        ${kpiCard("Gana visitante", fmtInt(h2h.away_wins), "veces", "var(--away)")}
      </div><div class="inline-note" style="margin-top:7px">${icon("info")}${esc(h2h.matches)} partidos registrados</div>` : `<div class="empty-state compact"><p>Sin historial directo disponible.</p></div>`}
    </div>
    <div class="card card-pad">
      <div class="section-title">${icon("target")}Resultado y estadísticas reales</div>
      ${actual ? `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span class="hero-score" style="font-size:28px">${esc(actual.score || "—")}</span><span class="hero-status ${actual.status === "live" ? "live" : "finished"}">${esc(actual.status === "live" ? `En vivo ${Math.round(actual.minute || 0)}'` : "Finalizado")}</span></div>${renderActualStats(actual)}` : `<div class="empty-state compact"><p>Disponible cuando el partido haya empezado.</p></div>`}
    </div>
  </div>
  ${renderWarnings(analysis.warnings)}`;
}

function renderStandings(standings, match) {
  const rows = [
    ["home", match.home_team, "Local"],
    ["away", match.away_team, "Visitante"],
  ];
  return `<table class="validation-table"><thead><tr><th scope="col">Equipo</th><th scope="col" class="num">Pos.</th><th scope="col" class="num">Pts</th><th scope="col" class="num">PJ</th><th scope="col" class="num">DG</th><th scope="col" class="num">Pts/PJ</th></tr></thead><tbody>${rows
    .map(([side, team, fallback]) => {
      const data = standings[side];
      if (!data) return `<tr><td>${esc(teamFullName(team) || fallback)}</td><td colspan="5" class="muted">Sin datos</td></tr>`;
      return `<tr><td>${esc(teamFullName(team) || fallback)}</td><td class="num">${esc(data.position ?? "—")}</td><td class="num">${esc(data.points ?? "—")}</td><td class="num">${esc(data.matches ?? "—")}</td><td class="num">${esc(data.goal_difference ?? "—")}</td><td class="num">${esc(fmt(data.points_per_game, 2))}</td></tr>`;
    })
    .join("")}</tbody></table>`;
}

function renderActualStats(actual) {
  const totals = actual.totals || {};
  const rows = [
    ["Goles", totals.goals],
    ["Remates", totals.shots],
    ["Al arco", totals.shots_on_target],
    ["Córners", totals.corners],
    ["Tarjetas", totals.cards],
    ["Faltas", totals.fouls],
    ["Paradas", totals.saves],
  ].filter(([, value]) => value !== null && value !== undefined);
  return `<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:5px">${rows
    .map(
      ([label, value]) =>
        `<div style="display:flex;justify-content:space-between;font-size:10.5px;padding:4px 0;border-bottom:1px solid var(--border);color:var(--muted)"><span>${esc(label)}</span><strong style="color:var(--text-soft)">${esc(fmtInt(value))}</strong></div>`,
    )
    .join("")}</div>`;
}

/* --------------------------------------------------------------------------
   Previa
   -------------------------------------------------------------------------- */
async function generatePreview() {
  if (!state.selectedMatch) return;
  let analysis = state.analysis;
  if (!analysis) analysis = await analyzeMatch();
  if (!analysis) return;
  setStatus("Generando la previa…", "busy");
  try {
    const payload = await api(
      `/api/preview?id=${encodeURIComponent(state.selectedMatch.id)}&window=${encodeURIComponent(analysis.window ?? state.analysisWindow)}`,
    );
    state.preview = payload;
    setView("previews");
    renderPreviews();
    setStatus("Previa generada.");
    toast("Previa lista", "Puedes copiarla, descargarla o abrirla en el navegador.", "success");
  } catch (error) {
    toast("No se pudo generar la previa", error.message, "error");
    setStatus("Error al generar la previa.", "error");
  }
}

function renderPreviews() {
  const preview = state.preview;
  const frame = $("#previewFrame");
  const empty = $("#previewEmpty");
  const title = $("#previewTitle");
  const badge = $("#previewBadge");
  const actions = ["#previewCopy", "#previewDownloadMd", "#previewDownloadHtml", "#previewOpen"];
  if (!preview) {
    if (title) title.textContent = "Sin previa generada";
    if (badge) {
      badge.textContent = "—";
      badge.hidden = true;
    }
    if (frame) frame.srcdoc = "";
    if (empty) {
      empty.hidden = false;
      empty.innerHTML = state.selectedMatch
        ? `<div class="empty-icon">${icon("file")}</div><h2>Genera una previa</h2><p>Has seleccionado <strong>${esc(teamFullName(state.selectedMatch.home_team))} vs ${esc(teamFullName(state.selectedMatch.away_team))}</strong>. Analiza el partido y pulsa el botón.</p><button class="primary-button" type="button" id="previewGenerateButton">${icon("sparkles")}Generar previa</button>`
        : `<div class="empty-icon">${icon("file")}</div><h2>Genera una previa</h2><p>Abre un partido y pulsa <strong>Generar previa</strong>. También puedes hacerlo desde la ficha del partido.</p>`;
    }
    actions.forEach((selector) => {
      const button = $(selector);
      if (button) button.disabled = true;
    });
    const generate = $("#previewGenerateButton");
    if (generate) generate.addEventListener("click", generatePreview);
    return;
  }
  if (empty) empty.hidden = true;
  if (frame) frame.srcdoc = preview.html || "";
  if (title) title.textContent = `${preview.home} vs ${preview.away}`;
  if (badge) {
    badge.textContent = preview.tournament || "Previa";
    badge.hidden = false;
  }
  actions.forEach((selector) => {
    const button = $(selector);
    if (button) button.disabled = false;
  });
}

async function copyPreviewMarkdown() {
  if (!state.preview?.markdown) return;
  try {
    await navigator.clipboard.writeText(state.preview.markdown);
    toast("Copiado", "El Markdown está en el portapapeles.", "success");
  } catch {
    toast("No se pudo copiar", "El navegador bloqueó el portapapeles.", "error");
  }
}

function downloadPreview(kind) {
  if (!state.preview) return;
  const name = `${state.preview.home}_vs_${state.preview.away}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (kind === "md") {
    downloadBlob(
      new Blob([state.preview.markdown || ""], { type: "text/markdown;charset=utf-8" }),
      `previa_${name || "partido"}.md`,
    );
  } else {
    downloadBlob(
      new Blob([state.preview.html || ""], { type: "text/html;charset=utf-8" }),
      `previa_${name || "partido"}.html`,
    );
  }
}

async function openPreviewInBrowser() {
  const matchId = state.preview?.analysis_meta?.match_id || state.selectedMatch?.id;
  if (!matchId) return;
  try {
    const result = await api("/api/preview/open", {
      method: "POST",
      body: {
        match_id: matchId,
        window: state.preview?.analysis_meta?.window ?? state.analysis?.window ?? state.analysisWindow,
      },
    });
    toast("Abriendo en el navegador", result.opened || "Previa HTML generada.", "info");
  } catch (error) {
    toast("No se pudo abrir", error.message, "error");
  }
}

/* --------------------------------------------------------------------------
   Sala de directo
   -------------------------------------------------------------------------- */
function renderLive() {
  const grid = $("#liveGrid");
  const empty = $("#liveEmpty");
  if (!grid) return;
  let matches = mergeMatches(state.matches, Object.values(state.liveExtras || {}));
  if (state.liveFilter === "live") matches = matches.filter(isLive);
  else if (state.liveFilter === "favorites") matches = matches.filter((match) => teamMatchesFavorite(match));
  matches.sort(
    (a, b) =>
      statusRank(a) - statusRank(b) ||
      (a.start_timestamp || 0) - (b.start_timestamp || 0),
  );
  const shown = matches.slice(0, 48);
  grid.innerHTML = shown.map(renderLiveCard).join("");
  if (empty) empty.hidden = shown.length > 0;
  const updated = $("#liveUpdated");
  if (updated) {
    updated.textContent = state.lastLiveAt
      ? `Actualizado ${new Date(state.lastLiveAt).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`
      : "Esperando datos…";
  }
  updateControlStates();
}

function renderLiveCard(match) {
  const live = isLive(match);
  const finished = isFinished(match);
  const prediction = state.latestPredictions[String(match.id)];
  const pick = prediction ? predictionPick(prediction) : null;
  const status = statusInfo(match);
  const className = live ? "" : finished ? "finished" : "upcoming";
  return `<article class="live-card ${className}" data-open-match="${esc(match.id)}" style="cursor:pointer">
    <div class="live-card-top">
      ${flag(match.tournament?.category_id, match.tournament?.category)}
      <span class="live-card-league">${esc(match.tournament?.name || "Competición")}</span>
      <span class="live-card-time">${esc(live ? status.short : finished ? "Final" : formatTime(match.start_timestamp))}</span>
    </div>
    <div class="live-card-teams">
      <div class="live-team home">${crest(match.home_team)}<span class="live-team-name">${esc(teamName(match.home_team))}</span></div>
      <div class="live-score ${live ? "live" : ""}">${esc(scoreShort(match))}</div>
      <div class="live-team away">${crest(match.away_team)}<span class="live-team-name">${esc(teamName(match.away_team))}</span></div>
    </div>
    <div class="live-card-bottom">
      ${pick ? `<span class="probability-pill">${esc(pick.name)} · ${esc(pct(pick.probability, 0))}</span>` : `<span class="probability-pill" style="background:var(--surface-3);color:var(--muted)">Sin pronóstico</span>`}
      <span class="live-card-actions"><button class="soft-button" type="button" data-open-match="${esc(match.id)}" style="height:28px;font-size:10px;padding:0 9px">Abrir</button></span>
    </div>
  </article>`;
}

async function refreshLive({ silent = false } = {}) {
  if (state.liveLoading) return;
  const liveIds = mergeMatches(state.matches, Object.values(state.liveExtras || {}))
    .filter(isLive)
    .map((match) => match.id);
  if (!liveIds.length && !state.matches.length) return;
  state.liveLoading = true;
  try {
    const data = await api(`/api/live?ids=${encodeURIComponent(liveIds.join(","))}`);
    const updates = data.matches || [];
    if (updates.length) {
      checkAlerts(updates);
      updates.forEach((update) => {
        const index = state.matches.findIndex((match) => match.id === update.id);
        if (index >= 0) {
          state.matches[index] = { ...state.matches[index], ...update };
          state.matchesById.set(update.id, {
            ...(state.matchesById.get(update.id) || {}),
            ...update,
          });
        } else {
          state.liveExtras[String(update.id)] = {
            ...(state.liveExtras[String(update.id)] || {}),
            ...update,
          };
        }
      });
      if (state.selectedId !== null) {
        const selected =
          state.matchesById.get(Number(state.selectedId)) ||
          state.liveExtras[String(state.selectedId)];
        if (selected) state.selectedMatch = { ...state.selectedMatch, ...selected };
      }
      state.lastLiveAt = Date.now();
      const finishedUpdate = updates.some((update) => update.status_type === "finished");
      if (finishedUpdate) {
        state.journalLoaded = false;
        if (state.activeView === "journal") loadJournal(true).catch(() => {});
        if (state.activeView === "explorer") loadExplorer().catch(() => {});
      }
      renderMatches();
      if (state.selectedId !== null) renderDetail();
      if (state.activeView === "live") renderLive();
      if (!silent) setStatus(`En vivo actualizado · ${updates.length} partido${updates.length === 1 ? "" : "s"}.`);
    } else if (!silent) {
      setStatus("Sin cambios en los partidos en vivo.");
    }
  } catch (error) {
    if (!silent) {
      toast("No se pudo actualizar el directo", error.message, "error");
      setStatus("Error al actualizar el directo.", "error");
    }
  } finally {
    state.liveLoading = false;
  }
}

function checkAlerts(updates) {
  if (!state.prefs.alerts) return;
  let changed = false;
  updates.forEach((update) => {
    const key = String(update.id);
    const previous = state.lastScores[key];
    const current = {
      h: update.home_score,
      a: update.away_score,
      s: update.status_type,
    };
    if (
      previous &&
      (previous.h !== current.h || previous.a !== current.a || previous.s !== current.s)
    ) {
      const favorite = favoriteName(update);
      if (favorite) {
        const score = scoreShort(update);
        const live = isLive(update);
        toast(
          live ? "Gol o cambio en directo" : "Resultado final",
          `${favorite} · ${teamName(update.home_team)} ${score} ${teamName(update.away_team)}`,
          live ? "warn" : "success",
          7000,
        );
        if ("Notification" in window && Notification.permission === "granted") {
          try {
            new Notification(`SofaScore · ${favorite}`, {
              body: `${teamName(update.home_team)} ${score} ${teamName(update.away_team)}`,
            });
          } catch {
            /* ignore */
          }
        }
      }
    }
    state.lastScores[key] = current;
    changed = true;
  });
  if (changed) {
    try {
      localStorage.setItem("sofascore:lastScores", JSON.stringify(state.lastScores));
    } catch {
      /* ignore */
    }
  }
}

let liveTimer = null;
function startLiveLoop() {
  if (liveTimer) clearInterval(liveTimer);
  liveTimer = setInterval(() => {
    if (!state.prefs.auto_live) return;
    if (state.activeView === "live" || state.activeView === "matches") {
      refreshLive({ silent: true });
    }
  }, 45000);
}

/* --------------------------------------------------------------------------
   Cuaderno de predicciones
   -------------------------------------------------------------------------- */
async function loadJournal(force = false) {
  if (state.journalLoaded && !force) {
    renderJournal();
    return;
  }
  setStatus("Cargando el cuaderno…", "busy");
  const panel = $("#journalBody")?.closest(".panel");
  panel?.setAttribute("aria-busy", "true");
  try {
    const [predictions, accuracy] = await Promise.all([
      api("/api/predictions?limit=1000"),
      api("/api/accuracy"),
    ]);
    state.predictions = predictions.predictions || [];
    state.accuracy = accuracy || {};
    state.latestPredictions = {};
    state.predictions.forEach((prediction) => {
      if (!state.latestPredictions[String(prediction.match_id)]) {
        state.latestPredictions[String(prediction.match_id)] = prediction;
      }
    });
    state.journalLoaded = true;
    renderJournal();
    panel?.setAttribute("aria-busy", "false");
    setStatus(
      state.predictions.length === 1
        ? "1 predicción en el cuaderno."
        : `${state.predictions.length} predicciones en el cuaderno.`,
    );
  } catch (error) {
    panel?.setAttribute("aria-busy", "false");
    toast("No se pudo cargar el cuaderno", error.message, "error");
    setStatus("Error al cargar el cuaderno.", "error");
  }
}

function renderJournal() {
  const body = $("#journalBody");
  if (!body) return;
  const accuracy = state.accuracy || {};
  const kpis = $("#journalKpis");
  if (kpis) {
    const resolved = accuracy.total || 0;
    kpis.innerHTML = [
      kpiCard("Predicciones", fmtInt(state.predictions.length), state.predictions.length === 1 ? "guardada" : "guardadas", "var(--accent)"),
      kpiCard("Resueltas", fmtInt(resolved), "con resultado", "var(--good)"),
      kpiCard("Acierto 1X2", resolved ? pct(accuracy.accuracy, 1) : "—", "resultado exacto", "var(--home)"),
      kpiCard("Brier", resolved ? fmt(accuracy.brier, 3) : "—", "menor es mejor", "var(--warn)"),
      kpiCard("MAE goles", resolved ? fmt(accuracy.goal_mae, 2) : "—", "error medio", "var(--accent-2)"),
    ].join("");
  }
  const query = normalizeText($("#journalSearch")?.value || "");
  const filter = $("#journalStatus")?.value || "all";
  const rows = state.predictions.filter((prediction) => {
    const resolved = predictionResolved(prediction);
    const hit = predictionHit(prediction);
    if (filter === "resolved" && !resolved) return false;
    if (filter === "pending" && resolved) return false;
    if (filter === "hit" && hit !== true) return false;
    if (filter === "miss" && hit !== false) return false;
    if (!query) return true;
    return normalizeText(
      [prediction.home_name, prediction.away_name, prediction.tournament, prediction.actual_score].join(" "),
    ).includes(query);
  });
  body.innerHTML = rows.length
    ? rows
        .map((prediction) => {
          const pick = predictionPick(prediction);
          const resolved = predictionResolved(prediction);
          const hit = predictionHit(prediction);
          const status = resolved
            ? `<span class="result-pill ${hit ? "hit" : "miss"}">${hit ? "Acertada" : "Fallada"}</span>`
            : `<span class="result-pill pending">Pendiente</span>`;
          return `<tr data-open-match="${esc(prediction.match_id)}">
            <td><span class="muted">${esc(formatPredictionDate(prediction.created_at))}</span></td>
            <td><div class="match-name">${esc(prediction.home_name || "Local")} vs ${esc(prediction.away_name || "Visitante")}</div><span class="muted">${esc(formatDate(prediction.day))}</span></td>
            <td>${esc(prediction.tournament || "—")}</td>
            <td>${pick ? `<span class="probability-pill">${esc(pick.name)} · ${esc(pct(pick.probability, 0))}</span>` : "—"}</td>
            <td class="num">${pick ? esc(pct(pick.probability, 0)) : "—"}</td>
            <td class="num"><span class="score-pill ${prediction.actual_status === "finished" ? "finished" : prediction.actual_status === "live" ? "live" : ""}">${esc(prediction.actual_score || "—")}</span></td>
            <td>${status}</td>
            <td><button class="row-action" type="button" data-open-match="${esc(prediction.match_id)}" title="Abrir partido" aria-label="Abrir partido">${icon("external")}</button></td>
          </tr>`;
        })
        .join("")
    : `<tr><td colspan="8"><div class="empty-state compact"><div class="empty-icon">${icon("notebook")}</div><h2>Sin predicciones</h2><p>Analiza un partido y ejecuta una simulación para que aparezca aquí.</p></div></td></tr>`;
  const count = $("#journalCount");
  if (count) count.textContent = `${rows.length} de ${state.predictions.length}`;
  const footer = $("#journalFooter");
  if (footer) footer.textContent = `${state.predictions.length} predicción${state.predictions.length === 1 ? "" : "es"} · Base de datos: ${state.boot?.storage?.path || "—"}`;
}

function formatPredictionDate(timestamp) {
  if (!timestamp) return "—";
  try {
    return new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(Number(timestamp) * 1000));
  } catch {
    return "—";
  }
}

function predictionPick(prediction) {
  if (!prediction) return null;
  const probabilities = {
    home: Number(prediction.prob_home || 0),
    draw: Number(prediction.prob_draw || 0),
    away: Number(prediction.prob_away || 0),
  };
  const side = Object.keys(probabilities).reduce((best, key) => probabilities[key] > probabilities[best] ? key : best, "home");
  const name = side === "home" ? prediction.home_name || "Local" : side === "away" ? prediction.away_name || "Visitante" : "Empate";
  return { side, name, probability: probabilities[side] };
}

function predictionResolved(prediction) {
  return Boolean(prediction?.actual_score) && prediction?.actual_status === "finished";
}

function predictionHit(prediction) {
  if (!predictionResolved(prediction)) return null;
  const score = String(prediction.actual_score || "");
  const match = /^(\d+)\s*-\s*(\d+)$/.exec(score);
  if (!match) return null;
  const home = Number(match[1]);
  const away = Number(match[2]);
  const actualSide = home > away ? "home" : away > home ? "away" : "draw";
  return predictionPick(prediction)?.side === actualSide;
}

/* --------------------------------------------------------------------------
   Explorador
   -------------------------------------------------------------------------- */
async function loadExplorer() {
  setStatus("Cargando el explorador…", "busy");
  const panel = $("#explorerBody")?.closest(".panel");
  panel?.setAttribute("aria-busy", "true");
  try {
    const [matches, predictions] = await Promise.all([
      api(`/api/history/matches?${new URLSearchParams({ query: state.explorerQuery, status: state.explorerStatus, limit: "500" }).toString()}`),
      api("/api/predictions?limit=1000"),
    ]);
    state.explorerMatches = matches.matches || [];
    const latest = {};
    (predictions.predictions || []).forEach((prediction) => {
      if (!latest[String(prediction.match_id)]) latest[String(prediction.match_id)] = prediction;
    });
    state.latestPredictions = { ...state.latestPredictions, ...latest };
    state.explorerLoaded = true;
    renderExplorer();
    panel?.setAttribute("aria-busy", "false");
    setStatus(`${state.explorerMatches.length} partidos en el historial local.`);
  } catch (error) {
    panel?.setAttribute("aria-busy", "false");
    toast("No se pudo cargar el explorador", error.message, "error");
    setStatus("Error al cargar el explorador.", "error");
  }
}

function renderExplorer() {
  const body = $("#explorerBody");
  if (!body) return;
  body.innerHTML = state.explorerMatches.length
    ? state.explorerMatches
        .map((match) => {
          const prediction = state.latestPredictions[String(match.id)];
          const pick = prediction ? predictionPick(prediction) : null;
          const status = match.status === "finished" ? "Finalizado" : match.status === "inprogress" ? "En vivo" : match.status === "notstarted" ? "Próximo" : match.status || "—";
          return `<tr data-open-match="${esc(match.id)}">
            <td>${esc(formatDate(match.day))}</td>
            <td>${esc(match.tournament || "—")}</td>
            <td><div class="team-cell">${crest({ id: match.home_id, name: match.home_name })}<span class="match-name">${esc(match.home_name || "—")}</span></div></td>
            <td><div class="team-cell">${crest({ id: match.away_id, name: match.away_name })}<span class="match-name">${esc(match.away_name || "—")}</span></div></td>
            <td class="num"><span class="score-pill ${match.status === "finished" ? "finished" : match.status === "inprogress" ? "live" : ""}">${match.home_score !== null && match.home_score !== undefined ? `${esc(match.home_score)}-${esc(match.away_score)}` : "—"}</span></td>
            <td>${esc(status)}</td>
            <td>${pick ? `<span class="probability-pill">${esc(pick.name)} · ${esc(pct(pick.probability, 0))}</span>` : "—"}</td>
            <td><button class="row-action" type="button" data-open-match="${esc(match.id)}" title="Abrir partido" aria-label="Abrir partido">${icon("external")}</button></td>
          </tr>`;
        })
        .join("")
    : `<tr><td colspan="8"><div class="empty-state compact"><div class="empty-icon">${icon("compass")}</div><h2>Sin partidos guardados</h2><p>Los partidos aparecen aquí al cargar una fecha o analizarlos.</p></div></td></tr>`;
  const count = $("#explorerCount");
  if (count) count.textContent = `${state.explorerMatches.length} partidos`;
  const footer = $("#explorerFooter");
  if (footer) footer.textContent = `Base de datos: ${state.boot?.storage?.path || "—"}`;
  const apiUrl = $("#apiUrl");
  if (apiUrl) apiUrl.textContent = `${location.origin}`;
}

async function clearHistory() {
  const modal = openModal({
    title: "Borrar historial",
    subtitle: "Esta acción no se puede deshacer.",
    body: `<div class="warning-box">${icon("alert")}<div>Se eliminarán los partidos, análisis y predicciones guardadas en este equipo. Las preferencias y los favoritos se conservan.</div></div>`,
    footer: `<button class="soft-button" type="button" data-close-modal>Cancelar</button><button class="danger-button" type="button" id="confirmClearHistory">${icon("trash")}Borrar historial</button>`,
  });
  $("#confirmClearHistory", modal)?.addEventListener("click", async () => {
    try {
      await api("/api/history", { method: "DELETE" });
      state.predictions = [];
      state.latestPredictions = {};
      state.explorerMatches = [];
      state.journalLoaded = false;
      state.explorerLoaded = false;
      closeModal();
      renderJournal();
      renderExplorer();
      toast("Historial borrado", "La base de datos local está vacía.", "success");
      setStatus("Historial local eliminado.");
    } catch (error) {
      toast("No se pudo borrar", error.message, "error");
    }
  });
}

/* --------------------------------------------------------------------------
   Modelo
   -------------------------------------------------------------------------- */
async function loadModel() {
  const container = $("#modelContent");
  container?.setAttribute("aria-busy", "true");
  try {
    const payload = await api("/api/model");
    state.model = payload;
    updateModelMini();
    renderModel();
    container?.setAttribute("aria-busy", "false");
  } catch (error) {
    container?.setAttribute("aria-busy", "false");
    toast("No se pudo cargar el modelo", error.message, "error");
  }
}

function renderModel() {
  const container = $("#modelContent");
  if (!container) return;
  const model = state.model || {};
  const metrics = model.metrics || {};
  if (!metrics || !Object.keys(metrics).length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">${icon("brain")}</div><h2>Modelo no disponible</h2><p>No se encontraron las métricas de entrenamiento.</p></div>`;
    return;
  }
  const targets = model.targets || [];
  const maeRows = targets
    .map((target) => {
      const neural = Number(target.neural);
      const baseline = Number(target.baseline);
      if (!Number.isFinite(neural) && !Number.isFinite(baseline)) return "";
      const better = Number.isFinite(neural) && Number.isFinite(baseline) ? neural < baseline : null;
      return `<tr><td>${esc(target.label)}</td><td class="num">${esc(fmt(neural, 3))}</td><td class="num">${esc(fmt(baseline, 3))}</td><td class="num ${better === true ? "better" : better === false ? "worse" : ""}">${better === null ? "—" : better ? "Mejor" : "Peor"}</td></tr>`;
    })
    .join("");
  const blends = Object.entries(model.blend_weights || {}).filter(([, value]) => Number(value) > 0);
  const hidden = metrics.hidden || [];
  container.innerHTML = `<div class="model-grid">
    <div class="model-hero">
      <p class="eyebrow">Modelo activo</p>
      <h2>Versión ${esc(String(model.version || "—").split(":")[0])}</h2>
      <p>Red neuronal multicapa entrenada con NumPy. Se usa como apoyo del simulador; la decisión final sigue siendo probabilística.</p>
      <div class="model-stats">
        <div class="model-stat"><span>Entrenado</span><strong style="font-size:12px">${esc(formatModelDate(metrics.trained_at))}</strong></div>
        <div class="model-stat"><span>Muestras</span><strong>${esc(fmtInt((metrics.train || 0) + (metrics.validation || 0) + (metrics.test || 0)))}</strong></div>
        <div class="model-stat"><span>Ensemble</span><strong>${esc(metrics.ensemble ?? "—")}</strong></div>
        <div class="model-stat"><span>Capas</span><strong>${esc(hidden.length ? hidden.join(" · ") : "—")}</strong></div>
        <div class="model-stat"><span>Validación</span><strong>${esc(fmtInt(metrics.validation || 0))}</strong></div>
        <div class="model-stat"><span>Test</span><strong>${esc(fmtInt(metrics.test || 0))}</strong></div>
      </div>
    </div>
    <div class="card card-pad">
      <div class="section-title">${icon("chart")}Error por mercado</div>
      <div style="overflow-x:auto"><table class="mae-table"><thead><tr><th scope="col">Mercado</th><th scope="col" class="num">Red</th><th scope="col" class="num">Base</th><th scope="col" class="num">Resultado</th></tr></thead><tbody>${maeRows || '<tr><td colspan="4">Sin métricas.</td></tr>'}</tbody></table></div>
      <div class="inline-note" style="margin-top:8px">${icon("info")}MAE: error absoluto medio. Cuanto menor, mejor.</div>
    </div>
  </div>
  <div class="grid-2" style="margin-top:14px;align-items:start">
    <div class="card card-pad">
      <div class="section-title">${icon("layers")}Peso de la red por mercado</div>
      ${blends.length ? `<div class="blend-list">${blends.map(([key, value]) => `<div class="blend-row"><span>${esc(friendlyTarget(key))}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, Number(value) * 100)}%"></div></div><span style="text-align:right;color:var(--muted)">${esc(pct(value, 0))}</span></div>`).join("")}</div>` : `<div class="empty-state compact"><p>Sin pesos de mezcla.</p></div>`}
    </div>
    <div class="card card-pad">
      <div class="section-title">${icon("zap")}Cómo se usa</div>
      <div class="info-list">
        ${infoRow("1. Análisis", "Se construyen las features con los partidos anteriores al encuentro, sin fuga de información.")}
        ${infoRow("2. Simulación", "Monte Carlo combina la forma, las alineaciones y el árbitro con la salida de la red.")}
        ${infoRow("3. Cuaderno", "Cada pronóstico se guarda y se compara con el resultado real para medir el acierto.")}
      </div>
    </div>
  </div>`;
}

function formatModelDate(value) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
  } catch {
    return String(value);
  }
}

function friendlyTarget(key) {
  return key
    .replace(/^home_/, "Local · ")
    .replace(/^away_/, "Visitante · ")
    .replace("goals", "goles")
    .replace("shots_on_target", "al arco")
    .replace("shots", "remates")
    .replace("corners", "córners")
    .replace("cards", "tarjetas")
    .replace("fouls", "faltas");
}

/* --------------------------------------------------------------------------
   Ajustes y ayuda
   -------------------------------------------------------------------------- */
function openSettings() {
  const prefs = state.prefs;
  const modal = openModal({
    title: "Ajustes",
    subtitle: "Preferencias compartidas con el modo clásico.",
    wide: true,
    body: `<div class="settings-section">
      <h3>Apariencia</h3>
      <div class="theme-grid" id="settingsThemeGrid">${renderThemeCards(state.theme)}</div>
      <div class="setting-row" style="margin-top:6px">
        <div class="setting-copy"><strong>Analizar al abrir</strong><span>Lanza el análisis automáticamente al seleccionar un partido.</span></div>
        <label class="switch"><input type="checkbox" id="settingAutoAnalyze" aria-label="Analizar al abrir" ${prefs.auto_analyze !== false ? "checked" : ""}><span></span></label>
      </div>
    </div>
    <div class="settings-section">
      <h3>Datos y directo</h3>
      <div class="setting-row">
        <div class="setting-copy"><strong>Zona horaria</strong><span>Se aplica a las horas y a la fecha de los partidos.</span></div>
        <select class="settings-select" id="settingTimezone" aria-label="Zona horaria">${(state.boot?.timezones || []).map((timezone) => `<option value="${esc(timezone)}" ${timezone === state.timezone ? "selected" : ""}>${esc(timezone)}</option>`).join("")}</select>
      </div>
      <div class="setting-row">
        <div class="setting-copy"><strong>Región</strong><span>Europa, Sudamérica o ambas.</span></div>
        <select class="settings-select" id="settingRegion" aria-label="Región">${(state.boot?.regions || []).map((region) => `<option value="${esc(region.key)}" ${region.key === state.region ? "selected" : ""}>${esc(region.label)}</option>`).join("")}</select>
      </div>
      <div class="setting-row">
        <div class="setting-copy"><strong>Competiciones</strong><span>Principales o todas las disponibles.</span></div>
        <select class="settings-select" id="settingCompetitions" aria-label="Competiciones">${(state.boot?.competitions || []).map((competition) => `<option value="${esc(competition.key)}" ${competition.key === state.competitions ? "selected" : ""}>${esc(competition.label)}</option>`).join("")}</select>
      </div>
      <div class="setting-row">
        <div class="setting-copy"><strong>Auto en vivo</strong><span>Actualiza los marcadores cada 45 segundos.</span></div>
        <label class="switch"><input type="checkbox" id="settingAutoLive" aria-label="Actualización automática en vivo" ${prefs.auto_live !== false ? "checked" : ""}><span></span></label>
      </div>
      <div class="setting-row">
        <div class="setting-copy"><strong>Alertas de favoritos</strong><span>Avisa cuando cambia el marcador de un equipo favorito.</span></div>
        <label class="switch"><input type="checkbox" id="settingAlerts" aria-label="Alertas de favoritos" ${prefs.alerts !== false ? "checked" : ""}><span></span></label>
      </div>
    </div>
    <div class="settings-section">
      <h3>Almacenamiento</h3>
      <div class="setting-row">
        <div class="setting-copy"><strong>Base de datos</strong><span style="word-break:break-all">${esc(state.boot?.storage?.path || "No disponible")}</span></div>
        <button class="soft-button" type="button" id="settingOpenFolder">${icon("folder")}Abrir</button>
      </div>
    </div>
    <div class="settings-section">
      <h3>Atajos</h3>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 16px">${(state.boot?.shortcuts || []).map((shortcut) => `<div style="display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--border);font-size:11px"><span style="color:var(--muted)">${esc(shortcut.action)}</span><kbd style="font-family:inherit;font-size:9px;color:var(--faint)">${esc(shortcut.keys)}</kbd></div>`).join("")}</div>
    </div>`,
    footer: `<span class="left" style="font-size:10px;color:var(--faint)">SofaScore v${esc(state.boot?.version || "")}</span><button class="primary-button" type="button" data-close-modal>Listo</button>`,
  });
  bindThemeCards($("#settingsThemeGrid", modal));
  $("#settingAutoAnalyze", modal)?.addEventListener("change", (event) => {
    state.prefs.auto_analyze = event.target.checked;
    api("/api/preferences", { method: "POST", body: { auto_analyze: event.target.checked } }).catch(() => {});
  });
  $("#settingTimezone", modal)?.addEventListener("change", (event) => {
    state.timezone = event.target.value;
    state.prefs.timezone = event.target.value;
    state.settingsNeedsReload = true;
    api("/api/preferences", { method: "POST", body: { timezone: event.target.value } }).catch(() => {});
  });
  $("#settingRegion", modal)?.addEventListener("change", (event) => {
    state.region = event.target.value;
    state.prefs.region = event.target.value;
    state.settingsNeedsReload = true;
    $("#regionSelect").value = state.region;
    api("/api/preferences", { method: "POST", body: { region: event.target.value } }).catch(() => {});
  });
  $("#settingCompetitions", modal)?.addEventListener("change", (event) => {
    state.competitions = event.target.value;
    state.prefs.competitions = event.target.value;
    state.settingsNeedsReload = true;
    $("#competitionSelect").value = state.competitions;
    api("/api/preferences", { method: "POST", body: { competitions: event.target.value } }).catch(() => {});
  });
  $("#settingAutoLive", modal)?.addEventListener("change", (event) => {
    state.prefs.auto_live = event.target.checked;
    api("/api/preferences", { method: "POST", body: { auto_live: event.target.checked } }).catch(() => {});
  });
  $("#settingAlerts", modal)?.addEventListener("change", async (event) => {
    state.prefs.alerts = event.target.checked;
    api("/api/preferences", { method: "POST", body: { alerts: event.target.checked } }).catch(() => {});
    if (event.target.checked && "Notification" in window && Notification.permission === "default") {
      try {
        await Notification.requestPermission();
      } catch {
        /* ignore */
      }
    }
  });
  $("#settingOpenFolder", modal)?.addEventListener("click", async () => {
    try {
      const result = await api("/api/open-folder", { method: "POST", body: {} });
      toast("Carpeta abierta", result.opened, "info");
    } catch (error) {
      toast("No se pudo abrir", error.message, "error");
    }
  });
}

function openHelp() {
  openModal({
    title: "Ayuda y atajos",
    subtitle: "Todo lo que puedes hacer desde el teclado.",
    wide: true,
    body: `<div class="settings-section">
      <h3>Atajos principales</h3>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 16px">${(state.boot?.shortcuts || []).map((shortcut) => `<div style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px"><span style="color:var(--muted)">${esc(shortcut.action)}</span><kbd style="font-family:inherit;font-size:9px;color:var(--faint)">${esc(shortcut.keys)}</kbd></div>`).join("")}</div>
    </div>
    <div class="settings-section">
      <h3>Consejos</h3>
      <div class="info-list">
        ${infoRow("Favoritos", "Pasa el ratón por un partido y pulsa la estrella. El filtro ★ Favoritos y las alertas usan esa lista.")}
        ${infoRow("Análisis", "La ventana de forma se puede cambiar entre 5, 10, 15 partidos o toda la temporada.")}
        ${infoRow("Simulación", "10.000 escenarios es un buen equilibrio. Usa la misma semilla para comparar escenarios.")}
        ${infoRow("Previa", "El HTML se abre en el navegador y se puede imprimir como PDF con Ctrl+P.")}
      </div>
    </div>
    <div class="settings-section">
      <h3>Acerca de</h3>
      <p style="font-size:11px;color:var(--muted);margin:0">SofaScore · Análisis de forma v${esc(state.boot?.version || "")}. Datos de la API interna de SofaScore. Uso personal; las probabilidades no son una garantía de resultado.</p>
    </div>`,
    footer: `<button class="primary-button" type="button" data-close-modal>Entendido</button>`,
  });
}

/* --------------------------------------------------------------------------
   Búsqueda de equipos
   -------------------------------------------------------------------------- */
function openTeamSearch() {
  const modal = openModal({
    title: "Buscar equipo",
    subtitle: "Encuentra un equipo y consulta sus últimos y próximos partidos.",
    body: `<div class="team-search-box">${icon("search")}<input id="teamSearchInput" type="search" placeholder="Escribe el nombre de un equipo…" autocomplete="off" aria-label="Buscar equipo"></div>
      <div class="search-results" id="teamResults"><div class="empty-state compact"><p>Escribe al menos dos letras.</p></div></div>`,
    footer: `<button class="soft-button" type="button" data-close-modal>Cerrar</button>`,
  });
  const input = $("#teamSearchInput", modal);
  const results = $("#teamResults", modal);
  const search = debounce(async () => {
    const query = input.value.trim();
    if (query.length < 2) {
      results.innerHTML = `<div class="empty-state compact"><p>Escribe al menos dos letras.</p></div>`;
      return;
    }
    results.innerHTML = `<div class="empty-state compact"><span class="spinner"></span><p style="margin-top:8px">Buscando equipos…</p></div>`;
    try {
      const payload = await api(`/api/team/search?q=${encodeURIComponent(query)}&limit=12`);
      const teams = payload.results || [];
      results.innerHTML = teams.length
        ? teams
            .map(
              (team) => `<button class="search-result" type="button" data-team-id="${esc(team.id)}" data-team-name="${esc(team.name)}" data-team-country="${esc(team.country || "")}">
                ${crest({ id: team.id, name: team.name })}
                <span class="search-result-copy"><strong>${esc(team.name || "Equipo")}</strong><span>${esc(team.country || "—")}</span></span>
                ${icon("chevron-right")}
              </button>`,
            )
            .join("")
        : `<div class="empty-state compact"><p>No se encontraron equipos.</p></div>`;
      results.querySelectorAll("[data-team-id]").forEach((button) => {
        button.addEventListener("click", () => openTeamMatches(button.dataset.teamId, button.dataset.teamName, modal));
      });
    } catch (error) {
      results.innerHTML = `<div class="warning-box">${icon("alert")}<div>${esc(error.message)}</div></div>`;
    }
  }, 320);
  input.addEventListener("input", search);
  setTimeout(() => input.focus(), 80);
}

async function openTeamMatches(teamId, teamNameValue, modal) {
  const body = $(".modal-body", modal);
  if (!body) return;
  body.innerHTML = `<div class="empty-state compact"><span class="spinner"></span><p style="margin-top:8px">Buscando partidos de ${esc(teamNameValue)}…</p></div>`;
  try {
    const payload = await api(`/api/team/matches?id=${encodeURIComponent(teamId)}&limit=40`);
    const matches = payload.matches || [];
    body.innerHTML = `<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <button class="icon-button" type="button" id="teamBack" title="Volver" aria-label="Volver a la búsqueda de equipos">${icon("arrow-left")}</button>
        ${crest({ id: teamId, name: teamNameValue }, "crest")}
        <strong style="font-size:13px">${esc(teamNameValue)}</strong>
        <span class="panel-count" style="margin-left:auto">${matches.length} partidos</span>
      </div>
      <div class="team-match-list">${matches.length ? matches.map((match) => {
        const status = statusInfo(match);
        return `<div class="team-match-row" data-open-match="${esc(match.id)}" tabindex="0" role="button" aria-label="Abrir ${esc(teamName(match.home_team))} contra ${esc(teamName(match.away_team))}">
          <span class="team-match-date">${esc(formatDate(matchDay(match)))}</span>
          <span>${isLive(match) ? '<span class="live-dot" style="color:var(--live)"></span>' : isFinished(match) ? "✓" : "•"}</span>
          <span class="team-match-main">${esc(teamName(match.home_team))} vs ${esc(teamName(match.away_team))}<span class="team-match-comp">${esc(match.tournament?.name || "")}</span></span>
          <span class="score-pill ${isLive(match) ? "live" : isFinished(match) ? "finished" : ""}">${esc(isFinished(match) || isLive(match) ? scoreShort(match) : status.short)}</span>
        </div>`;
      }).join("") : `<div class="empty-state compact"><p>No hay partidos en Europa o Sudamérica con los filtros actuales.</p></div>`}</div>`;
    $("#teamBack", body)?.addEventListener("click", openTeamSearch);
  } catch (error) {
    body.innerHTML = `<div class="warning-box">${icon("alert")}<div>${esc(error.message)}</div></div>`;
  }
}

/* --------------------------------------------------------------------------
   Exportaciones
   -------------------------------------------------------------------------- */
async function exportAnalysis(format) {
  if (!state.selectedMatch) return;
  try {
    setStatus("Generando exportación…", "busy");
    await downloadFrom(
      `/api/export/analysis?id=${encodeURIComponent(state.selectedMatch.id)}&window=${encodeURIComponent(state.analysis?.window ?? state.analysisWindow)}&format=${encodeURIComponent(format)}`,
      format === "json" ? "analisis.json" : "analisis.zip",
    );
    toast("Exportado", `El archivo ${format.toUpperCase()} se está descargando.`, "success");
  } catch (error) {
    toast("No se pudo exportar", error.message, "error");
  } finally {
    setStatus("Listo.");
  }
}

async function exportSimulation(format) {
  if (!state.simulation) return;
  try {
    setStatus("Generando exportación…", "busy");
    const response = await fetch("/api/export/simulation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        match_id: state.selectedMatch?.id,
        format,
        summary: state.simulation,
      }),
    });
    if (!response.ok) {
      let message = "No se pudo exportar.";
      try {
        message = (await response.json()).error || message;
      } catch {
        /* ignore */
      }
      throw new Error(message);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/i.exec(disposition);
    downloadBlob(blob, match ? match[1] : `simulacion.${format === "csv" ? "csv" : "json"}`);
    toast("Exportado", `La simulación ${format.toUpperCase()} se está descargando.`, "success");
  } catch (error) {
    toast("No se pudo exportar", error.message, "error");
  } finally {
    setStatus("Listo.");
  }
}

/* --------------------------------------------------------------------------
   Vistas y navegación
   -------------------------------------------------------------------------- */
function setView(name, { silent = false } = {}) {
  state.activeView = name;
  $$(".nav-item").forEach((button) => {
    const active = button.dataset.view === name;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  $$(".view").forEach((view) => {
    view.classList.toggle("is-active", view.id === `view-${name}`);
  });
  const filterbar = $("#filterbar");
  if (filterbar) filterbar.hidden = name !== "matches";
  const searchWrap = $("#matchSearchWrap");
  if (searchWrap) searchWrap.hidden = name !== "matches";
  const dateCluster = $("#dateCluster");
  if (dateCluster) dateCluster.hidden = name !== "matches" && name !== "live";
  if (silent) return;
  const view = $(`#view-${name}`);
  if (view) view.scrollTop = 0;
  if (name === "live") {
    if (!Object.keys(state.latestPredictions).length) {
      loadJournal(true).then(() => renderLive()).catch(() => {});
    }
    renderLive();
    refreshLive({ silent: true });
  } else if (name === "journal") {
    loadJournal();
  } else if (name === "explorer") {
    loadExplorer();
  } else if (name === "previews") {
    renderPreviews();
  } else if (name === "model") {
    loadModel();
  } else if (name === "matches") {
    renderMatches();
  }
}

/* --------------------------------------------------------------------------
   Eventos
   -------------------------------------------------------------------------- */
function bindEvents() {
  $$(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      setView(button.dataset.view);
      if (window.innerWidth <= 820) setSidebarOpen(false);
    });
  });

  $("#themeToggle")?.addEventListener("click", openThemePicker);
  $("#helpButton")?.addEventListener("click", openHelp);
  $("#settingsButton")?.addEventListener("click", openSettings);
  $("#teamSearchButton")?.addEventListener("click", openTeamSearch);

  $("#prevDay")?.addEventListener("click", () => {
    state.date = shiftDate(state.date, -1);
    $("#dateInput").value = state.date;
    updateDayCaption();
    loadDay();
  });
  $("#nextDay")?.addEventListener("click", () => {
    state.date = shiftDate(state.date, 1);
    $("#dateInput").value = state.date;
    updateDayCaption();
    loadDay();
  });
  $("#todayButton")?.addEventListener("click", () => {
    state.date = state.boot?.today || dayKeyFromDate(new Date().toISOString().slice(0, 10));
    $("#dateInput").value = state.date;
    updateDayCaption();
    loadDay();
  });
  $("#emptyTodayButton")?.addEventListener("click", () => {
    state.date = state.boot?.today || dayKeyFromDate(new Date().toISOString().slice(0, 10));
    $("#dateInput").value = state.date;
    updateDayCaption();
    loadDay();
  });
  $("#dateInput")?.addEventListener("change", (event) => {
    if (!event.target.value) return;
    state.date = event.target.value;
    updateDayCaption();
    loadDay();
  });

  $("#regionSelect")?.addEventListener("change", (event) => {
    state.region = event.target.value;
    state.prefs.region = event.target.value;
    api("/api/preferences", { method: "POST", body: { region: event.target.value } }).catch(() => {});
    loadDay();
  });
  $("#competitionSelect")?.addEventListener("change", (event) => {
    state.competitions = event.target.value;
    state.prefs.competitions = event.target.value;
    api("/api/preferences", { method: "POST", body: { competitions: event.target.value } }).catch(() => {});
    loadDay();
  });
  $("#leagueSelect")?.addEventListener("change", (event) => {
    state.league = event.target.value;
    renderMatches();
  });
  $$("#statusChips .chip").forEach((button) => {
    button.addEventListener("click", () => {
      state.status = button.dataset.status;
      $$("#statusChips .chip").forEach((chip) => chip.classList.toggle("is-active", chip === button));
      renderMatches();
    });
  });
  $("#matchSearch")?.addEventListener(
    "input",
    debounce((event) => {
      state.query = event.target.value;
      renderMatches();
    }, 140),
  );
  $("#refreshButton")?.addEventListener("click", () => {
    if (state.activeView === "matches") loadDay({ refresh: true });
    else if (state.activeView === "live") refreshLive();
    else if (state.activeView === "journal") loadJournal(true);
    else if (state.activeView === "explorer") loadExplorer();
    else if (state.activeView === "model") loadModel();
    else if (state.activeView === "previews" && state.selectedMatch) generatePreview();
  });
  $("#livePill")?.addEventListener("click", () => setView("live"));
  $("#collapseFilters")?.addEventListener("click", () => {
    $("#filterbar")?.classList.toggle("is-collapsed");
  });
  $("#menuToggle")?.addEventListener("click", () => {
    const sidebar = $("#sidebar");
    setSidebarOpen(!sidebar?.classList.contains("is-open"));
  });
  $("#sidebarBackdrop")?.addEventListener("click", () => setSidebarOpen(false));
  $("#modalRoot")?.addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeModal();
  });

  $("#matchList")?.addEventListener("click", (event) => {
    if (event.target.closest("[data-fav-team]")) return;
    const row = event.target.closest(".match-row");
    if (row) selectMatch(Number(row.dataset.matchId));
  });
  $("#matchList")?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    if (event.target.closest("[data-fav-team]")) return;
    const row = event.target.closest(".match-row");
    if (!row) return;
    event.preventDefault();
    selectMatch(Number(row.dataset.matchId));
  });
  $("#detailContent")?.addEventListener("click", handleDetailClick);
  $("#detailContent")?.addEventListener("change", handleDetailChange);
  $("#detailContent")?.addEventListener("keydown", handleDetailKeydown);

  $("#liveRefreshButton")?.addEventListener("click", () => refreshLive());
  $("#liveGoMatches")?.addEventListener("click", () => setView("matches"));
  $("#liveEmptyButton")?.addEventListener("click", () => setView("matches"));
  $$("#liveFilters button").forEach((button) => {
    button.addEventListener("click", () => {
      state.liveFilter = button.dataset.liveFilter;
      $$("#liveFilters button").forEach((item) => item.classList.toggle("is-active", item === button));
      renderLive();
    });
  });

  $("#journalRefresh")?.addEventListener("click", () => loadJournal(true));
  $("#journalExport")?.addEventListener("click", () => {
    downloadFrom("/api/export/history?kind=predictions", "predicciones.csv").catch((error) =>
      toast("No se pudo exportar", error.message, "error"),
    );
  });
  $("#journalSearch")?.addEventListener("input", debounce(renderJournal, 130));
  $("#journalStatus")?.addEventListener("change", renderJournal);

  $("#explorerApply")?.addEventListener("click", () => {
    state.explorerQuery = $("#explorerSearch")?.value || "";
    state.explorerStatus = $("#explorerStatus")?.value || "";
    loadExplorer();
  });
  $("#explorerSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      state.explorerQuery = event.target.value;
      state.explorerStatus = $("#explorerStatus")?.value || "";
      loadExplorer();
    }
  });
  $("#explorerStatus")?.addEventListener("change", () => {
    state.explorerStatus = $("#explorerStatus")?.value || "";
    loadExplorer();
  });
  $("#explorerExport")?.addEventListener("click", () => {
    downloadFrom(
      `/api/export/history?${new URLSearchParams({ kind: "matches", query: state.explorerQuery, status: state.explorerStatus }).toString()}`,
      "historial_partidos.csv",
    ).catch((error) => toast("No se pudo exportar", error.message, "error"));
  });
  $("#explorerClear")?.addEventListener("click", clearHistory);
  $("#explorerFolder")?.addEventListener("click", async () => {
    try {
      const result = await api("/api/open-folder", { method: "POST", body: {} });
      toast("Carpeta abierta", result.opened, "info");
    } catch (error) {
      toast("No se pudo abrir", error.message, "error");
    }
  });
  $("#apiCopy")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(location.origin);
      toast("Copiado", "La URL de la API está en el portapapeles.", "success");
    } catch {
      toast("No se pudo copiar", "El navegador bloqueó el portapapeles.", "error");
    }
  });
  $("#apiOpen")?.addEventListener("click", () => {
    window.open(`${location.origin}/api/health`, "_blank", "noopener");
  });

  $("#modelRefresh")?.addEventListener("click", loadModel);

  $("#previewCopy")?.addEventListener("click", copyPreviewMarkdown);
  $("#previewDownloadMd")?.addEventListener("click", () => downloadPreview("md"));
  $("#previewDownloadHtml")?.addEventListener("click", () => downloadPreview("html"));
  $("#previewOpen")?.addEventListener("click", openPreviewInBrowser);

  document.addEventListener("click", (event) => {
    const star = event.target.closest("[data-fav-team]");
    if (star) {
      event.preventDefault();
      event.stopPropagation();
      toggleFavorite(star.dataset.favTeam, star.dataset.favName);
      return;
    }
    const openMatch = event.target.closest("[data-open-match]");
    if (openMatch) {
      event.preventDefault();
      if (openMatch.closest(".modal")) closeModal();
      openMatchById(openMatch.dataset.openMatch);
    }
  });

  document.addEventListener("keydown", (event) => {
    const ctrl = event.ctrlKey || event.metaKey;
    const modalRoot = $("#modalRoot");
    if (modalRoot && !modalRoot.hidden) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
        return;
      }
      if (event.key === "Tab") {
        const modal = $(".modal", modalRoot);
        const focusable = modal ? modalFocusable(modal) : [];
        if (!focusable.length) {
          event.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!modal.contains(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
          return;
        }
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
          return;
        }
        if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
          return;
        }
      }
      const openTarget = event.target.closest("[data-open-match]");
      if (
        openTarget &&
        (event.key === "Enter" || event.key === " ") &&
        !event.target.closest("button, a")
      ) {
        event.preventDefault();
        closeModal();
        openMatchById(openTarget.dataset.openMatch);
      }
      return;
    }
    const openTarget = event.target.closest("[data-open-match]");
    if (
      openTarget &&
      (event.key === "Enter" || event.key === " ") &&
      !event.target.closest("button, a")
    ) {
      event.preventDefault();
      if (openTarget.closest(".modal")) closeModal();
      openMatchById(openTarget.dataset.openMatch);
      return;
    }
    if (event.key === "Escape") {
      if (!$("#modalRoot")?.hidden) {
        closeModal();
        return;
      }
      if (window.innerWidth <= 820 && $("#sidebar")?.classList.contains("is-open")) {
        setSidebarOpen(false);
        return;
      }
      if (state.activeView === "matches" && state.detailOpen && window.innerWidth <= 1120) {
        clearSelection();
        return;
      }
      if (state.status !== "all" || state.query || state.league !== "all") {
        state.status = "all";
        state.query = "";
        state.league = "all";
        $("#matchSearch").value = "";
        $("#leagueSelect").value = "all";
        $$("#statusChips .chip").forEach((chip) => chip.classList.toggle("is-active", chip.dataset.status === "all"));
        renderMatches();
      }
      return;
    }
    if (event.key === "F1") {
      event.preventDefault();
      openHelp();
      return;
    }
    if (ctrl && event.key.toLowerCase() === "k") {
      event.preventDefault();
      setView("matches");
      $("#matchSearch")?.focus();
      return;
    }
    if (ctrl && event.key.toLowerCase() === "f") {
      event.preventDefault();
      setView("matches");
      $("#matchSearch")?.focus();
      return;
    }
    if (ctrl && event.key.toLowerCase() === "g") {
      event.preventDefault();
      openTeamSearch();
      return;
    }
    if (ctrl && event.key.toLowerCase() === "r") {
      event.preventDefault();
      if (state.activeView === "matches") loadDay({ refresh: true });
      else refreshLive();
      return;
    }
    if (ctrl && event.key.toLowerCase() === "d") {
      event.preventDefault();
      cycleTheme();
      return;
    }
    if (ctrl && event.shiftKey && event.key.toLowerCase() === "l") {
      event.preventDefault();
      setView("live");
      return;
    }
    if (ctrl && event.shiftKey && event.key.toLowerCase() === "p") {
      event.preventDefault();
      setView("journal");
      return;
    }
    if (ctrl && event.shiftKey && event.key.toLowerCase() === "e") {
      event.preventDefault();
      if (state.analysis) exportAnalysis("json");
      return;
    }
    if (ctrl && event.shiftKey && event.key.toLowerCase() === "r") {
      event.preventDefault();
      setView("previews");
      return;
    }
    if (ctrl && event.shiftKey && event.key.toLowerCase() === "d") {
      event.preventDefault();
      setView("explorer");
      return;
    }
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 820) {
      setSidebarOpen(false);
    }
  });
}

async function toggleFavorite(teamId, name) {
  if (!teamId) return;
  const key = String(teamId);
  const favorite = state.favorites[key] === undefined;
  try {
    const result = await api("/api/favorites", {
      method: "POST",
      body: { team_id: teamId, name, favorite },
    });
    state.favorites = result.favorites || {};
    state.prefs.favorites = state.favorites;
    toast(
      favorite ? "Añadido a favoritos" : "Quitado de favoritos",
      name || key,
      favorite ? "success" : "info",
      2200,
    );
    renderMatches();
    if (state.selectedMatch) renderDetail();
    if (state.activeView === "live") renderLive();
  } catch (error) {
    toast("No se pudo guardar el favorito", error.message, "error");
  }
}

function handleDetailClick(event) {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!action) return;
  const button = event.target.closest("[data-action]");
  if (action === "tab") {
    state.detailTab = button.dataset.tab;
    renderDetail({ scrollTop: 0 });
    document.querySelector(`#tab-${state.detailTab}`)?.focus();
    return;
  }
  if (action === "analyze") {
    analyzeMatch(true);
    return;
  }
  if (action === "simulate") {
    if (!state.analysis) return;
    state.detailTab = "simulation";
    renderDetail({ scrollTop: 0 });
    return;
  }
  if (action === "preview") {
    generatePreview();
    return;
  }
  if (action === "close-detail") {
    clearSelection();
    return;
  }
  if (action === "go-day") {
    if (!state.selectedMatch) return;
    const day = matchDay(state.selectedMatch);
    if (!day) return;
    state.date = day;
    $("#dateInput").value = day;
    updateDayCaption();
    loadDay().then(() => selectMatchObject(state.selectedMatch));
    return;
  }
  if (action === "run-simulation") {
    runSimulation();
    return;
  }
  if (action === "clear-cache") {
    clearSimulationCache();
    return;
  }
  if (action === "export-analysis-json") {
    exportAnalysis("json");
    return;
  }
  if (action === "export-analysis-csv") {
    exportAnalysis("csv");
    return;
  }
  if (action === "export-sim-json") {
    exportSimulation("json");
    return;
  }
  if (action === "export-sim-csv") {
    exportSimulation("csv");
  }
}

function handleDetailChange(event) {
  if (event.target.id === "analysisWindowSelect" || event.target.id === "simWindow") {
    state.analysisWindow = event.target.value === "all" ? "all" : Number(event.target.value);
    if (state.analysis) analyzeMatch(true);
  } else if (event.target.id === "simHistogramSelect") {
    state.simMetric = event.target.value;
    renderDetail();
  } else if (event.target.id === "simMarketSelect") {
    state.simMarket = event.target.value;
    renderDetail();
  }
}

function handleDetailKeydown(event) {
  const tab = event.target.closest(".tab");
  if (!tab) return;
  const tabs = Array.from(document.querySelectorAll(".tabs .tab"));
  if (!tabs.length) return;
  const index = tabs.indexOf(tab);
  let next = null;
  if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
  else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = tabs.length - 1;
  if (next === null) return;
  event.preventDefault();
  tabs[next].focus();
  tabs[next].click();
}

async function clearSimulationCache() {
  try {
    const result = await api("/api/simulation/cache", { method: "DELETE" });
    toast("Caché vaciada", `${result.deleted || 0} simulación(es) eliminadas.`, "success");
    state.journalLoaded = false;
  } catch (error) {
    toast("No se pudo vaciar la caché", error.message, "error");
  }
}

/* --------------------------------------------------------------------------
   Arranque final
   -------------------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", boot);
