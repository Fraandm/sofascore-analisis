# Datos de entrenamiento

Los archivos `*.jsonl` de esta carpeta no se incluyen en el repositorio porque
son datasets generados y pueden ser grandes.

Para reconstruirlos:

```bash
python training/collect_dataset.py
python training/collect_extra.py
python training/collect_lineups.py
```

Después puedes entrenar el modelo con:

```bash
python training/train_neural.py
```

El modelo activo (`sofascore/models/neural_model.npz`) y las métricas
(`training/metrics.json`) sí se versionan para que la aplicación funcione al
clonar el repositorio.
