# 📋 Control de Incidencias y Mejoras — Code Review SIF PyME

Documento de seguimiento operativo para la resolución progresiva de los hallazgos detectados durante la revisión de código del sistema **SIF PyME**.

---

## 📊 Resumen de Estado

- **Total incidencias:** 31
- **Pendientes:** 0
- **En progreso:** 0
- **Resueltas:** 31 (100% completado — 16 previas + 15 resueltas en esta fase)

---

## 🔍 Nueva Auditoría de Código (Octubre 2026)

### 🚨 Prioridad 1: Correcciones Urgentes (Integridad Fiscal, Persistencia y Recursos)

- [x] **[LOG-07] Sobrescritura forzosa de IVA al 21% en líneas exentas (0% IVA) al actualizar facturas**
  - **Severidad:** Alta
  - **Categoría:** Lógica de Negocio / Fiscal
  - **Archivos:** [`app/routes/facturas.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/facturas.py#L394-L397) y [`app/routes/facturas.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/facturas.py#L422)
  - **Tareas:**
    - [x] Modificar `actualizar_factura` para evaluar explícitamente `porcentaje_iva is None`, respetando `0.0` en partidas exentas o no gravadas.
    - [x] Asegurar que la inserción SQL de `lineas_factura` mantenga el `0.0` recibido sin sustituirlo por `21.0`.
    - [x] Añadir test unitario de regresión para actualización de facturas con líneas mixtas (0% y 21%).

- [x] **[LOG-08] Eliminación indebida de IVA e IRPF en líneas negativas al convertir presupuesto a factura**
  - **Severidad:** Alta
  - **Categoría:** Lógica de Negocio / Fiscal
  - **Archivos:** [`app/routes/presupuestos.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/presupuestos.py#L811-L820)
  - **Tareas:**
    - [x] Retirar la condición `es_neg` que fuerza `porcentaje_iva = 0.0` y `porcentaje_irpf = 0.0` en partidas negativas.
    - [x] Verificar que `calcular_totales_factura` reciba los porcentajes de IVA e IRPF reales para deducir la cuota proporcionalmente.
    - [x] Añadir prueba automatizada en `tests/test_api_presupuestos.py` convirtiendo un presupuesto con anticipo negativo.

- [x] **[RES-01] Fuga de descriptores de conexión SQLite en `get_pdf_storage_dir()`**
  - **Severidad:** Media / Gestión de Recursos
  - **Archivos:** [`app/paths.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/paths.py#L62-L70)
  - **Tareas:**
    - [x] Sustituir el bloque `with sqlite3.connect(DB_PATH) as conn:` por `try ... finally: conn.close()`.
    - [x] Reutilizar la conexión del hilo actual si está disponible para evitar aperturas redundantes de base de datos.

- [x] **[LOG-15] Robustez en ciclo de vida y edge cases del flujo Presupuestos - Facturas**
  - **Severidad:** Alta
  - **Categoría:** Lógica de Negocio / Integridad Relacional
  - **Archivos:** [`app/routes/presupuestos.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/presupuestos.py), [`app/routes/papelera.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/papelera.py), [`app/routes/facturas.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/facturas.py), [`app/services/version_service.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/services/version_service.py) y [`tests/test_flujo_presupuestos_facturas_edge_cases.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/tests/test_flujo_presupuestos_facturas_edge_cases.py)
  - **Tareas:**
    - [x] Purgar archivo PDF en disco al reabrir un presupuesto facturado a Borrador (`eliminar_pdf_factura`).
    - [x] Sincronizar y preservar `descuento_id` y `precio_unitario_original` al absorber líneas de factura hacia la opción del presupuesto al reabrir a Borrador.
    - [x] Revertir automáticamente los presupuestos vinculados a estado `Aceptado` al vaciar la papelera o destruir definitivamente facturas (evitando presupuestos huérfanos bloqueados en `Facturado` con `factura_id = NULL`).
    - [x] Prorratear correctamente descuentos globales de opción al convertir a factura.
    - [x] Añadir suite de pruebas automatizadas cubriendo los casos límite del flujo.

- [x] **[LOG-14] Actualización de serie y numeración correlativa al editar régimen o restaurar versiones (Con IVA / Sin IVA)**
  - **Severidad:** Alta
  - **Categoría:** Lógica de Negocio / Facturación Normativa
  - **Archivos:** [`app/routes/facturas.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/facturas.py#L437-L488) y [`tests/test_pdf_iva_folders.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/tests/test_pdf_iva_folders.py)
  - **Tareas:**
    - [x] Detectar cambio de régimen en `actualizar_factura` (`antiguo_sin_iva != nuevo_sin_iva`).
    - [x] Si cambia de Con IVA a Sin IVA (o viceversa), reasignar automáticamente la serie correspondiente (`serie_sin_iva` vs `serie_defecto`) y el siguiente correlativo independiente mediante `generar_numero_factura(...)`.
    - [x] Actualizar `numero_factura`, `serie` y `correlativo` en base de datos.
    - [x] Purgar el PDF anterior en su carpeta de origen (`Con_IVA` o `Sin_IVA`) y generar el nuevo PDF en el directorio destino con la nueva numeración.
    - [x] Registrar la versión con detalle del cambio de régimen y serie.
    - [x] Sincronizar la restauración de versiones en `app/services/version_service.py` (`restaurar_version_factura`) para que al volver a una versión con distinto régimen se recupere la serie/número original o se reasigne la serie correspondiente y se reubique físicamente el PDF eliminando el anterior.
    - [x] Añadir pruebas automatizadas de migración bidireccional (`Con IVA` <-> `Sin IVA`) comprobando reasignación de número y coherencia de carpetas.

- [x] **[LOG-09] Generación de PDFs huérfanos al modificar fecha de emisión o régimen fiscal de factura**
  - **Severidad:** Media / Integridad del Sistema de Archivos
  - **Archivos:** [`app/routes/facturas.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/facturas.py#L492-L494) y [`app/services/pdf_service.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/services/pdf_service.py#L207-L244)
  - **Tareas:**
    - [x] En `actualizar_factura`, comparar `fecha_emision` y `sin_iva` con los valores de `factura_existente`.
    - [x] Si cambiaron, invocar `eliminar_pdf_factura(factura_existente['numero_factura'], factura_existente['fecha_emision'], factura_existente['sin_iva'])` antes de crear el nuevo PDF.
    - [x] Añadir test verificando la purga física del PDF en el directorio del mes previo al cambiar de fecha.

---

### ⚡ Prioridad 2: Mejoras Importantes (Robustez, Seguridad y Usabilidad)

- [x] **[SEC-04] Migración de atributos `onclick` con cadenas interpoladas a delegación de eventos**
  - **Severidad:** Media
  - **Categoría:** Seguridad / Robustez de Frontend
  - **Archivos:** [`app/static/js/app.js`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/static/js/app.js#L1469-L1470) y [`app/static/js/app.js`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/static/js/app.js#L2000)
  - **Tareas:**
    - [x] Eliminar `onclick="openEstadoModal(...)"` y `onclick="eliminarFactura(...)"` con interpolación de strings.
    - [x] Usar atributos semánticos `data-action`, `data-id`, `data-numero` y `data-estado`.
    - [x] Capturar eventos mediante delegación en el `tbody` correspondiente para evitar fallos con apóstrofes o caracteres especiales.

- [x] **[LOG-10] Prevención de colisión en `sugerir_numero_presupuesto` con registros en papelera**
  - **Severidad:** Media
  - **Categoría:** Lógica de Negocio / Persistencia
  - **Archivos:** [`app/routes/presupuestos.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/presupuestos.py#L55-L68)
  - **Tareas:**
    - [x] Comprobar existencia del código en la tabla completa sin filtrar por `is_deleted = 0`.
    - [x] Asegurar que el correlativo sugerido nunca coincida con un presupuesto existente en papelera.

- [x] **[LOG-11] Soporte para reactivar o reutilizar códigos de producto en alta individual**
  - **Severidad:** Media
  - **Categoría:** Lógica de Negocio / Catálogo
  - **Archivos:** [`app/routes/productos.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/productos.py#L230-L254)
  - **Tareas:**
    - [x] Añadir `ON CONFLICT(codigo) DO UPDATE SET is_deleted=0 ...` en la inserción individual de `crear_producto`.
    - [x] Sincronizar el comportamiento entre el alta masiva y el formulario individual.

- [x] **[DESK-01] Sincronización del directorio de almacenamiento configurado en descargas Desktop**
  - **Severidad:** Baja
  - **Categoría:** Desktop / PySide6 / Integración
  - **Archivos:** [`desktop.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/desktop.py#L293)
  - **Tareas:**
    - [x] Sustituir `directorio_destino = str(PDF_BASE_DIR)` por `directorio_destino = str(get_pdf_storage_dir())`.
    - [x] Verificar que las descargas de PDFs respeten carpetas configuradas (iCloud, OneDrive, ruta externa).

---

### 🛠️ Prioridad 3: Mejoras Recomendables (Rendimiento, Arquitectura y Limpieza)

- [x] **[PERF-02] Optimización de consultas N+1 en listado de descuentos**
  - **Severidad:** Baja
  - **Categoría:** Rendimiento
  - **Archivos:** [`app/routes/descuentos.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/descuentos.py#L96-L98)
  - **Tareas:**
    - [x] Cargar productos vinculados a descuentos en lote mediante `WHERE descuento_id IN (...)`.
    - [x] Reducir la consulta de $1+N$ a 2 consultas SQL totales.

- [x] **[ARQ-06] Neutralización de textos residuales de invitaciones de boda en modelos y servicios**
  - **Severidad:** Baja
  - **Categoría:** Calidad de Código / Generalización
  - **Archivos:** [`app/models.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/models.py#L555), [`app/routes/configuracion.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/routes/configuracion.py#L93) y [`app/services/presupuesto_pdf_service.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/services/presupuesto_pdf_service.py#L20-L28)
  - **Tareas:**
    - [x] Reemplazar "Precios para el diseño de invitaciones de boda" por textos comerciales neutros.
    - [x] Sustituir "Estilo de invitación" y "Tiempos de producción de vuestras invitaciones" por términos profesionales estándar.

- [x] **[ARQ-07] Portada editorial opcional en facturas oficiales en PDF**
  - **Severidad:** Baja
  - **Categoría:** Usabilidad / Formato Fiscal
  - **Archivos:** [`app/services/pdf_service.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/services/pdf_service.py#L424-L448) y [`app/models.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/models.py#L462)
  - **Tareas:**
    - [x] Desactivar por defecto la portada fotográfica en PDFs de facturas comerciales para emitir documentos de 1 sola página.
    - [x] Permitir activar la portada mediante configuración (`factura_incluir_portada`) si el usuario la requiere expresamente.

- [x] **[ARQ-08] Supresión de inicialización redundante de base de datos en `desktop.py`**
  - **Severidad:** Baja
  - **Categoría:** Rendimiento de Arranque
  - **Archivos:** [`desktop.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/desktop.py#L410)
  - **Tareas:**
    - [x] Retirar la llamada duplicada a `init_db()` en `desktop.py`, delegando exclusivamente en el `lifespan` de FastAPI.

---

### 💡 Prioridad 4: Mejoras Opcionales

- [x] **[ARQ-09] Limpieza de sentencias duplicadas en el script fallback de `init_db()`**
  - **Severidad:** Baja
  - **Categoría:** Mantenibilidad
  - **Archivos:** [`app/database.py`](file:///c:/Users/72359576/Documents/Personales/Proyectos/Otros/factura/app/database.py#L242-L264)
  - **Tareas:**
    - [x] Eliminar la segunda declaración idéntica de las tablas `descuentos` y `descuento_productos`.

---

## 🏛️ Histórico de Incidencias Resueltas (Auditoría Inicial)

<details>
<summary>Ver 16 incidencias resueltas en fases anteriores</summary>

### Fase 1: Correcciones Urgentes
- [x] **[SEC-01] Sanitización de rutas y prevención de Path Traversal en restauración de backups**
- [x] **[LOG-01] Sincronización completa de datos en restauración de versiones históricas (Time Machine)**
- [x] **[SEC-02] Sanitización y mitigación de XSS en tablas dinámicas de frontend**
- [x] **[LOG-02] Validación obligatoria de datos fiscales al convertir presupuesto a factura**
- [x] **[LOG-03] Eliminación de mutaciones arbitrarias (`UPDATE`) en el ciclo de vida de arranque**

### Fase 2: Mejoras Importantes
- [x] **[LOG-04] Corrección de obtención de ID en inserción masiva de productos (`ON CONFLICT`)**
- [x] **[LOG-05] Prevención de des-eliminación masiva no intencionada en `restaurar_cliente`**
- [x] **[SEC-03] Desacoplamiento de cadenas de texto en atributos de eventos inline (`onclick`)**
- [x] **[ARQ-01] Sincronización canónica del script `schema.sql` con el estado real de la BD**
- [x] **[LOG-06] Sincronización del ciclo de vida de archivos PDF al eliminar, restaurar o destruir facturas**

### Fase 3: Mejoras Recomendables
- [x] **[ARQ-02] Modularización y separación de responsabilidades en `facturas.py`**
- [x] **[ARQ-03] Estandarización de registro y prefijos de routers en `main.py`**
- [x] **[ARQ-04] Unificación del gestor transaccional `db_connection()` en `presupuestos.py`**
- [x] **[PERF-01] Optimización de consultas N+1 en listado de productos y detalles de presupuesto**

### Fase 4: Mejoras Opcionales y Suite de Pruebas
- [x] **[ARQ-05] Neutralización de textos por defecto y branding de marca en servicios de PDF**
- [x] **[TEST-01] Ampliación de la suite de pruebas unitarias y de integración**

</details>

</details>

