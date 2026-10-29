# 📋 Registro de Tareas y Roadmap — SIF PyME

Documento de seguimiento de incidencias, mejoras funcionales y hoja de ruta del proyecto.

---

## 📌 Tareas Pendientes (Roadmap Futuro)

- [ ] **Generación y verificación de instaladores en cada plataforma**:
  - **Windows**: Compilación con Inno Setup (`dist/SIF_PyME_v1.0.0_Windows_Setup.exe`).
  - **macOS**: Compilación con Apple Tools (`dist/SIF_PyME.dmg` y `dist/SIF_PyME_v1.0.0_Installer.pkg`).
- [ ] **Facturas Rectificativas y Abonos (Devoluciones)**:
  - Serie independiente `REC-...` y vinculación legal a factura de origen según RD 1619/2012.

---

## ✅ Tareas Completadas

### 0. Auditoría de Código y Calidad (Octubre 2026 — 100% Resuelta)
- [x] **[LOG-07] Preservación de partidas exentas / 0% IVA en facturas**: Soporte explícito para líneas no gravadas o suplidos sin forzarlas al 21%.
- [x] **[LOG-08] Deducción proporcional de IVA e IRPF en partidas negativas**: Anticipos y entregas a cuenta deducen la base y la cuota impositiva proporcionalmente.
- [x] **[RES-01] Prevención de fuga de descriptores SQLite en `get_pdf_storage_dir()`**: Cierre garantizado con bloque `try ... finally: conn.close()`.
- [x] **[LOG-09] Purgado automático de PDFs huérfanos**: Al actualizar fecha o régimen fiscal de factura, se elimina el archivo en el directorio previo.
- [x] **[SEC-04] Migración a delegación de eventos en JS**: Eliminados atributos `onclick` con interpolación de strings en tablas de facturas y clientes.
- [x] **[LOG-10] Prevención de colisión en sugerencias de presupuesto**: Consulta a la tabla completa para evitar correlativos duplicados con presupuestos en papelera.
- [x] **[LOG-11] Reactivación automática de códigos de producto**: Alta individual soporta reutilización de referencias dadas de baja en papelera.
- [x] **[DESK-01] Sincronización del almacenamiento en Desktop**: PySide6 descarga y gestiona PDFs respetando la ruta personalizada configurada.
- [x] **[PERF-02] Optimización de consultas en descuentos**: Carga en lote de productos vinculados eliminando problemas N+1.
- [x] **[ARQ-06] Textos comerciales universales y neutros**: Generalización total eliminando terminología residual de invitaciones de boda.
- [x] **[ARQ-07] Portada editorial opcional**: Alternancia entre facturas oficiales de 1 sola página y formato dossier multipágina.
- [x] **[ARQ-08] Rendimiento de arranque en Desktop**: Eliminación de llamadas duplicadas a `init_db()`.
- [x] **[ARQ-09] Limpieza de sentencias DDL redundantes en `app/database.py`**.

### 1. Interfaz y Experiencia de Usuario (macOS HIG)
- [x] **Ajuste de generación de PDF a factura legal oficial**: Formato administrativo limpio de 1 sola página, tabulaciones milimétricas, tipografía TrueType (Inter/Georgia) y redondeo bancario Decimal.
- [x] **Paginación automática y cálculo dinámico de alturas**: Control de desbordamiento de partidas en facturas y presupuestos editoriales.
- [x] **Organización de navegación lateral**: Tabs movidos a la barra lateral izquierda bajo las secciones *Gestión* (Facturas, Presupuestos) y *Directorio* (Clientes, Catálogo), eliminando la barra superior redundante.
- [x] **Botones de acción rápida**: Incorporación de `+ Nuevo presupuesto` junto a `+ Nueva factura` en la barra superior.
- [x] **Sincronización de contadores**: Endpoint `/api/contadores` para mantener contadores de barra lateral activos incluso al navegar entre pestañas.
- [x] **Barra de estado condicional**: Status bar de Facturas (`NSStatusBar`) optimizada con balance y contadores en tiempo real.
- [x] **Ajuste visual de selección y hover**: Resaltado sutil en filas de tablas (`NSTableView`) que preserva la legibilidad del texto en cualquier resolución.
- [x] **Diálogos de confirmación nativos (NSAlert)**: Alertas modales para vaciar papelera, restaurar versiones y eliminaciones destructivas.
- [x] **Paginación integral (MacPagination)**: Componente nativo de barra de estado con selector de tamaño (25/50/100 por pág.) y navegación fluida en Facturas, Presupuestos, Clientes y Catálogo.

### 2. Catálogo de Productos y Servicios
- [x] **Campos independientes Nombre y Descripción**: Eliminación de códigos/SKU artificiales innecesarios, orientando la búsqueda a la denominación comercial y técnica.
- [x] **Escalados de precio por volumen**: Soporte de tramos de cantidad en base de datos, frontend y cálculo reactivo en emisión de documentos.
- [x] **Variantes y atributos (Colores, Acabados, Tamaños)**: Selector visual de color hexadecimal (`color_hex`), recargos o tarifas fijas por variante.
- [x] **Sincronización reactiva en presupuestos**: Limpieza automática y actualización de especificaciones técnicas al alternar productos de catálogo en partidas presupuestarias.
- [x] **Desacoplamiento de `detalle_material` en facturas**: Eliminación definitiva de paréntesis artificiales `(detalle)` al editar partidas y renderizado limpio en PDF.

### 3. Presupuestos y Conversión a Factura
- [x] **Filtrado de opción aprobada**: En presupuestos con múltiples opciones, la factura convertida solo incluye las partidas de la opción elegida por el cliente.
- [x] **Textos y condiciones configurables**: Eliminación de textos estáticos forzados (bodas/papelería); todos los términos son personalizables desde `/configuracion`.
- [x] **Flujo de estados y acciones rápidas**: Menú de acciones en presupuestos (*Aceptar propuesta*, *Facturar*, *Borrador*, *Enviado*, *Rechazado*, *Mover a papelera*).
- [x] **Corrección de errores de validación**: Exposición global de `ApiError`, gestión estándar con `apiFetch` y validadores Pydantic con valores por defecto.

### 4. Facturación, Series y Persistencia Fiscal
- [x] **Numeración y series independientes para facturas con IVA y sin IVA**: Series diferenciadas (`serie_defecto` como "Factura Nº" y `serie_sin_iva` como "Factura Sin IVA Nº") con números de inicio y secuencias correlativas completamente independientes configurables desde `/configuracion`.
- [x] **Separación física de archivos PDF con y sin IVA**: Subcarpetas `Con_IVA` y `Sin_IVA` dentro de la jerarquía mensual (`~/Facturas/PDFs/{AÑO}/{TRIMESTRE}/{MES}/{Con_IVA|Sin_IVA}/`) con migración automática y sincronización reactiva al editar facturas.
- [x] **Configuración de serie por defecto y número de inicio correlativo**: Serie predeterminada ("Factura Nº") y correlativo inicial configurables desde `/configuracion`.
- [x] **Ciclo de vida y purga física de PDFs al eliminar/destruir facturas**: Limpieza inmediata de PDFs huérfanos al borrar o vaciar papelera y regeneración al restaurar.
- [x] **Numeración de series oficial**: Formato configurable con prevención estricta de duplicados.
- [x] **Limpieza de modalidades obsoletas**: Eliminación de 'Modalidad de Emisión' redundante en la conversión de presupuestos.
- [x] **Prevención de duplicidad de clientes**: Bloqueo de concurrencia e in-flight checks al registrar clientes rápidamente desde modales.
- [x] **Edición completa de facturas**: Ruta dedicada `/facturas/{id}/editar`, endpoint `PUT /api/facturas/{id}`, precarga integral y botón directo en inspector lateral.
- [x] **Protección contra doble envío**: Bloqueo in-flight en botón de emisión y descarga PDF oficial.

### 5. Seguridad, Versiones y Disaster Recovery
- [x] **Historial inmutable de versiones (Time Machine)**: Snapshots v1, v2, v3 en facturas y presupuestos con reversión completa sin pérdida de trazabilidad.
- [x] **Módulo de Papelera de Reciclaje**: Eliminación lógica (`is_deleted = 1`), listado independiente, restauración a activo y purga definitiva.
- [x] **Copias de seguridad automáticas y manuales**: Snapshots SQLite mediante Online Backup API y CLI interactivo `scripts/restore_backup.py`.

### 6. Pruebas y Documentación
- [x] **Colección Bruno sincronizada**: Colecciones 01 a 08 actualizadas y validadas con entornos locales.
- [x] **Documentación oficial y Plan de Pruebas**: Matriz de casos de prueba unitarios, de integración y edge cases en `docs/PLAN_DE_PRUEBAS.md`.
- [x] **Suite de pruebas automatizadas**: 53 tests en `pytest` cubriendo cálculos, modelos, API, papelera, versiones y paginación.

---

## 🛠️ Guía Rápida de Compilación de Instaladores

### En Windows:
```powershell
.\build_windows.ps1
# o bien:
.\scripts\build_windows.ps1
```
> Genera `dist\SIF_PyME\SIF_PyME.exe` y, si Inno Setup está disponible, `dist\SIF_PyME_v1.0.0_Windows_Setup.exe`.

### En macOS:
```bash
chmod +x build_macos.sh && ./build_macos.sh
# o bien:
./scripts/build_macos.sh
```
> Genera `dist/SIF PyME.app`, la imagen de disco `dist/SIF_PyME.dmg` y el paquete `dist/SIF_PyME_v1.0.0_Installer.pkg`.

- [x] **Si se pone un precio negativo se calcula el IVA incorrectamente**: Corregido en backend y frontend con acumulación proporcional de base y cuota impositiva.
- [x] **Justificar con la última línea a la izquierda**: Párrafos de observaciones y condiciones de la factura configurados con `align='J'`.
- [x] **Quitar línea de debajo del total**: Supresión de la línea divisoria inferior tras el total.
- [x] **La palabra total debe estar en el mismo tipo de letra, pero en negrita**: Etiqueta 'TOTAL FACTURA' unificada a `sans_font` en negrita ('B').
- [x] **Quitar resaltado de los encabezados de las tablas**: Estilo sutil y limpio sin fondo oscuro en CSS y tipografía secundaria en PDF.
- [x] **Líneas más gordas a 0.75 puntos**: Líneas de tabla estandarizadas a 0.75 pt (0.265 mm).
- [x] **Presupuesto aceptado (sin facturar) editable con regeneración de PDF y opciones**: Desbloqueada la edición directa cuando `factura_id` es nulo, re-enlazado de opciones y regeneración íntegra de opciones en PDF.
- [x] **Estructura intuitiva de carpetas mensuales de facturas (`01_Enero`, `02_Febrero`...)**: Nombrado cronológico y legible de carpetas con retrocompatibilidad y migración automática.
- [x] **Soporte completo para facturas sin IVA y selector exclusivo macOS**: Selector segmentado nativo `[ Todas | Con IVA | Sin IVA ]` en la barra de filtros de facturas (desacoplado del selector de Estado), corrección y unificación del control de IVA en el modal de aceptación de presupuesto (con conversión directa sin modales redundantes ni pérdida de parámetros fiscales), segmented control nativo en la creación/edición de facturas y soporte de filtrado independiente en backend (`/api/facturas?sin_iva=true/false`).
- [x] **Carpetas por trimestres (`1T`, `2T`, `3T`, `4T`)**: Subestructura jerárquica `[AÑO] / [TRIMESTRE] / [MES]` con migración automática.
- [x] **Autocompletado de productos en facturas unificado con presupuestos**: Eliminado recorte por `overflow-x: auto` en contenedor de líneas, asegurado `overflow: visible`, z-index 1050, ancho mínimo optimizado (360px), cierre con tecla Escape y placeholder unificado con presupuestos.
- [x] **Nueva sección: Descuentos y promociones con vinculación a productos y visibilidad configurable**:
  - Sección completa `/descuentos` con tabla macOS NSTableView, búsqueda, selector de estado y modal de alta/edición.
  - Soporte para descuentos globales (a todos los productos) o vinculados a productos específicos seleccionables (`descuento_productos`).
  - Aplicación flexible en Facturas y Presupuestos (por opción) con selector de descuento y control segmentado de visibilidad (`[ 👁️ Visible | 🔒 Oculto (Neto) ]`).
  - Modo Oculto: autocalcula los precios unitarios rebajados únicamente en las líneas de productos vinculados, preservando el precio original y ocultando desgloses y cualquier mención de "Descuento" en el PDF final.
  - Modo Visible: muestra el descuento reflejado en cabecera y el desglose de importe descontado en el resumen de totales.
  - Conversión automática de presupuestos a facturas preservando el descuento, visibilidad y precios calculados.

- [x] **Si borro una factura esta se queda guardada en pdf en archivos**: Sincronización física de archivos PDF al eliminar, restaurar o destruir facturas y vaciar papelera con limpieza recursiva de carpetas vacías en disco.
- [x] **Generar una versión genérica**: Neutralización completa y desacoplamiento de todas las reglas de negocio, textos y valores predeterminados de martamisasdesign (bodas, invitaciones, papelería personalizada, emails y redes sociales específicas) convirtiendo la aplicación en un software de facturación y presupuestos comercial universal para cualquier empresa, pyme o autónomo.
- [x] **Cambiar numeración de las facturas, y en configuración añadir un campo para poder poner el número del comienzo**: Formato configurable de serie y número correlativo de inicio. Nuevos nombres con formato estándar 'Factura Nº [numero]', campo de número de inicio en Configuración (`numero_inicio_factura`) y cálculo automático de correlativos sin duplicidades.