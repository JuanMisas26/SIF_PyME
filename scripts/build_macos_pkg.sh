#!/usr/bin/env bash
# ==============================================================================
# Script de Generación de Instalador Nativo macOS (.pkg) para SIF PyME
# Utiliza las herramientas oficiales de Apple: pkgbuild y productbuild.
# ==============================================================================

set -e

# Asegurar ejecución desde la raíz del proyecto
cd "$(dirname "$0")/.."

echo "========================================================"
echo "   SIF PyME — Generador de Instalador macOS (.pkg)"
echo "========================================================"
echo ""

APP_NAME="SIF PyME"
BUNDLE_ID="com.sifpyme.facturacion"
VERSION="1.0.0"

# 1. Comprobar sistema operativo
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "[AVISO] Este script debe ejecutarse directamente en macOS."
    echo "pkgbuild y productbuild son herramientas nativas de Apple que requieren macOS."
    exit 1
fi

# 2. Verificar que la aplicación ya esté compilada
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "[*] 'dist/${APP_NAME}.app' no encontrado. Ejecutando compilación previa..."
    ./build_macos.sh
fi

BUILD_DIR="dist/pkg_build"
PKG_COMPONENT="${BUILD_DIR}/SIF_PyME_Component.pkg"
PKG_FINAL="dist/SIF_PyME_v${VERSION}_Installer.pkg"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "[*] Creando paquete componente con pkgbuild..."
pkgbuild \
    --component "dist/${APP_NAME}.app" \
    --install-location "/Applications" \
    "$PKG_COMPONENT"

echo "[*] Generando archivo de especificación de distribución..."
DISTRIBUTION_XML="${BUILD_DIR}/distribution.xml"
cat <<EOF > "$DISTRIBUTION_XML"
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>${APP_NAME}</title>
    <options customize="never" require-scripts="false"/>
    <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
    <choices-outline>
        <line choice="default">
            <line choice="${BUNDLE_ID}"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="${BUNDLE_ID}" visible="false">
        <pkg-ref id="${BUNDLE_ID}"/>
    </choice>
    <pkg-ref id="${BUNDLE_ID}" version="${VERSION}" onConclusion="none">SIF_PyME_Component.pkg</pkg-ref>
</installer-gui-script>
EOF

echo "[*] Creando instalador final con productbuild..."
productbuild \
    --distribution "$DISTRIBUTION_XML" \
    --package-path "$BUILD_DIR" \
    "$PKG_FINAL"

# Limpieza temporal
rm -rf "$BUILD_DIR"

echo ""
echo "========================================================"
echo "  [ÉXITO] Instalador macOS generado con éxito:"
echo "  - Archivo instalable: ${PKG_FINAL}"
echo "========================================================"

