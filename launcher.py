"""Punto de entrada para el ejecutable de Windows.

La interfaz web local es la opción por defecto. El modo clásico de Tkinter
sigue disponible con ``SofaScore.exe --classic`` o ``python -m sofascore gui``.

Genera SofaScore.exe con:
    python -m PyInstaller --noconfirm --clean SofaScore.spec
"""

from sofascore.webapp import main

if __name__ == "__main__":
    raise SystemExit(main())
