# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
from pathlib import Path
_model_path = Path('sofascore/models/neural_model.npz')
if _model_path.exists():
    datas.append((str(_model_path), 'sofascore/models'))
_web_ui = Path('sofascore/web_ui')
if _web_ui.exists():
    datas.append((str(_web_ui), 'sofascore/web_ui'))
_metrics_path = Path('training/metrics.json')
if _metrics_path.exists():
    datas.append((str(_metrics_path), 'training'))
tmp_ret = collect_all('curl_cffi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tzdata')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += [
    'sofascore.gui',
    'sofascore.charts',
    'sofascore.live_desk',
    'sofascore.journal_window',
    'sofascore.preview_window',
    'sofascore.explorer_window',
    'sofascore.storage',
    'sofascore.settings',
    'sofascore.upcoming',
]


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SofaScore',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
