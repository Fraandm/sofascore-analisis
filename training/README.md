# Entrenamiento de la red neuronal

La red es una MLP multi-salida en NumPy. No requiere PyTorch ni GPU: el
entrenamiento offline tarda segundos y la inferencia en la app es una sola
pasada de milisegundos.

## 1. Recopilar datos

```bash
python training/collect_dataset.py
python training/collect_extra.py
python training/collect_lineups.py
```

El primero descarga las cinco grandes ligas y Champions League 2025/26 y
2026/27. El segundo añade 2023/24 y 2024/25, las principales ligas
profesionales de Sudamérica (2024 y 2025), Copa Libertadores y Copa
Sudamericana (2024 y 2025). El tercero recoge las alineaciones históricas y
sus valores de mercado. Los resultados se guardan en
`training/data/dataset.jsonl`, `training/data/dataset_extra.jsonl` y
`training/data/lineups.jsonl`.

## 2. Entrenar

```bash
python training/train_neural.py
```

El entrenador combina ambos datasets, deduplica por ID, cruza las
alineaciones y genera:

- `sofascore/models/neural_model.npz` — pesos, medias de normalización,
  historial Elo y métricas.
- `training/metrics.json` — split, MAE de la red y baseline, y pesos de mezcla.

## Características

- Forma de los últimos 5 y 10 partidos.
- Splits local/visitante.
- xG, xG al arco, ocasiones claras, remates dentro del área, estadísticas
  concedidas, córners, tarjetas y faltas.
- Elo prepartido calculado de forma incremental.
- Clasificación, descanso y H2H anterior al partido.
- Valor de mercado y valoración media de la alineación, ausencias y
  confianza de la alineación.
- Contexto de competición mediante one-hot.
- Validación temporal: 2023/24–2025/26 para entrenar, inicio de 2026/27
  para validar y los partidos más recientes para probar.
- Datos de Europa y Sudamérica, incluidas Libertadores y Sudamericana.

## Integración

La app carga los pesos automáticamente. Si el archivo no existe, sigue
funcionando con el modelo contextual. La red solo se mezcla en las salidas
donde mejora la validación; actualmente goles y tarjetas.

## Reentrenar

Basta con volver a ejecutar los dos comandos. La caché de simulaciones
incluye la versión del modelo, así que se invalida automáticamente cuando
cambian los pesos.
