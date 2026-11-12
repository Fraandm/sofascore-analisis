# Instalador de Windows

Este directorio contiene la configuración de **Inno Setup** para generar el
instalador de SofaScore.

## Generar el instalador

Desde la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
```

El script:

1. Compila `SofaScore.exe` con PyInstaller (se puede omitir con `-SkipExe`).
2. Lee la versión desde `sofascore/__init__.py`.
3. Genera `dist-installer/SofaScore-Setup-<versión>.exe`.
4. Crea `dist-installer/SHA256SUMS.txt`.

## Probar el instalador

```powershell
powershell -ExecutionPolicy Bypass -File .\test_installer.ps1
```

La prueba instala en una carpeta temporal, inicia la copia instalada, comprueba
la API local, desinstala y limpia la carpeta.

## Instalación

- Instalación **por usuario**, sin permisos de administrador.
- Carpeta por defecto: `%LOCALAPPDATA%\Programs\SofaScore`.
- Crea acceso directo en el menú Inicio y, opcionalmente, en el escritorio.
- Incluye desinstalador.
- El historial y las preferencias en `%LOCALAPPDATA%\sofascore-gui` se conservan
  al desinstalar.

> El instalador no está firmado digitalmente. Windows SmartScreen puede mostrar
> un aviso la primera vez: pulsa **Más información → Ejecutar de todas formas**.

## Releases automáticas

El workflow `.github/workflows/release.yml` compila el ejecutable y el
instalador en Windows cuando se publica un tag `v*`, y adjunta el instalador y
las sumas SHA-256 a la release de GitHub.

```bash
git tag v1.16.0
git push origin v1.16.0
```
