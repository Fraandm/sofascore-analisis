# Entrenamiento de la red neuronal

La red es una MLP multi-salida en NumPy. No requiere PyTorch ni GPU: el
entrenamiento offline tarda segundos o pocos minutos y la inferencia en la app
es una sola pasada de milisegundos.

## 1. Recopilar datos

```bash
python training/collect_dataset.py
python training/collect_extra.py
python training/collect_national.py
python training/collect_lineups.py
```

- `collect_dataset.py` descarga las cinco grandes ligas y Champions League
  2025/26 y 2026/27.
- `collect_extra.py` añade 2023/24 y 2024/25, las principales ligas
  profesionales de Sudamérica (2024 y 2025), Copa Libertadores y Copa
  Sudamericana (2024 y 2025).
- `collect_national.py` recoge competiciones oficiales de selecciones
  masculinas absolutas: Nations League, Copa América, Mundial, Eurocopa,
  Copa Oro, Copa Africana, Copa Asiática, Finalissima, clasificaciones
  continentales (Eurocopa, Copa Asiática y Copa Africana) y todas las
  eliminatorias mundialistas (UEFA, CONMEBOL, CAF, CONCACAF, AFC y OFC,
  además de la repesca intercontinental).
- `collect_lineups.py` recoge las alineaciones históricas y sus valores de
  mercado.

Los resultados se guardan en `training/data/dataset.jsonl`,
`training/data/dataset_extra.jsonl`, `training/data/dataset_national.jsonl` y
`training/data/lineups.jsonl`.

### Amistosos

Los amistosos internacionales (`851` y `852`) se excluyen explícitamente del
dataset de selecciones y el entrenador también los descarta si aparecen en
cualquier archivo. Se pueden analizar en la interfaz, pero no influyen en los
pesos de la red neuronal.

El recolector de selecciones es reanudable: si la API bloquea temporalmente las
estadísticas, vuelve a ejecutarlo y continuará sin duplicar los partidos ya
guardados.

## 2. Entrenar

```bash
python training/train_neural.py
```

El entrenador combina los tres datasets, deduplica por ID, cruza las
alineaciones y genera:

- `sofascore/models/neural_model.npz` — pesos, medias de normalización,
  historial Elo y métricas.
- `training/metrics.json` — split, MAE de la red y baseline, pesos de mezcla
  y métricas separadas para clubes y selecciones.

## Características

- Forma de los últimos 5 y 10 partidos.
- Splits local/visitante.
- xG, xG al arco, ocasiones claras, remates dentro del área, estadísticas
  concedidas, córners, tarjetas y faltas.
- Elo prepartido calculado de forma incremental.
- Clasificación, descanso y H2H anterior al partido.
- Valor de mercado y valoración media de la alineación, ausencias y
  confianza de la alineación.
- Contexto de competición mediante one-hot, con columnas propias para las
  competiciones de selecciones y un indicador genérico de partido de
  selecciones que también se activa en amistosos.
- Validación temporal: temporadas anteriores para entrenar, inicio de 2026/27
  para validar y los partidos más recientes para probar.
- Datos de Europa, Sudamérica y selecciones. Las selecciones usan un mínimo
  de dos partidos previos para poder aprovechar su calendario más disperso.

## Integración

La app carga los pesos automáticamente. Si el archivo no existe, sigue
funcionando con el modelo contextual. La red solo se mezcla en las salidas
donde mejora la validación.

## Reentrenar

Basta con volver a ejecutar los comandos. La caché de simulaciones incluye la
versión del modelo, así que se invalida automáticamente cuando cambian los
pesos.
