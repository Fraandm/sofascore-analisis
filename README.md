# SofaScore Extractor

Programa de línea de comandos y aplicación de escritorio con interfaz web local para extraer datos de partidos de fútbol desde la API interna de SofaScore: calendario por fecha, resultados, estadísticas, alineaciones, incidencias, equipos, torneos, clasificaciones y jugadores.

Incluye un **analizador de forma** que, a partir de un próximo partido, recopila las estadísticas de los últimos 5, 10, 15 o todos los partidos de ambos clubes en la temporada y las compara en una interfaz web local con siete temas visuales.

Exporta a **JSON**, **JSONL** o **CSV** y funciona en Windows, Linux y macOS.

> **Aviso legal:** este proyecto no está afiliado a SofaScore. Los datos pertenecen a SofaScore y a sus proveedores. Úsalo únicamente para fines personales, educativos o de investigación, respeta sus términos de servicio y no redistribuyas los datos de forma masiva. La API no es pública ni está documentada y puede cambiar sin aviso.

---

## Abrir desde el Explorador de Windows

En la carpeta del proyecto hay un ejecutable listo para usar:

- **`SofaScore.exe`** — doble clic para abrir la interfaz web local. No necesita tener Python instalado.
- **`Iniciar SofaScore.cmd`** — alternativa que abre el programa desde el código fuente (usa `SofaScore.exe` si existe).

La primera vez, Windows SmartScreen puede mostrar un aviso porque el ejecutable no está firmado digitalmente: pulsa **«Más información» → «Ejecutar de todas formas»**.

Para regenerar el ejecutable después de modificar el código:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

El script instala PyInstaller si hace falta y deja el nuevo `SofaScore.exe` en la raíz del proyecto.

---

## Características

- Partidos de una fecha con filtro por país, torneo o estado en vivo.
- **Listado agrupado por liga**: primero las cinco grandes, después el resto de Europa y Sudamérica, con encabezados y separadores visuales.
- **Partidos próximos, en vivo y finalizados** en el mismo listado, con marcador actual o final y minuto de juego.
- **Carga progresiva**: primero aparecen las cinco grandes y Sudamérica; el resto de competiciones se incorpora en segundo plano.
- **Actualización automática en vivo** cada 45 segundos, sin recargar toda la fecha.
- **Favoritos y alertas**: marca equipos, filtra por ellos y recibe avisos de inicio, gol y final.
- **Escudos, banderas y chips de estado**: imágenes de equipos y países con caché local, además de filtros rápidos por estado.
- **Sala de directo**: panel de tarjetas en vivo con marcador, pronóstico guardado y acceso al partido.
- **Cuaderno de predicciones**: historial automático, acierto 1X2, Brier, log-loss y error de goles.
- **Estudio de previas**: genera previas en Markdown/HTML y las abre en el navegador.
- **Explorador de datos y API local**: consulta el historial desde la app o desde `127.0.0.1`.
- **Validación contra la realidad**: analiza y simula un partido ya jugado y compara el resultado real con las probabilidades y las métricas simuladas.
- **Caché de simulaciones** en disco para no repetir cálculos, con botón para vaciarla.
- Detalle completo de un partido: estadísticas por periodo, alineaciones, goles/tarjetas/cambios, H2H, gráfico de juego y mejores jugadores.
- Historial, próximos partidos y últimos resultados de un equipo.
- Temporadas, jornadas, partidos y clasificación de un torneo.
- Buscador global de equipos, jugadores, torneos y partidos.
- **Análisis de forma previo a un partido**: goles, xG, ocasiones claras, remates dentro del área, córners, tarjetas, remates, remates al arco, faltas y paradas del portero de ambos equipos.
- **Modelo ajustado al rival**: remates, córners, tarjetas y faltas combinan la producción propia con lo que concede el adversario; los goles mezclan goles y xG.
- **Contexto de fuerza**: valor de mercado de la alineación, clasificación de la competición y H2H para corregir favoritos artificiales.
- **Red neuronal de apoyo**: MLP entrenada con partidos históricos para ajustar los goles y las tarjetas; se combina con Monte Carlo cuando mejora la validación.
- **Alineaciones y árbitro**: etiqueta si la alineación es probable o confirmada, usa los titulares confirmados en la simulación y ajusta tarjetas/faltas con el historial del árbitro.
- **Simulación Monte Carlo con NumPy**: miles de escenarios para estimar distribuciones, percentiles, probabilidades 1X2, ambos marcan, over/under y matriz de marcadores.
- **Interfaz web local HTML5/CSS/JS** para elegir el partido, la ventana de partidos y exportar el análisis, con **siete temas visuales**, búsqueda instantánea, filtros, atajos de teclado, gráficos propios y diseño adaptable. Incluye **modo clásico de Tkinter** como respaldo.
- **Ejecutable para Windows** que se abre con doble clic desde el Explorador.
- Fechas en la zona horaria del usuario (`--timezone`), no en la ventana UTC que usa la API.
- Caché en disco, reintentos con backoff, límite de peticiones y soporte de proxy.
- Salida legible por humanos o lista para Excel/CSV.

---

## Requisitos e instalación

- Python 3.9 o superior (probado con Python 3.14).
- Conexión a Internet.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Comprueba que funciona:

```bash
python -m sofascore --help
```

### Instalación opcional como comando

```bash
pip install -e .
sofascore --help
```

Las dos formas son equivalentes: `python -m sofascore ...` y `sofascore ...`.

> **Windows:** el paquete `tzdata` se instala automáticamente con `requirements.txt` y es necesario para usar zonas horarias IANA como `Europe/Madrid`.

---

## Uso rápido

```bash
# Partidos de hoy en España, en hora española, exportados a CSV
python -m sofascore date hoy --country Spain --timezone Europe/Madrid -f csv -o partidos.csv

# Partidos en directo
python -m sofascore live --limit 20

# Detalle completo de un partido
python -m sofascore match 16938982 --all -o partido.json

# Buscar un equipo para obtener su ID
python -m sofascore search "real madrid" --type team
```

Los IDs (`team_id`, `tournament_id`, `event_id`, `player_id`, `season`) aparecen en los resultados de `search` y en las URLs de SofaScore.

---

## Interfaz web local (predeterminada)

La aplicación usa una interfaz **HTML5 + CSS + JavaScript** servida por un servidor local en `127.0.0.1`. En Windows, `SofaScore.exe` abre esa interfaz en una ventana de Microsoft Edge en modo aplicación, sin barra de direcciones ni pestañas. No necesita Python instalado ni un servidor externo. Si Edge no está disponible, se abre en el navegador predeterminado.

La interfaz clásica de Tkinter sigue incluida como respaldo: se abre con `SofaScore.exe --classic` o `python -m sofascore gui`. Comparte la misma base de datos, preferencias, análisis, simulación y modelo.

### Abrir la aplicación

```bash
# Interfaz web local (por defecto)
python -m sofascore.webapp

# Elegir puerto
python -m sofascore.webapp --port 9000

# Abrir en el navegador predeterminado en vez de la ventana Edge
python -m sofascore.webapp --browser

# Solo servidor, sin abrir ventana (útil para pruebas o para integrarla)
python -m sofascore.webapp --no-window

# Interfaz clásica de Tkinter
python -m sofascore gui
python -m sofascore gui --theme oscuro
```

También puedes usar `SofaScore.exe` con doble clic, `Iniciar SofaScore.cmd` o, si instalaste el paquete, `sofascore-gui` (web) y `sofascore-classic` (Tkinter).

### Flujo de uso

1. Elige una fecha con las flechas, el calendario o el botón **Hoy**.
2. Filtra por **región**, **competiciones** o una **liga** concreta.
3. Selecciona un partido de la lista. La ficha se abre a la derecha y el análisis comienza automáticamente.
4. Revisa **Resumen**: forma, comparación, contexto, alineaciones, árbitro, clasificación y H2H.
5. Abre **Simulación**, ajusta escenarios y semilla, y pulsa **Simular partido**.
6. Consulta los KPI, el donut 1X2, los marcadores probables, las distribuciones, los mercados over/under, la matriz de marcadores y la validación real.
7. Pulsa **Previa** para generar un documento listo para copiar, descargar o imprimir como PDF.
8. Las predicciones se guardan solas en el **Cuaderno**.
9. En **Explorador** consulta el historial, exporta CSV o abre la API local.
10. En **Modelo** revisa la versión activa, el MAE por mercado y el peso de la red.

### Pantallas

- **Partidos**: listado agrupado en **Top 5**, **Otras competiciones** y **Sudamérica**, con búsqueda instantánea, chips de estado, favoritos y carga progresiva.
- **Sala de directo**: tarjetas de todos los partidos en vivo, con marcador, minuto, escudos, liga y el último pronóstico guardado. Se actualiza sola.
- **Cuaderno de predicciones**: historial automático con acierto 1X2, Brier, log-loss, error medio de goles, búsqueda, filtros y exportación CSV.
- **Estudio de previas**: previa completa con forma, comparación, probabilidades, alineaciones y árbitro. Permite copiar Markdown, descargar Markdown/HTML y abrir el HTML en el navegador para imprimirlo como PDF.
- **Explorador**: partidos y pronósticos guardados, búsqueda, exportación, borrado del historial y controles de la API local.
- **Modelo**: estado del modelo neuronal, métricas de test, comparación con la línea base y pesos de mezcla.
- **Ajustes**: tema, análisis automático, zona horaria, región, competiciones, auto en vivo, alertas, carpeta de datos y atajos.
- **Ayuda** (`F1`): atajos y consejos.

### Filtros, carga progresiva y directo

El listado por fecha se organiza en tres bloques: **Top 5** (Premier League, LaLiga, Serie A, Bundesliga y Ligue 1), **Otras competiciones** y **Sudamérica**. Dentro de cada bloque, los partidos en vivo aparecen primero, después los próximos y al final los finalizados.

La primera petición carga las competiciones principales y Sudamérica; el resto se incorpora en segundo plano con un aviso de progreso. El botón **Todas** permite ampliar el alcance.

La **Sala de directo** y el listado se actualizan automáticamente cada 45 segundos. Solo se consulta el endpoint de eventos en vivo y, si un partido acaba de terminar, se pide su detalle para mostrar el resultado final. Se puede desactivar en **Ajustes → Auto en vivo**.

### Favoritos y alertas

Pulsa la **estrella** junto a un equipo en la lista o en la ficha del partido. Los favoritos se guardan en la configuración y el chip **★ Favoritos** muestra solo sus partidos.

Con **Ajustes → Alertas de favoritos** activado, la actualización en vivo muestra un aviso flotante cuando cambia el marcador o termina un partido de un equipo favorito. Si el navegador lo permite, también se envía una notificación del sistema. Las alertas se generan durante la actualización automática.

### Partidos finalizados y validación

Al cargar una fecha, los partidos terminados aparecen con su marcador final. Para contrastar el modelo:

1. Selecciona un partido finalizado.
2. Pulsa **Analizar partido** y después **Simular**.
3. Abre la tarjeta **Validación** de la simulación.

La validación muestra el marcador real, la comparación entre lo esperado y lo real, el error, el rango P10–P90 y si el valor real cae dentro del rango. El partido objetivo se excluye siempre del entrenamiento: solo se usan sus rivales anteriores a la fecha del partido. Sus estadísticas reales se emplean únicamente para validar, nunca como entrada del modelo.

En partidos en vivo, las estadísticas actuales se escalan por el minuto jugado y se comparan con la proyección final. Vuelve a pulsar **Actualizar análisis** para refrescar el minuto y los datos.

### Estudio de previas

El **Estudio de previas** genera un documento con:

- forma reciente de ambos equipos,
- tabla de comparación,
- probabilidades de la simulación,
- alineaciones y árbitro,
- resultado real si el partido ya terminó.

Puedes **copiar el Markdown**, **descargar Markdown**, **descargar HTML** o **abrir el HTML en el navegador**. Desde el navegador, usa `Ctrl+P → Guardar como PDF` si quieres conservar la previa.

### Explorador y API local

La base de datos se guarda en:

```text
%LOCALAPPDATA%\sofascore-gui\history.db
```

La API local escucha solo en `127.0.0.1` y ofrece:

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/day?date=&region=&competitions=&timezone=&stage=`
- `GET /api/live?ids=`
- `GET /api/match?id=`
- `GET /api/predictions?limit=`
- `GET /api/history/matches?query=&status=&limit=`
- `GET /api/accuracy`
- `GET /api/model`
- `GET /api/preview?id=&window=`
- `GET /api/export/analysis?id=&window=&format=json|csv`
- `GET /api/export/history?kind=matches|predictions`
- `POST /api/jobs/analysis`
- `POST /api/jobs/simulation`
- `POST /api/preferences`
- `POST /api/favorites`

La API está pensada para uso personal. No la expongas directamente a Internet.

### Atajos de teclado

| Atajo | Acción |
| --- | --- |
| `Ctrl+K` / `Ctrl+F` | Buscar en el listado de partidos. |
| `Ctrl+G` | Buscar un equipo. |
| `Ctrl+R` | Recargar la fecha o actualizar el directo. |
| `Ctrl+D` | Cambiar al siguiente tema. |
| `Ctrl+Shift+L` | Abrir la sala de directo. |
| `Ctrl+Shift+P` | Abrir el cuaderno de predicciones. |
| `Ctrl+Shift+R` | Abrir el estudio de previas. |
| `Ctrl+Shift+D` | Abrir el explorador. |
| `Ctrl+Shift+E` | Exportar el análisis seleccionado a JSON. |
| `F1` | Abrir la ayuda. |
| `Esc` | Cerrar un diálogo o limpiar los filtros. |
| `Intro` | Abrir el partido enfocado. |

### Temas, preferencias y datos

La interfaz incluye **siete temas**: **Claro**, **Oscuro**, **Medianoche**, **Bosque**, **Océano**, **Atardecer** y **Alto contraste**. Puedes abrir el selector desde el botón **Tema** de la barra lateral o desde **Ajustes → Apariencia**. Cada tarjeta muestra una vista previa de la paleta.

También puedes recorrer los temas con `Ctrl+D`. El tema, la zona horaria, la región, las competiciones, los favoritos y las alertas se guardan en:

```text
%LOCALAPPDATA%\sofascore-gui\settings.json
```

La caché de imágenes está en `%LOCALAPPDATA%\sofascore-gui\images` y las simulaciones en `%LOCALAPPDATA%\sofascore-gui\simulations`. La interfaz web y la clásica comparten estos datos.

### Modo clásico de Tkinter

La interfaz original sigue disponible para quien prefiera una ventana nativa o tenga problemas con Edge/WebView2:

```bash
python -m sofascore gui
python -m sofascore gui --theme oscuro
SofaScore.exe --classic
```

El modo clásico mantiene el listado, filtros, favoritos, análisis, simulación, gráficos, cuaderno, previas, explorador y API local. Sus preferencias y su historial son los mismos que los de la interfaz web.

## Comandos

### `search` — buscar entidades

```bash
python -m sofascore search "real madrid" --type team
python -m sofascore search "mbappe" --type player --limit 5
python -m sofascore search "champions league" --type tournament
python -m sofascore search "real madrid" --type all --sport all
```

| Opción | Descripción |
|---|---|
| `--type` | `all`, `team`, `player`, `tournament`, `event` o `manager`. |
| `--sport` | Deporte (por defecto `football`; usa `all` para no filtrar). |
| `--limit` | Número máximo de resultados (por defecto 20). |

### `date` — partidos de una fecha

```bash
python -m sofascore date 2026-11-04
python -m sofascore date 04/11/2026 --country Spain
python -m sofascore date hoy --tournament "Champions League"
python -m sofascore date 2026-11-04 --country Spain --live
python -m sofascore date 2026-11-04 --max-tournaments 10
```

| Opción | Descripción |
|---|---|
| `date` | `YYYY-MM-DD`, `DD/MM/YYYY`, `hoy`, `ayer` o `mañana`. |
| `--country` | País o categoría (`Spain`, `England`, `España`, `USA`...). Usa el endpoint de categoría: **1 petición**. |
| `--tournament` | Nombre del torneo (`Champions League`, `Copa del Rey`...). |
| `--timezone` | `local` (por defecto), `UTC`, `Europe/Madrid` o `+02:00`. |
| `--live` | Solo partidos en juego. |
| `--limit` | Máximo de partidos. |
| `--max-tournaments` | Limita cuántos torneos se consultan (0 = todos). |

Sin `--country` ni `--tournament`, el programa descarga la lista de torneos del día y luego consulta cada torneo. Es más lento (puede ser un centenar de peticiones); para pruebas usa `--max-tournaments` o filtra por país/torneo.

### `live` — partidos en directo

```bash
python -m sofascore live
python -m sofascore live --country Spain --limit 10
python -m sofascore live --tournament "Champions League"
```

### `match` — detalle de un partido

```bash
python -m sofascore match 16938982
python -m sofascore match 16938982 --stats
python -m sofascore match 16938982 --stats --period ALL
python -m sofascore match 16938982 --all -o partido.json
python -m sofascore match 16938982 --all --lineup-stats --raw -o partido_completo.json
```

| Opción | Descripción |
|---|---|
| `--stats` | Estadísticas del partido. |
| `--lineups` | Alineaciones. |
| `--incidents` | Goles, tarjetas, cambios y periodos. |
| `--h2h` | Historial entre ambos equipos. |
| `--graph` | Gráfico de presión/dominio. |
| `--best-players` | Mejores jugadores del partido. |
| `--all` | Incluye todas las secciones anteriores. |
| `--period` | Filtra estadísticas: `ALL`, `1ST`, `2ND`, `ET`, `PEN`. |
| `--lineup-stats` | Incluye estadísticas individuales de cada jugador. |
| `--raw` | Añade las respuestas crudas de la API en `_raw`. |

### `team` — equipo, historial y próximos partidos

```bash
python -m sofascore team 2829 --last 10
python -m sofascore team 2829 --next 5
python -m sofascore team 2829 --last 10 --next 5 -o real_madrid.json
```

Por defecto devuelve los últimos 10 partidos. Para CSV/JSONL usa `--last` o `--next` por separado; para ambos a la vez usa JSON.

### `tournament` — temporadas, jornadas y clasificación

```bash
python -m sofascore tournament 7 --seasons
python -m sofascore tournament 7 --season 96518 --last 10
python -m sofascore tournament 7 --season 96518 --next 10
python -m sofascore tournament 7 --round 4
python -m sofascore tournament 7 --season 96518 --standings
```

Si no indicas `--season`, se usa la temporada más reciente que devuelve la API.

### `player` — información de un jugador

```bash
python -m sofascore player 826643
```

### `categories` — países y categorías disponibles

```bash
python -m sofascore categories --filter spain
python -m sofascore categories --filter "south america"
```

Útil para saber qué valor pasar a `--country`.

### `upcoming` — partidos de una fecha

```bash
python -m sofascore upcoming
python -m sofascore upcoming 2026-11-04 --include-finished
python -m sofascore upcoming 2026-11-07 --region europa
python -m sofascore upcoming 2026-11-07 --limit 40 -f csv -o partidos.csv
```

Incluye partidos próximos y en vivo, y con `--include-finished` también terminados con su marcador final. Usa `--no-live` para excluir los que están en juego.

| Opción | Descripción |
|---|---|
| `date` | `YYYY-MM-DD`, `DD/MM/YYYY`, `hoy`, `ayer` o `mañana` (por defecto `hoy`). |
| `--region` | `ambas`, `europa` o `sudamerica`. |
| `--competitions` | `principales` (rápido) o `todas`. |
| `--include-finished` | Añade partidos finalizados con su marcador. |
| `--no-live` | Excluye los partidos en vivo (por defecto se incluyen). |
| `--timezone` | Zona horaria usada para filtrar y mostrar la fecha. |
| `--limit` | Máximo de partidos. |

### `form` — análisis de forma de ambos equipos

```bash
python -m sofascore form 16421105 --last 10
python -m sofascore form 16421105 --last 5 -f csv -o resumen.csv
python -m sofascore form 16421105 --last all -o analisis.json
python -m sofascore form 16943943 --context -o analisis_con_contexto.json
```

Analiza los partidos terminados de ambos clubes en la temporada del partido indicado y devuelve:

- Totales y medias de goles a favor/en contra, córners, tarjetas, remates, remates al arco, faltas y paradas.
- El detalle de cada partido con rival, condición de local/visitante y resultado.
- Una comparación directa con la diferencia entre ambos equipos.
- Medias específicas del local jugando en casa y del visitante jugando fuera.
- Con `--context`, las alineaciones normalizadas, el perfil del árbitro, la clasificación y el H2H.

| Opción | Descripción |
|---|---|
| `--last` | `5`, `10`, `15` o `all` (por defecto 10). |
| `--context` | Incluye alineaciones, árbitro, clasificación y H2H. |
| `-o, --output` | Guarda el análisis. |
| `-f, --format` | `json`, `jsonl` o `csv`. En CSV se exporta la tabla comparativa. |

### `simulate` — simulación Monte Carlo

```bash
python -m sofascore simulate 16421105 --last 10
python -m sofascore simulate 16421105 --last 10 --iterations 100000 --seed 7
python -m sofascore simulate 16421105 --iterations 50000 -o simulacion.json
python -m sofascore simulate 16421105 --iterations 50000 -f csv -o simulacion.csv
```

Simula miles de partidos a partir del análisis de forma y devuelve:

- Medias y percentiles (P10, P25, mediana, P75, P90) de goles, córners, tarjetas, remates, remates al arco, faltas y paradas.
- Probabilidades 1X2, ambos marcan, porterías a cero y over/under.
- Distribuciones completas y matriz de marcadores.
- Los marcadores más probables y los parámetros del modelo.
- Si están disponibles, la alineación, el árbitro, la clasificación y el H2H se consultan y se aplican automáticamente.

| Opción | Descripción |
|---|---|
| `--last` | `5`, `10`, `15` o `all` (por defecto 10). |
| `--iterations` | Escenarios simulados. Por defecto 50.000; mínimo 1.000; máximo 500.000. |
| `--seed` | Semilla entera para que el resultado sea reproducible (por defecto 42). |
| `-o, --output` | Guarda el resultado. En JSON incluye todo; en CSV se exporta una tabla resumida. |
| `-f, --format` | `json`, `jsonl` o `csv`. |

### `webapp` — interfaz web local

```bash
python -m sofascore.webapp
python -m sofascore.webapp --port 9000
python -m sofascore.webapp --browser
python -m sofascore.webapp --no-window
```

Abre la interfaz web local descrita arriba. Por defecto escucha en `127.0.0.1` y abre una ventana de Edge en modo aplicación.

| Opción | Descripción |
|---|---|
| `--port` | Puerto local (por defecto 8765; si está ocupado se prueba el siguiente). |
| `--browser` | Abre en el navegador predeterminado en vez de la ventana Edge. |
| `--no-window` | Solo inicia el servidor y muestra la URL. |
| `--position` | Posición de la ventana, por ejemplo `-1650,-37`. |
| `--size` | Tamaño de la ventana, por ejemplo `1380,880`. |
| `--workers` | Hilos de consulta a SofaScore. |
| `--classic` | Abre la interfaz clásica de Tkinter. |

### `gui` — interfaz clásica de Tkinter

```bash
python -m sofascore gui
python -m sofascore gui --theme oscuro
python -m sofascore gui --timezone America/Bogota --workers 6
```

Abre la ventana clásica de análisis. Comparte historial, preferencias y modelo con la interfaz web.

| Opción | Descripción |
|---|---|
| `--theme` | `auto` (recuerda la última elección), `claro` u `oscuro`. |
| `--timezone` | Zona horaria inicial de la interfaz. |

---

## Estadísticas de forma

| Estadística | Origen en SofaScore | Cálculo |
|---|---|---|
| Goles a favor | Marcador del partido | Suma/media de goles del equipo |
| Goles en contra | Marcador del partido | Suma/media de goles del rival |
| xG a favor | `expectedGoals` | Media del xG generado |
| xG en contra | `expectedGoals` rival | Media del xG concedido |
| Ocasiones claras | `bigChanceCreated` | Media de ocasiones claras |
| Remates dentro del área | `totalShotsInsideBox` | Media de remates dentro del área |
| Tiros de esquina | `cornerKicks` | Suma/media |
| Tarjetas | `yellowCards` + `redCards` | Tarjetas totales |
| Tarjetas amarillas | `yellowCards` | Suma/media |
| Tarjetas rojas | `redCards` | Suma/media |
| Remates totales | `totalShotsOnGoal` | Suma/media |
| Remates al arco | `shotsOnGoal` | Suma/media |
| Faltas | `fouls` | Suma/media |
| Paradas del portero | `goalkeeperSaves` | Suma/media |

SofaScore omite las claves cuyo valor es cero; el programa las interpreta como 0 cuando el partido sí tiene estadísticas. Si un partido no tiene estadísticas disponibles, sus goles siguen contando pero el resto de métricas se excluye de las medias.

### ¿Hace falta Opta u otra plataforma?

No para estas siete métricas: SofaScore ya publica todas ellas para las competiciones profesionales de Europa y Sudamérica. Opta es un proveedor de datos con licencia de pago y no se integra en este proyecto. Si en el futuro se añade otro proveedor, la lógica de descarga está aislada en `sofascore/form.py` y `sofascore/client.py`.

### Temporada y competiciones incluidas

- Se usa la temporada del partido seleccionado. Por ejemplo, `26/27` cubre todos los partidos de esa temporada, aunque el equipo juegue LaLiga y Champions League.
- En ligas de año natural (Brasil, Argentina, etc.) se usa la temporada `2026`.
- Solo se incluyen competiciones cuya categoría pertenece a Europa o Sudamérica.
- Se excluyen amistosos, torneos mundiales y competiciones de selecciones.
- Para «toda la temporada» se limita la muestra a 80 partidos por equipo para evitar cientos de peticiones.

---

## Simulación Monte Carlo

La pestaña **Simulación** y el comando `simulate` responden a «¿qué es probable que ocurra?», no a «¿qué va a ocurrir?». Generan miles de partidos hipotéticos a partir de las medias de forma y devuelven **distribuciones y probabilidades**, que es mucho más informativo que una única cifra.

### Alineaciones y árbitro

**Alineaciones.** Al seleccionar un partido se consulta su alineación y se muestra una etiqueta:

- **Alineación confirmada**: los titulares ya están definidos. El modelo usa sus estadísticas de temporada para ajustar el ataque, los remates, la precisión y el efecto del portero.
- **Alineación probable**: SofaScore ofrece una alineación estimada. El ajuste se aplica solo al **45 %**, porque todavía puede cambiar.
- **Sin datos**: no hay alineación publicada; se usa únicamente el modelo histórico.

El ajuste de alineación compara la producción esperada de los titulares (xG, remates y remates al arco por partido, y valoración media como respaldo) con las medias históricas del equipo. Los factores están limitados a ±7 % para que la alineación no domine al modelo. Si no hay estadísticas de temporada de los jugadores, la etiqueta sigue siendo informativa pero no se aplica ningún ajuste.

**Árbitro.** Si el partido tiene árbitro asignado, se consulta su ficha y sus partidos recientes de la misma competición y temporada. Se calculan:

- Tarjetas por partido (amarillas + rojas).
- Faltas por partido, a partir de las estadísticas de sus partidos dirigidos.

Esos promedios ajustan las tasas de tarjetas y faltas del modelo con factores limitados (0,85–1,25 para tarjetas y 0,85–1,20 para faltas). Si la muestra es pequeña, el ajuste es orientativo y se avisa en el resultado.

### Contexto de fuerza

Para que un buen tramo de forma no convierta en favorito a un equipo claramente inferior, el modelo incorpora un **prior contextual**:

- **Calidad de la plantilla**: valor de mercado de los titulares de la alineación.
- **Clasificación de la competición**: puntos por partido y diferencia de goles por partido.
- **Historial H2H**: victorias, empates y derrotas entre ambos equipos.
- **Valoración media** de los titulares como respaldo cuando falta el valor de mercado.

Las señales se combinan con pesos y límites: el contexto puede ajustar los goles entre ×0,70 y ×1,30, y los remates/córners entre ×0,88 y ×1,12. Así corrige favoritos artificiales sin tapar la forma reciente.

En los partidos **ya finalizados** no se usan clasificación ni H2H para el modelo, porque esas tablas ya incluyen el resultado del partido y producirían fuga de información. Para la validación se usan el valor de la alineación y la forma previa al partido.

### Red neuronal de apoyo

La app incorpora una **MLP multi-salida implementada con NumPy**, sin PyTorch, para que el ejecutable siga siendo ligero. Predice las medias de goles, remates, remates al arco, córners, tarjetas y faltas.

- **Entrenamiento offline** con **11.663 partidos**:
  - Premier League, LaLiga, Serie A, Bundesliga, Ligue 1 y Champions League.
  - Temporadas 2023/24, 2024/25, 2025/26 y 2026/27.
  - Ligas profesionales de Sudamérica: Brasil, Argentina, Colombia, Ecuador, Perú, Chile, Uruguay, Paraguay, Bolivia y Venezuela, con temporadas 2024 y 2025.
  - Copa Libertadores y Copa Sudamericana 2024/2025.
- **10.919 muestras utilizables** tras exigir historial previo.
- **Alineaciones históricas** de los 11.663 partidos: valor de mercado, valoración media, ausencias y confianza de la alineación.
- Features: forma de los últimos 5/10 partidos, splits local/visitante, xG, xG al arco, ocasiones claras, remates dentro del área, estadísticas concedidas, Elo, clasificación, descanso, H2H, calidad de alineación y competición.
- Validación temporal estricta: temporadas anteriores para entrenar, inicio de 2026/27 para validar y los partidos más recientes para probar.
- Ensemble de 5 redes y mezcla conservadora con el modelo existente.
- La mezcla se aplica en goles, remates, remates al arco, córners, tarjetas y faltas; en las salidas donde la validación no mejora, el peso se reduce o se anula.

Métricas de la última prueba:

| Salida | MAE red | MAE baseline |
|---|---:|---:|
| Goles local | **1,03** | 1,12 |
| Goles visitante | **0,94** | 1,03 |
| Remates local | **4,04** | 4,44 |
| Remates visitante | **3,78** | 4,33 |
| Remates al arco local | **1,84** | 2,03 |
| Remates al arco visitante | **1,86** | 2,00 |
| Córners local | **2,25** | 2,27 |
| Córners visitante | **1,88** | 2,10 |
| Tarjetas local | **1,13** | 1,20 |
| Tarjetas visitante | **1,15** | 1,21 |
| Faltas local | **2,98** | 3,08 |
| Faltas visitante | **3,07** | 3,07 |

Los pesos están en `sofascore/models/neural_model.npz` y el modelo se incluye en el ejecutable. Para reentrenar:

```bash
python training/collect_dataset.py
python training/collect_extra.py
python training/collect_lineups.py
python training/train_neural.py
```

El dataset bruto queda en `training/data/dataset.jsonl`, `training/data/dataset_extra.jsonl` y `training/data/lineups.jsonl`; las métricas, en `training/metrics.json`.

### Modelo

- Las medias se ponderan por recencia (los partidos recientes pesan más) y se contraen hacia una referencia común para reducir el ruido de muestras pequeñas.
- Se separa el rendimiento como local y como visitante, y los goles se ajustan con el ataque propio y la defensa del rival.
- Los goles combinan **goles reales y xG** (55 % xG cuando hay datos) y usan el xG concedido por el rival para la defensa.
- Remates, córners, tarjetas y faltas mezclan la producción propia con lo que concede el rival en su misma condición (58 % propia / 42 % rival).
- La probabilidad de remate al arco también se ajusta con la precisión concedida por el adversario.
- Los goles se generan en cadena: **remates → remates al arco → goles**, usando distribuciones beta-binomiales. Así se cumple siempre `goles <= remates al arco <= remates`.
- Remates, córners, tarjetas y faltas usan una **binomial negativa** para permitir sobredispersión.
- Factores latentes compartidos introducen correlación entre métricas del mismo partido (un partido abierto genera más remates y córners; uno intenso, más faltas y tarjetas).
- Las **paradas** se derivan de los remates al arco del rival que no terminaron en gol.
- La semilla hace que el resultado sea reproducible.

### Cómo leer el resultado

- **Media**: el valor esperado, útil como referencia rápida.
- **P10 / P90**: rango central del 80 % de los escenarios. Es más honesto que una media sola.
- **P99**: percentil 99, útil para ver hasta dónde llega la cola sin que un valor extremo distorsione la lectura.
- **Over/Under**: probabilidad de superar una línea (por ejemplo, más de 9,5 córners).
- **1X2, ambos marcan y porterías a cero**: probabilidades agregadas de todos los escenarios.
- **Paradas por arquero**: en Mercados, las paradas se muestran por separado para el portero local y el visitante, cada uno con sus propias líneas over/under.
- **Matriz de marcadores**: porcentaje de veces que aparece cada resultado, con el eje vertical invertido (0 abajo, 6+ arriba) y dos decimales de precisión.

Los histogramas usan un rango dinámico basado en el percentil 99,5 de cada métrica. La última barra (por ejemplo, `33+` en córners) agrupa la cola restante y se muestra con su porcentaje, para que no parezca un pico artificial. La media se calcula siempre con todas las simulaciones, no a partir de las barras.

La simulación no modela lesiones, sanciones, cambios de entrenador ni xG futuro. El contexto se limita a alineación, valor de plantilla, clasificación y H2H; las alineaciones probables pueden cambiar y las tendencias del árbitro son una muestra histórica, no una garantía. Tampoco sustituye una validación contra partidos ya jugados. Si el modelo no supera a una referencia simple (media de la liga o media de los últimos partidos), sus probabilidades no aportan valor.

### Rendimiento

Todo se ejecuta en **CPU con NumPy vectorizado**. En la máquina de prueba, 50.000 escenarios de 12 métricas tardan del orden de 0,1-0,3 s, así que la GPU no aporta ninguna ventaja a esta escala. La interfaz lanza la simulación en un hilo aparte para no congelar la ventana.

### Caché de simulaciones

Cada simulación se guarda en:

```
%LOCALAPPDATA%\sofascore-gui\simulations
```

La clave incluye la versión del modelo, el partido, la ventana, las iteraciones, la semilla, las alineaciones, el árbitro, la clasificación, el H2H y los partidos usados en el análisis. Si cambia cualquiera de esos datos, la simulación se vuelve a calcular. Las entradas caducan a los 7 días.

- Si existe una simulación compatible, la interfaz la carga al instante y lo indica en la barra de estado.
- En partidos en vivo se reutiliza la simulación del modelo, pero las estadísticas actuales se refrescan cada vez que pulsas **Analizar partido**.
- El botón **Vaciar caché** elimina todas las simulaciones guardadas.
- Al cerrar y volver a abrir el programa, las simulaciones siguen disponibles hasta que caduquen o se vacíe la caché.

---

## Opciones globales

Se pueden usar con cualquier comando:

| Opción | Descripción |
|---|---|
| `-o, --output ARCHIVO` | Guarda la salida en un archivo. Si se omite, escribe por stdout. |
| `-f, --format` | `json`, `jsonl` o `csv`. Si se omite, se deduce de la extensión. |
| `--compact` | JSON sin indentación. |
| `--no-cache` | No lee ni escribe caché. |
| `--cache-dir DIR` | Cambia el directorio de caché. |
| `--cache-ttl SEGUNDOS` | Vida de la caché (por defecto 300). |
| `--rate-limit SEGUNDOS` | Separación mínima entre peticiones (por defecto 0.2). |
| `--timeout SEGUNDOS` | Timeout por petición (por defecto 30). |
| `--workers N` | Hilos para consultar torneos en paralelo (por defecto 4). |
| `--proxy URL` | Proxy HTTP(S), por ejemplo `http://127.0.0.1:8080`. |
| `--base-url URL` | URL base alternativa de la API (avanzado). |
| `--dump-raw DIR` | Guarda cada respuesta cruda para depurar. |
| `--debug` | Muestra cada petición HTTP y su estado. |
| `-v, --verbose` | Muestra progreso e información adicional. |

---

## Formatos de salida

### JSON

Formato por defecto. Conserva toda la estructura (listas y objetos anidados).

```bash
python -m sofascore date hoy --country Spain -o partidos.json
```

### JSONL

Un objeto JSON por línea. Ideal para procesar con `jq`, pandas o streaming.

```bash
python -m sofascore date hoy --country Spain -f jsonl -o partidos.jsonl
```

### CSV

Aplana los objetos con notación de puntos (`home_team.name`, `tournament.country`...). Se escribe en **UTF-8 con BOM** para que Excel lo abra correctamente.

```bash
python -m sofascore date hoy --country Spain -f csv -o partidos.csv
```

En `match`, el comportamiento del CSV depende de lo que pidas:

- Una sola sección (`--stats`, `--incidents` o `--lineups`): se exporta **solo esa tabla**.
  ```bash
  python -m sofascore match 16938982 --stats -f csv -o estadisticas.csv
  ```
- Varias secciones o `--all`: se genera un CSV de resumen y un archivo por sección.
  ```bash
  python -m sofascore match 16938982 --all -f csv -o partido.csv
  ```
  Genera, por ejemplo:
  ```
  partido.csv
  partido_stats.csv
  partido_lineups.csv
  partido_incidents.csv
  partido_h2h.json
  partido_graph.json
  partido_best_players.json
  ```

---

## Esquema de datos

Cada partido normalizado contiene:

```json
{
  "id": 16938982,
  "start_timestamp": 1793727900,
  "start_time": "2026-11-03T17:45:00+00:00",
  "start_time_local": "2026-11-03T18:45:00+01:00",
  "status": "Ended",
  "status_type": "finished",
  "status_code": 100,
  "tournament": {
    "id": 7,
    "edition_id": 138314,
    "name": "UEFA Champions League",
    "slug": "uefa-champions-league",
    "category": "Europe",
    "category_id": 1465,
    "country": "Europe"
  },
  "season": {"id": 96518, "name": "UEFA Champions League 26/27", "year": "26/27"},
  "round": 4,
  "home_team": {"id": 3061, "name": "Galatasaray", "short_name": "Galatasaray", "code": "GAL"},
  "away_team": {"id": 2677, "name": "VfB Stuttgart", "short_name": "Stuttgart", "code": "VFB"},
  "home_score": 2,
  "away_score": 0,
  "winner": "home",
  "venue": {"name": "Rams Park Stadyumu", "city": "Istanbul", "country": "Türkiye"},
  "referee": {"name": "Chris Kavanagh", "country": "England"},
  "has_xg": true
}
```

- `start_time` está siempre en **UTC**.
- `start_time_local` solo aparece en `date` y usa `--timezone`.
- `status_type`: `notstarted`, `inprogress`, `finished`, `postponed`, `canceled`, `suspended`...
- `winner`: `home`, `away`, `draw` o `null`.

Las estadísticas se aplanan a filas:

```json
{
  "period": "ALL",
  "group": "Match overview",
  "name": "Ball possession",
  "home": "52%",
  "away": "48%",
  "home_value": 52,
  "away_value": 48,
  "compare_code": 1,
  "statistics_type": "positive",
  "key": "ballPossession"
}
```

Las incidencias:

```json
{
  "type": "goal",
  "class": "regular",
  "minute": 23,
  "side": "home",
  "player": "Player One",
  "assist": "Player Two",
  "home_score": 1,
  "away_score": 0
}
```

Las alineaciones incluyen `formation` y una lista de jugadores por lado con `name`, `shirt_number`, `position`, `substitute`, `captain` y `rating`. Con `--lineup-stats` se añade el objeto `statistics` completo de cada jugador.

---

## Fechas y zonas horarias

La API de SofaScore no devuelve exactamente el día solicitado: devuelve una **ventana de 48 horas** centrada en esa fecha. Por eso el programa:

1. Consulta la ventana de la API.
2. Filtra los partidos por el día real en la zona horaria indicada.
3. Añade `start_time_local` para que no haya ambigüedad.

```bash
# Hora española (recomendado si estás en España)
python -m sofascore date 2026-11-04 --country Spain --timezone Europe/Madrid

# Hora UTC
python -m sofascore date 2026-11-04 --country Spain --timezone UTC

# Offset manual
python -m sofascore date 2026-11-04 --country Spain --timezone -05:00
```

`--timezone local` usa el offset actual del sistema. Si consultas fechas de verano desde invierno, o viceversa, es más fiable indicar la zona IANA (`Europe/Madrid`, `America/Mexico_City`, etc.).

---

## Caché, ritmo y anti-bot

SofaScore protege su API con Cloudflare y comprueba la huella TLS del cliente. El programa:

- Usa [`curl_cffi`](https://github.com/lexiforest/curl_cffi) para imitar a Chrome.
- **Fuerza IPv4** en las peticiones: SofaScore/Varnish devuelve `403 challenge` a muchas conexiones IPv6, aunque la web funcione en el navegador. Si IPv4 no está disponible, vuelve automáticamente a la ruta del sistema.
- Hace una petición previa a `https://www.sofascore.com/` para obtener cookies.
- Envía el token efímero `X-Requested-With` que genera el propio sitio.
- **No** envía un `User-Agent` manual: un UA que no coincide con la huella TLS provoca un `403 challenge`.
- Reintenta con backoff exponencial ante `403`, `429` y errores `5xx`.
- Espacia las peticiones con `--rate-limit` (global, incluso entre hilos). El CLI usa 0,2 s por defecto; el ejecutable de escritorio usa 0,08 s para que «Todas» no tarde demasiado.
- Cachea las respuestas en disco.

Ubicación de la caché:

- Windows: `%LOCALAPPDATA%\sofascore-extractor\cache`
- Linux/macOS: `~/.cache/sofascore-extractor/cache`

Los escudos y banderas se guardan aparte, en `%LOCALAPPDATA%\sofascore-gui\images`.

Para limpiarla, borra ese directorio o usa `--no-cache`.

Si recibes un `403` persistente:

1. Comprueba que la conexión IPv4 funciona. El cliente ya la fuerza por defecto; en una red solo IPv6 puedes desactivarla con `--no-ipv4`.
2. Espera unos minutos.
3. Baja el ritmo: `--rate-limit 1.0 --workers 1`.
4. Prueba con un proxy residencial: `--proxy http://host:puerto`.
5. Si el navegador te pide verificar que eres humano, abre `https://www.sofascore.com/` y completa el captcha; después reintenta.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `Falta la dependencia 'curl_cffi'` | `pip install -r requirements.txt`. |
| `403 (bloqueado por Cloudflare)` | Espera, baja el ritmo o usa `--proxy`. |
| `Zona horaria no válida` | Instala `tzdata` o usa `UTC`/`+02:00`. |
| No aparecen los partidos esperados | Revisa `--timezone`; la API agrupa en una ventana de 48 h. |
| `date` sin filtros tarda mucho | Usa `--country`, `--tournament` o `--max-tournaments`. |
| Error 404 en un partido | El ID no existe o la sección no está disponible para ese partido. |
| La API cambió | Las rutas están centralizadas en `sofascore/endpoints.py`. |

---

## Estructura del proyecto

```
.
├── sofascore/
│   ├── __init__.py
│   ├── __main__.py        # python -m sofascore
│   ├── cli.py             # argumentos y comandos
│   ├── client.py          # HTTP, cookies, reintentos, caché, rate limit
│   ├── endpoints.py       # rutas de la API
│   ├── exceptions.py
│   ├── export.py          # JSON / JSONL / CSV
│   ├── extractor.py       # lógica de partidos, equipos y torneos
│   ├── form.py            # análisis de forma y estadísticas clave
│   ├── charts.py          # gráficos Canvas para la simulación
│   ├── simulation.py      # modelo Monte Carlo con NumPy
│   ├── simulation_cache.py # caché persistente de simulaciones
│   ├── neural.py          # inferencia de la red neuronal (NumPy)
│   ├── models/            # pesos de la red neuronal
│   ├── webapp.py          # servidor local y API de la interfaz web
│   ├── web_ui/            # HTML, CSS y JavaScript de la interfaz
│   ├── settings.py        # preferencias compartidas por web y Tkinter
│   ├── storage.py         # historial SQLite de partidos y predicciones
│   ├── gui.py             # interfaz clásica Tkinter
│   ├── live_desk.py       # sala de directo (modo clásico)
│   ├── journal_window.py  # cuaderno de predicciones (modo clásico)
│   ├── preview_window.py  # estudio de previas (modo clásico)
│   ├── explorer_window.py # explorador y API (modo clásico)
│   ├── normalize.py       # normalización de respuestas
│   ├── regions.py         # competiciones de Europa y Sudamérica
│   └── upcoming.py        # partidos por fecha (próximos y finalizados)
├── tests/
│   ├── test_core.py
│   ├── test_form.py
│   ├── test_simulation.py
│   ├── test_neural.py
│   ├── test_simulation_cache.py
│   ├── test_apps.py       # historial, previas y API
│   └── test_webapp.py     # interfaz web y endpoints
├── training/
│   ├── collect_dataset.py # dataset europeo base
│   ├── collect_extra.py   # más temporadas + Sudamérica y copas
│   ├── collect_lineups.py # alineaciones y valores de plantilla
│   ├── train_neural.py    # entrena y exporta los pesos
│   ├── metrics.json       # métricas de la última prueba
│   └── data/              # dataset de entrenamiento
├── SofaScore.exe          # ejecutable para Windows (doble clic)
├── Iniciar SofaScore.cmd  # lanzador alternativo desde el código fuente
├── launcher.py            # punto de entrada del ejecutable
├── build_exe.ps1          # regenera SofaScore.exe con PyInstaller
├── SofaScore.spec         # configuración de PyInstaller
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Pruebas

Las pruebas no hacen peticiones de red:

```bash
python -m unittest discover -s tests -v
```

Son 64 pruebas: normalización, fechas, zonas horarias, exportación, regiones, estadísticas de forma, análisis completo con un cliente falso, perfil del árbitro, xG y tasas concedidas, contexto de fuerza, red neuronal, validación de partidos finalizados y en vivo, caché de simulaciones y el motor Monte Carlo (reproducibilidad, coherencia, alineaciones, árbitro, percentiles, mercados y serialización).

---

## Limitaciones

- La API es interna y no está documentada; puede cambiar sin aviso.
- No hay descarga masiva de temporadas completas en una sola petición: se pagina por equipo, torneo o fecha.
- Algunas secciones (estadísticas, alineaciones) no existen para partidos no empezados; el programa avisa y continúa.
- El análisis de forma necesita una petición de estadísticas por partido. La primera consulta de una ventana puede tardar; después se usa caché durante 7 días.
- La lista de partidos se limita a las competiciones con mayor prioridad para que la interfaz responda rápido. Usa «Todas» o el comando `upcoming --competitions todas` para ampliarla.
- El listado incluye partidos próximos, en vivo y finalizados. Los partidos en vivo muestran el minuto y el marcador actual; pulsa «Analizar partido» de nuevo para refrescar sus estadísticas.
- Solo se admiten competiciones profesionales de Europa y Sudamérica; los amistosos y torneos mundiales quedan fuera.
- El H2H, el gráfico y los mejores jugadores se devuelven como JSON crudo de la API porque su estructura varía según el partido.
- El xG, las ocasiones claras y los remates dentro del área no están disponibles en todas las competiciones. Si faltan, el modelo usa goles y el resto de estadísticas disponibles; las tasas concedidas por el rival también caen de vuelta a la producción propia.
- La simulación Monte Carlo es un modelo probabilístico a partir de medias históricas: usa alineaciones y árbitro cuando están disponibles, pero no conoce lesiones de última hora, xG futuro ni el contexto del partido. Interpreta sus resultados como escenarios, no como certezas.
- `SofaScore.exe` no está firmado digitalmente. Windows SmartScreen puede pedir confirmación la primera vez; es normal en ejecutables generados con PyInstaller.
- Respeta los límites de SofaScore. Este proyecto no pretende sustituir su API oficial ni sus datos licenciados.
