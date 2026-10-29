# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec multiplataforma para SIF PyME (Windows y macOS).
Genera:
- En Windows: Carpeta distribuible dist/SIF_PyME/ con SIF_PyME.exe y todos sus recursos.
- En macOS: Paquete .app independiente dist/SIF PyME.app.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Raíz del proyecto
PROJECT_ROOT = Path('.').resolve()

# Recolección exhaustiva de PySide6 y Shiboken6 (plugins de plataforma cocoa/windows,
# recursos webengine, traducciones, metadatos y dependencias dinámicas)
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all('PySide6')
shiboken6_datas, shiboken6_binaries, shiboken6_hidden = collect_all('shiboken6')

# Archivos de datos que deben empaquetarse dentro del ejecutable
added_datas = [
    ('app/static', 'app/static'),
    ('app/templates', 'app/templates'),
    ('schema.sql', '.'),
] + pyside6_datas + shiboken6_datas

# Dependencias dinámicas que Uvicorn, FastAPI y PySide6 cargan en tiempo de ejecución
hidden_imports = [
    # Uvicorn internals
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',

    # FastAPI y dependencias
    'fastapi',
    'starlette',
    'pydantic',
    'pydantic_core',
    'jinja2',
    
    # Generación PDF y base de datos
    'fpdf',
    'sqlite3',

    # Módulos de la aplicación
    'main',
    'app.paths',
    'app.database',
    'app.errors',
    'app.models',
    'app.validators',
    'app.routes.pages',
    'app.routes.clientes',
    'app.routes.productos',
    'app.routes.facturas',
    'app.routes.configuracion',
    'app.routes.presupuestos',
    'app.services.pdf_service',
    'app.services.presupuesto_pdf_service',
    'app.services.backup_service',
    'app.services.version_service',
] + pyside6_hidden + shiboken6_hidden

combined_binaries = pyside6_binaries + shiboken6_binaries

a = Analysis(
    ['desktop.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=combined_binaries,
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# En Windows, evitar que PyInstaller empaquete DLLs obsoletas de ICU procedentes de Anaconda/PATH
# (Windows 10/11 provee icuuc.dll nativo compatible en System32)
if sys.platform == 'win32':
    _conflicting_prefixes = ('icuuc', 'icudt', 'icuin', 'icuio')
    a.binaries = [
        b for b in a.binaries
        if not any(Path(b[0]).name.lower().startswith(p) for p in _conflicting_prefixes)
    ]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SIF_PyME',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str((PROJECT_ROOT / 'app' / 'static' / 'icon.ico').resolve()) if (PROJECT_ROOT / 'app' / 'static' / 'icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SIF_PyME',
)

# Empaquetado como .app en macOS (se omite automáticamente en Windows/Linux)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='SIF PyME.app',
        icon='app/static/icon.icns' if Path('app/static/icon.icns').exists() else None,
        bundle_identifier='com.sifpyme.facturacion',
        info_plist={
            'CFBundleDisplayName': 'SIF PyME',
            'CFBundleName': 'SIF PyME',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
            'NSRequiresAquaSystemAppearance': False,
            'NSHumanReadableCopyright': 'Copyright © 2026 SIF PyME. Todos los derechos reservados.',
        },
    )
