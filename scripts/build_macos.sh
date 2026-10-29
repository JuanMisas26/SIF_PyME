#!/usr/bin/env bash
# ==============================================================================
# Script de Compilación y Empaquetado macOS (.app, .dmg y .pkg) para SIF PyME
# Permite generar los paquetes distribuibles completos de la aplicación en macOS.
# ==============================================================================

set -e

# Asegurar ejecución desde la raíz del proyecto
cd "$(dirname "$0")/.."

echo "========================================================"
echo "   SIF PyME — Compilación de Distribución macOS         "
echo "========================================================"
echo ""

# 1. Comprobar sistema operativo
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "[AVISO] Este script debe ejecutarse directamente en un sistema macOS o runner CI/CD."
    echo "PyInstaller requiere el kernel de macOS para compilar binarios Mach-O."
    exit 1
fi

# 2. Activar entorno virtual de Python
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 3. Comprobar / instalar dependencias
if ! command -v pyinstaller &> /dev/null; then
    echo "[*] PyInstaller no detectado. Instalando dependencias..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 4. Limpieza de artefactos previos
echo "[*] Limpiando carpetas build/ y dist/..."
rm -rf build
rm -rf "dist/SIF PyME.app"
rm -rf "dist/SIF_PyME.dmg"
rm -rf dist/*.pkg

# 5. Compilación con PyInstaller usando el spec multiplataforma
echo "[*] Iniciando compilación con PyInstaller..."
python3 -m PyInstaller SIF_PyME.spec --clean --noconfirm

if [ ! -d "dist/SIF PyME.app" ]; then
    echo "[ERROR] No se pudo generar 'dist/SIF PyME.app'."
    exit 1
fi

# 6. Verificación e inyección de plugins de Qt (Cocoa) y archivo de configuración qt.conf
echo "[*] Verificando plugins de Qt (QPA Cocoa)..."
APP_BUNDLE="dist/SIF PyME.app"
COCOA_FOUND=$(find "$APP_BUNDLE" -name "libqcocoa.dylib" 2>/dev/null | head -n 1)

if [ -z "$COCOA_FOUND" ]; then
    echo "[AVISO] libqcocoa.dylib no detectado en el bundle. Buscando en entorno Python..."
    PY_PLUGINS_DIR=$(python3 -c "import PySide6, os; p=os.path.join(os.path.dirname(PySide6.__file__), 'Qt', 'plugins'); print(p if os.path.isdir(p) else os.path.join(os.path.dirname(PySide6.__file__), 'plugins'))" 2>/dev/null || true)
    if [ -n "$PY_PLUGINS_DIR" ] && [ -d "$PY_PLUGINS_DIR/platforms" ]; then
        echo "[*] Copiando plugins de Qt desde $PY_PLUGINS_DIR..."
        mkdir -p "$APP_BUNDLE/Contents/Frameworks/PySide6/Qt/plugins"
        cp -R "$PY_PLUGINS_DIR/"* "$APP_BUNDLE/Contents/Frameworks/PySide6/Qt/plugins/"
        COCOA_FOUND="$APP_BUNDLE/Contents/Frameworks/PySide6/Qt/plugins/platforms/libqcocoa.dylib"
    fi
fi

# Asegurar Contents/Resources/qt.conf
mkdir -p "$APP_BUNDLE/Contents/Resources"
if [ ! -f "$APP_BUNDLE/Contents/Resources/qt.conf" ]; then
    echo "[*] Generando Contents/Resources/qt.conf..."
    cat << 'EOF' > "$APP_BUNDLE/Contents/Resources/qt.conf"
[Paths]
Prefix = ../Frameworks
Plugins = PySide6/Qt/plugins
Resources = PySide6/Qt/resources
Translations = PySide6/Qt/translations
EOF
fi

# Crear fallback en Contents/MacOS/platforms para el loader de Qt
PLATFORMS_DIR=$(find "$APP_BUNDLE" -type d -name "platforms" 2>/dev/null | head -n 1)
if [ -n "$PLATFORMS_DIR" ] && [ ! -e "$APP_BUNDLE/Contents/MacOS/platforms" ]; then
    echo "[*] Configurando enlace de respaldo Contents/MacOS/platforms..."
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    cp -R "$PLATFORMS_DIR" "$APP_BUNDLE/Contents/MacOS/"
fi

if [ -f "$APP_BUNDLE/Contents/MacOS/platforms/libqcocoa.dylib" ] || [ -n "$COCOA_FOUND" ]; then
    echo "[✓] Plugin Cocoa de Qt verificado con éxito."
else
    echo "[ERROR CRÍTICO] No se pudo encontrar ni empaquetar libqcocoa.dylib."
    exit 1
fi

# 7. Firma de código (Ad-Hoc por defecto; personalizable con IDENTIDAD)
SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:--}"

echo "[*] Firmando código con identidad: $SIGNING_IDENTITY"
codesign --force --deep --sign "$SIGNING_IDENTITY" "dist/SIF PyME.app" || true

# 8. Generación de Imagen de Disco (.dmg)
echo "[*] Generando imagen de disco DMG de distribución..."
DMG_STAGING="dist/dmg_staging"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

# Copiar la aplicación y crear enlace simbólico a la carpeta Aplicaciones
cp -R "dist/SIF PyME.app" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Aplicaciones"

# Crear el DMG comprimido con hdiutil
hdiutil create \
    -volname "SIF PyME" \
    -srcfolder "$DMG_STAGING" \
    -ov \
    -format UDZO \
    "dist/SIF_PyME.dmg"

# Limpieza temporal del directorio staging
rm -rf "$DMG_STAGING"

# 9. Generación del instalador nativo Apple (.pkg)
if [ -f "scripts/build_macos_pkg.sh" ]; then
    echo "[*] Generando instalador nativo Apple (.pkg)..."
    chmod +x scripts/build_macos_pkg.sh
    ./scripts/build_macos_pkg.sh
fi

echo ""
echo "========================================================"
echo "  [ÉXITO] Distribución para macOS completada:"
echo "  - Bundle de Aplicación: dist/SIF PyME.app"
echo "  - Instalador DMG:       dist/SIF_PyME.dmg"
echo "  - Instalador PKG:       dist/SIF_PyME_v1.0.0_Installer.pkg"
echo "========================================================"

