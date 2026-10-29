# 📊 SIF PyME — Sistema de Facturación y Presupuestos Local

Software de facturación y gestión presupuestaria local para pequeñas empresas, autónomos y estudios de diseño. Diseñado bajo la filosofía **macOS Human Interface Guidelines (HIG)** con arquitectura **FastAPI + SQLite + HTML5 / CSS3 / Vanilla JS**, ejecutable tanto como **aplicación de escritorio nativa (PySide6 / WebEngine sin navegador externo)** como en **modo servidor web local**.

---

## 🌟 Características Principales

- **🖥️ Experiencia Nativa macOS HIG**: Interfaz de escritorio con diseño de ventana unificada, barra de herramientas (*Toolbar*), navegación lateral en dos secciones (*Gestión* y *Directorio*) con contadores en tiempo real (`/api/contadores`), tabla interactiva con selección suave (*NSTableView*) y panel inspector lateral.
- **📄 Facturación Oficial e Histórica**: 
  - Numeración diaria estructurada `FAC-[AÑO]-[MES]-[DIA]-[Identificador]` (ej. `FAC-2026-10-19-001`).
  - Validación de NIF/CIF, IBAN (Módulo 97 ISO 7064) y código postal provincial.
  - Snapshots de emisor y cliente en cada factura para preservar la validez legal del histórico ante cambios futuros.
  - Generación de PDF oficial instantáneo (< 1s) con desglose de IVA y retenciones IRPF.
- **📑 Presupuestos Editoriales y Propuestas de Proyecto**:
  - Propuestas con portada, bienvenida personalizada, fases de trabajo configurables y condiciones comerciales.
  - Soporte de múltiples **Opciones / Variantes** de productos con cálculo automático de rangos de importe (`total_minimo` y `total_maximo`).
  - Conversión directa de la opción aprobada a factura oficial emitida con un solo clic.
  - Paginación dinámica y generación de PDF editorial con control de desbordamiento de productos.
- **📦 Catálogo Avanzado de Productos y Servicios**:
  - Gestión directa y limpia orientada al **Nombre Comercial** y **Descripción Técnica**, prescindiendo de códigos/SKU artificiales innecesarios.
  - **Precios Escalados por Volumen (Tiered Pricing)**: Configuración de tramos de cantidad (ej. 1–49 uds a 6,50 €, 50–99 uds a 5,20 €, 100+ uds a 4,10 €) con ajuste reactivo automático en facturas y presupuestos.
  - **Variantes y Atributos (Colores, Acabados, Tamaños)**: Soporte de selector visual de paleta hexadecimal (`color_hex`), valores descriptivos y recargos (`precio_adicional`) o tarifas fijas (`precio_fijo`).
  - Modal nativo macOS con **Segmented Controls** (*General*, *Escalado de Precios*, *Variantes y Colores*).
  - **Casillas Independientes**: Preservación limpia y desacoplada del *Nombre del Producto* y su *Detalle/Especificación* (`detalle_material`) en facturas y presupuestos sin paréntesis artificiales.
- **🛡️ Integridad de Datos y Seguridad**:
  - Base de datos SQLite local relacional con claves foráneas activadas.
  - Borrado lógico (*Soft Delete*) en facturas, presupuestos, clientes y productos (`is_deleted = 1`).
  - Copias de seguridad automáticas (*Snapshots*) tras la emisión de cada documento fiscal.
  - Bloqueo de concurrencia para evitar duplicación accidental de clientes al crearlos desde modales rápidos.

---

## 💻 Modos de Ejecución

| Modo | Comando | Descripción |
| :--- | :--- | :--- |
| **🖥️ App de Escritorio** | `python desktop.py` | Ventana nativa con Chromium embebido (PySide6), menús del sistema y visor de PDF integrado sin requerir navegador externo. |
| **🌐 Servidor Web Local** | `python main.py` | Servidor FastAPI + Uvicorn estándar accesible desde el navegador en `http://127.0.0.1:8000`. |

---

## 🚀 Instalación y Puesta en Marcha (Entorno de Desarrollo)

### 1. Requisitos Previos
- **Python 3.10** o superior instalado en el sistema.
- Entorno Windows (PowerShell / CMD) o macOS (Apple Silicon / Intel).

### 2. Clonar el repositorio y crear el entorno virtual

```bash
# Navegar a la carpeta del proyecto
cd factura

# Crear el entorno virtual
python -m venv .venv

# Activar el entorno virtual:
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En macOS / Linux:
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Iniciar la aplicación

- **Para iniciar en modo App de Escritorio:**
  ```bash
  python desktop.py
  ```

- **Para iniciar en modo Servidor Web:**
  ```bash
  python main.py
  ```
  Abra su navegador en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🪟 Empaquetado como Ejecutable en Windows (`.exe`)

Para generar un paquete ejecutable autónomo e instalable en Windows:

### 1. Compilación Automática (Script)
Puede ejecutar directamente el script por lotes o PowerShell:
```cmd
build_windows.bat
```
o en PowerShell:
```powershell
.\build_windows.ps1
```

### 2. Compilación Manual con PyInstaller
```powershell
pip install -r requirements.txt
python -m PyInstaller SIF_PyME.spec --clean
```

El paquete generado se ubicará en:
```
dist/
└── SIF_PyME/
    ├── SIF_PyME.exe     # Ejecutable principal de escritorio
    └── ...              # Librerías y Chromium WebEngine
```

---

## 🍏 Empaquetado y Distribución para macOS (`.app` y `.dmg`)

Debido a que PyInstaller compila binarios ejecutables nativos (*Mach-O*), la distribución para macOS **debe compilarse directamente en una máquina con macOS** (Apple Silicon M1/M2/M3/M4 o Intel) o mediante un flujo de integración continua (CI) como **GitHub Actions**.

### 1. Compilación Automática (Script)

El proyecto incluye el script ejecutable [`build_macos.sh`](file:///build_macos.sh) que compila la app, aplica la firma de código y empaqueta la imagen de disco `.dmg`:

```bash
# Dar permisos de ejecución si es necesario
chmod +x build_macos.sh

# Ejecutar la compilación
./build_macos.sh
```

El script genera automáticamente:
- **`dist/SIF PyME.app`**: Paquete de aplicación nativa con su icono oficial `.icns` y metadatos en `Info.plist`.
- **`dist/SIF_PyME.dmg`**: Instalador clásico de macOS con acceso directo arrastrable a `/Applications`.

---

### 2. Compilación Manual Paso a Paso

Si prefiere compilar manualmente o personalizar los parámetros:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Compilar con PyInstaller
python3 -m PyInstaller SIF_PyME.spec --clean --noconfirm

# 3. Firmar código (Firma Ad-hoc para uso local o interno)
codesign --force --deep --sign - "dist/SIF PyME.app"

# 4. Crear imagen de disco DMG con hdiutil nativo
mkdir -p dist/dmg_staging
cp -R "dist/SIF PyME.app" dist/dmg_staging/
ln -s /Applications dist/dmg_staging/Aplicaciones
hdiutil create -volname "SIF PyME" -srcfolder dist/dmg_staging -ov -format UDZO dist/SIF_PyME.dmg
rm -rf dist/dmg_staging
```

---

### 3. Distribución y Seguridad en macOS (Gatekeeper)

#### Para distribución interna / sin cuenta de Apple Developer:
Al distribuir una aplicación firmada *ad-hoc*, macOS Gatekeeper puede mostrar un aviso de *"Desarrollador no identificado"* o *"La aplicación está dañada"*. Para abrirla:
1. En el Mac del destinatario: hacer clic secundario (clic derecho) en la app y seleccionar **Abrir** > **Abrir de todos modos**.
2. O bien desde Terminal:
   ```bash
   xattr -cr "/Applications/SIF PyME.app"
   ```

#### Para distribución comercial / oficial con Apple Developer:
Si dispone de una suscripción activa al *Apple Developer Program*:
1. Exporte su identidad:
   ```bash
   export APPLE_SIGNING_IDENTITY="Developer ID Application: Tu Nombre"
   ./build_macos.sh
   ```
2. Notarice el paquete DMG con Apple:
   ```bash
   xcrun notarytool submit dist/SIF_PyME.dmg \
     --apple-id "tu-email@apple.com" \
     --team-id "TU_TEAM_ID" \
     --password "tu-app-specific-password" \
     --wait
   ```
3. Grape la notarización al archivo final:
   ```bash
   xcrun stapler staple dist/SIF_PyME.dmg
   ```

---

## 🧪 Robustez y Suite de Tests Automatizados

La aplicación cuenta con una suite completa de **47 tests automatizados** (`pytest`) que validan:
- **Identificadores fiscales y cuentas bancarias**: Algoritmos de control para NIF, NIE, CIF, VAT intracomunitario e IBAN Módulo 97.
- **Cálculos financieros**: Redondeo `ROUND_HALF_UP` en bases imponibles, cuotas de IVA, retenciones IRPF y subtotales.
- **Presupuestos Editoriales**: Creación, rangos de precio mínimo/máximo, asociación de opciones, filtros de líneas y conversión a facturas.
- **Ciclo de vida y edición de facturas**: Creación, edición completa con recálculo dinámico (`PUT /api/facturas/{id}`), coherencia de fechas, generación de PDF oficial y prevención de duplicidad en series diarias `FAC-[AÑO]-[MES]-[DIA]-[Identificador]`.
- **Productos con nombre y descripción**: Integridad del modelo de catálogo y retrocompatibilidad.

Para ejecutar los tests automatizados:
```powershell
python -m pytest -v
```

---

## 📁 Estructura del Proyecto

`
factura/
├── desktop.py                      # Punto de entrada App de Escritorio (PySide6)
├── main.py                         # Punto de entrada Servidor Web (FastAPI + Uvicorn)
├── pyproject.toml                  # Configuración de empaquetado y herramientas Python (PEP 518/621)
├── requirements.txt                # Dependencias del proyecto y testing
├── SIF_PyME.spec                   # Configuración PyInstaller multiplataforma
├── schema.sql                      # Esquema SQLite relacional con soporte presupuestario
├── build_windows.ps1               # Forwarder de compilación Windows (PowerShell)
├── build_windows.bat               # Forwarder de compilación Windows (CMD)
├── build_macos.sh                  # Forwarder de compilación macOS (Bash)
├── .editorconfig                   # Estándares de indentación y codificación de archivos
├── .gitattributes                  # Normalización de saltos de línea LF/CRLF multiplataforma
├── .gitignore                      # Exclusiones de Git (entornos, temporales, binarios)
├── app/
│   ├── paths.py                    # Gestor central de rutas seguras por sistema operativo
│   ├── database.py                 # Conexión SQLite thread-safe y migraciones automáticas
│   ├── models.py                   # Modelos y esquemas de validación Pydantic v2
│   ├── validators.py               # Validador algorítmico de NIF, NIE, CIF, IBAN y CP
│   ├── errors.py                   # Jerarquía tipada de excepciones de negocio y API
│   ├── routes/
│   │   ├── pages.py                # Vistas HTML renderizadas por Jinja2
│   │   ├── facturas.py             # API REST Facturas y generación PDF oficial
│   │   ├── presupuestos.py         # API REST Presupuestos, opciones y conversión
│   │   ├── clientes.py             # API REST Clientes con validaciones fiscales
│   │   ├── productos.py            # API REST Catálogo de productos (nombre + descripción)
│   │   └── configuracion.py        # API REST Configuración fiscal, presupuestaria y contadores
│   ├── services/
│   │   ├── pdf_service.py          # Generador de PDFs de facturas de alta velocidad con fpdf2
│   │   ├── presupuesto_pdf_service.py # Generador de propuestas y presupuestos editoriales
│   │   ├── version_service.py      # Historial inmutable y reversión estilo Time Machine
│   │   └── backup_service.py       # Snapshots automáticos de base de datos
│   ├── static/
│   │   ├── icon.ico                # Icono para Windows y favicon web
│   │   ├── icon.icns               # Icono para macOS App Bundle
│   │   ├── css/
│   │   │   ├── macos.css           # Sistema de diseño nativo macOS HIG y componentes UI
│   │   │   └── styles.css          # Estilos base y componentes utilitarios
│   │   ├── fonts/                  # Tipografías locales seguras (Inter, Georgia)
│   │   ├── img/                    # Activos visuales y plantillas de diseño
│   │   └── js/
│   │       ├── app.js              # Lógica global, MacPagination, autocompletado y modales
│   │       ├── macos_controller.js # Controlador de la vista de facturas e inspector
│   │       └── onboarding.js       # Asistente de configuración inicial paso a paso
│   └── templates/
│       ├── base.html               # Layout unificado con sidebar de navegación y toolbar
│       ├── index.html              # Vista de Facturas con inspector lateral y balance
│       ├── nueva_factura.html      # Emisión rápida de factura oficial
│       ├── presupuestos.html       # Listado de presupuestos y propuestas de diseño
│       ├── nuevo_presupuesto.html  # Creador multipágina de presupuestos y variantes
│       ├── clientes.html           # Directorio y gestión de clientes
│       ├── productos.html          # Directorio y catálogo de productos / servicios
│       ├── papelera.html           # Papelera de reciclaje y restauración lógica
│       ├── configuracion.html      # Ajustes fiscales y personalización de propuestas
│       └── components/
│           └── onboarding_sheet.html # Modal nativo de bienvenida y setup fiscal
├── bruno/                          # Colección completa de pruebas de API REST para Bruno
│   ├── 01-Productos/               # CRUD de productos, escalados de volumen y variantes
│   ├── 02-Clientes/                # CRUD de clientes y validaciones
│   ├── 03-Presupuestos/            # Creación, descarga PDF y conversión a factura
│   ├── 04-Facturas/                # Facturación, detalle_material independiente y PDF oficial
│   ├── 05-Configuracion/           # Ajustes fiscales, presupuestos y contadores
│   ├── 06-Versiones/               # Historial inmutable y reversión estilo Time Machine
│   ├── 07-Papelera/                # Recuperación lógica y destrucción definitiva
│   ├── 08-Copias de Seguridad/     # Snapshots de base de datos y restauración
│   ├── 09-Descuentos/              # CRUD de descuentos, promociones y visibilidad
│   ├── environments/               # Variables de entorno (Local)
│   └── bruno.json                  # Manifiesto de la colección Bruno
├── docs/
│   ├── MANUAL_DE_USUARIO.md        # Manual oficial de usuario y guía operativa (Markdown)
│   ├── MANUAL_DE_USUARIO.pdf       # Manual editorial oficial en PDF (12 páginas con capturas)
│   ├── INCIDENCIAS_CODE_REVIEW.md  # Control de auditoría técnica e incidencias resueltas
│   ├── PLAN_DE_PRUEBAS.md          # Matriz exhaustiva de pruebas unitarias y edge cases
│   ├── TAREAS_PENDIENTES.md        # Registro de incidencias resueltas, roadmap y notas
│   └── PROPUESTAS_FUNCIONALIDADES.md # Análisis de nuevas funcionalidades, comercial y UX
├── scripts/
│   ├── build_windows.ps1           # Script PowerShell de compilación Windows (.exe + Setup)
│   ├── build_windows.bat           # Script por lotes de compilación Windows
│   ├── build_macos.sh              # Script Bash de compilación macOS (.app + .dmg + .pkg)
│   ├── build_macos_pkg.sh          # Generador de instalador nativo Apple PKG
│   ├── installer_windows.iss       # Configuración del instalador Setup de Inno Setup
│   └── restore_backup.py           # CLI interactivo de restauración de snapshots
└── tests/
    ├── conftest.py                             # Fixtures de pytest con base de datos en memoria
    ├── test_validators.py                      # Tests unitarios de NIF, NIE, CIF, IBAN y CP
    ├── test_calculos.py                        # Tests de redondeo y totales financieros
    ├── test_api_facturas.py                    # Tests de integración API de facturación
    ├── test_api_presupuestos.py                # Tests de integración API de presupuestos
    ├── test_productos_nombre.py                # Tests de catálogo de productos
    ├── test_productos_escalados_variantes.py   # Tests de escalados de volumen y variantes
    ├── test_versiones_y_papelera.py            # Tests de versiones, papelera y backups
    ├── test_paginacion.py                      # Tests de paginación integral backend
    └── test_onboarding.py                      # Tests del asistente de configuración inicial
`

---

## 🗄️ Persistencia de Datos y Archivos

El sistema almacena los datos de forma aislada respetando las directivas del sistema operativo:

### En macOS (Apple HIG):
- **Base de Datos SQLite**: `~/Library/Application Support/SIF PyME/facturacion_pyme.db`
- **Copias de Seguridad (Snapshots)**: `~/Library/Application Support/SIF PyME/Backups/Snapshots/`
- **Documentos PDF**: `~/Documents/Facturas/PDFs/{AÑO}/{MES}/` y `~/Documents/Facturas/Presupuestos/{AÑO}/`

### En Windows / Linux:
- **Base de Datos y Backups**: `~/Facturas/`
- **Documentos PDF**: `~/Facturas/PDFs/{AÑO}/{MES}/` y `~/Facturas/Presupuestos/{AÑO}/`

> **Protección contra pérdida de datos**: Ningún registro se borra físicamente de la base de datos (`is_deleted = 1`). Cada vez que se genera una factura, se crea un snapshot timestamped en el directorio de backups.

---

## 📡 API REST y Documentación Interactiva

Si ejecuta la aplicación con `python main.py`, dispone de:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Colección Bruno**: Carpeta `bruno/` lista para importar en el cliente [Bruno](https://www.usebruno.com/).
