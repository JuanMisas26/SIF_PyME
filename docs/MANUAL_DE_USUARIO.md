# 📖 SIF PyME — Manual Oficial de Usuario y Guía Operativa

> **Versión del Sistema:** 1.0.0 Oficial (Actualización Octubre 2026)  
> **Plataformas Soportadas:** macOS (Apple Silicon & Intel), Windows 10/11 y Linux  
> **Arquitectura:** 100% Local, Privada e Independiente (SQLite WAL + FastAPI + PySide6 / WebEngine)  
> **Marco Legal:** Conforme al Reglamento de Facturación (Real Decreto 1619/2012)

---

## 📑 Tabla de Contenidos

1. [Filosofía del Sistema y Arquitectura Soberana](#1-filosofía-del-sistema-y-arquitectura-soberana)
2. [Puesta en Marcha y Asistente de Configuración (Onboarding)](#2-puesta-en-marcha-y-asistente-de-configuración-onboarding)
3. [Módulo de Facturación (I): Navegación, Filtros e Inspector](#3-módulo-de-facturación-i-navegación-filtros-e-inspector)
4. [Módulo de Facturación (II): Emisión, Régimen Fiscal y Portada Opcional](#4-módulo-de-facturación-ii-emisión-régimen-fiscal-y-portada-opcional)
5. [Módulo de Presupuestos: Opciones Comparables y Conversión 1-Clic](#5-módulo-de-presupuestos-opciones-comparables-y-conversión-1-clic)
6. [Catálogo de Productos y Servicios: Escalados y Atributos](#6-catálogo-de-productos-y-servicios-escalados-y-atributos)
7. [Módulo de Descuentos Comerciales: Promociones y Visibilidad](#7-módulo-de-descuentos-comerciales-promociones-y-visibilidad)
8. [Directorio de Clientes y Validación Fiscal Oficial](#8-directorio-de-clientes-y-validación-fiscal-oficial)
9. [Seguridad y Auditoría: Historial Time Machine y Papelera Lógica](#9-seguridad-y-auditoría-historial-time-machine-y-papelera-lógica)
10. [Ajustes del Sistema, Series Diferenciadas y Copias de Seguridad](#10-ajustes-del-sistema-series-diferenciadas-y-copias-de-seguridad)
11. [Atajos de Teclado, Paginación y Productividad](#11-atajos-de-teclado-paginación-y-productividad)
12. [Preguntas Frecuentes (FAQ) y Especificaciones Técnicas](#12-preguntas-frecuentes-faq-y-especificaciones-técnicas)

---

## 1. Filosofía del Sistema y Arquitectura Soberana

**SIF PyME** es una solución de facturación, gestión presupuestaria y control comercial concebida bajo el principio de **soberanía total sobre los datos**:

- **🔒 Cero Nube Forzosa / 100% Local:** Tus datos contables, registros de clientes y propuestas residen únicamente en tu disco duro en una base de datos relacional SQLite con modo WAL (*Write-Ahead Logging*). No hay telemetría, ni cuotas mensuales, ni riesgo de filtración en servidores externos.
- **🖥️ Estándar macOS Human Interface Guidelines (HIG):** Interfaz unificada con barra de herramientas superior (*Toolbar*), navegación lateral categorizada, tabla de datos interactiva (*NSTableView*) e inspector lateral de detalle (*NSInspector*).
- **📂 Organización Física Predecible:** Los documentos PDF oficiales se almacenan y clasifican automáticamente en una estructura jerárquica unificada por Año, Trimestre y Mes de emisión (sin dispersión de carpetas por régimen de IVA).

```
📁 Directorio Base de Almacenamiento (Configurable)
└── 📁 PDFs/
    └── 📁 2026/
        └── 📁 4T/
            └── 📁 10_Octubre/ --> FAC-2026-10-29-001.pdf
```

---

## 2. Puesta en Marcha y Asistente de Configuración (Onboarding)

Al iniciar SIF PyME por primera vez, el sistema despliega el **Asistente de Bienvenida y Configuración Inicial (Onboarding)** en una hoja modal nativa (*Sheet*):

1. **Datos de la Empresa / Autónomo:**
   - **Nombre o Razón Social:** Nombre fiscal oficial que figurará en el encabezado.
   - **NIF / CIF:** Identificador tributario (validado automáticamente mediante checksum oficial).
   - **Dirección, Código Postal y Población:** Domicilio fiscal para el bloque emisor.
   - **Email, Teléfono y Web:** Datos de contacto profesional.
   - **IBAN Bancario:** Cuenta bancaria con comprobación del algoritmo de control Módulo 97 (ISO 7064).
2. **Ubicación del Almacenamiento de Documentos:**
   - El sistema detecta y sugiere las mejores rutas locales:
     - *Carpeta Local Estándar:* `~/Facturas/` o `~/Documents/Facturas/`
     - *iCloud Drive:* `~/Library/Mobile Documents/com~apple~CloudDocs/Facturas/` (ideal para consultar facturas desde iPhone/iPad sin exponer la base de datos).
     - *OneDrive / Dropbox / Carpeta Externa:* Selector de directorio libre.
3. **Acceso Directo de Escritorio:**
   - Opción para generar el acceso directo nativo en el Escritorio con un solo clic.

> [!TIP]
> Si deseas modificar la carpeta de almacenamiento en cualquier momento posterior, puedes acceder a **Ajustes de Empresa** (`/configuracion`) y seleccionar una nueva ruta. La aplicación mantendrá los históricos intactos y aplicará la nueva ruta a futuras emisiones.

---

## 3. Módulo de Facturación (I): Navegación, Filtros e Inspector

La pantalla principal de **Facturación** (`/`) ofrece una panorámica integral del ejercicio contable:

### 3.1. Barra de Herramientas y Filtros Temporales
- **Filtro de Estado:** Segmenta las facturas en *Todas*, *Emitida* (pendiente de cobro), *Pagada* (ingreso confirmado), *Vencida*, *Borrador* o *Anulada*.
- **Selector de Ejercicio y Periodo:** Selector de año (ej. `2026`) y periodos fiscales:
  - *Año Completo*
  - *Trimestres Fiscales:* `1T` (Ene-Mar), `2T` (Abr-Jun), `3T` (Jul-Sep), `4T` (Oct-Dic) para el **Modelo 303**.
  - *Meses Individuales:* De Enero a Diciembre.
- **Filtro de Régimen IVA:** Alterna entre *Todas*, *Con IVA* o *Sin IVA / Exentas*.
- **Buscador Reactivo en Tiempo Real:** Filtra al vuelo por número de factura (`FAC-...`), razón social del cliente, NIF/CIF o conceptos incluidos.

### 3.2. Panel Inspector Lateral (*NSInspector*)
Al hacer clic sobre cualquier fila del listado, el panel lateral derecho muestra:
- Razón social y NIF del cliente.
- Desglose exacto: **Base Imponible**, **Cuota de IVA**, **Retención de IRPF** y **Total a Pagar**.
- Estado actual con selector directo para marcar como **Pagada**, **Emitida** o **Anulada**.
- Accesos rápidos a:
  - 👁️ **Ver PDF:** Abre el PDF oficial en el visor nativo o navegador.
  - ✏️ **Editar Factura:** Permite modificar líneas o datos (generando una nueva versión histórica).
  - 🕒 **Historial de Versiones:** Abre el registro inmutable de auditoría *Time Machine*.
  - 🗑️ **Eliminar:** Envía el documento a la papelera lógica de reciclaje.

---

## 4. Módulo de Facturación (II): Emisión, Régimen Fiscal y Portada Opcional

Para emitir una factura, pulsa el botón principal **«+ Nueva Factura»** (o el atajo `Cmd + N` / `Ctrl + N`):

### 4.1. Flujo Paso a Paso de Emisión
1. **Cliente Destinatario:** Teclea las primeras letras del cliente para autocompletar su razón social, NIF y dirección. Si es un cliente nuevo, pulsa **«Nuevo Cliente…»** para darlo de alta en un modal sin perder la factura en curso.
2. **Fechas:** Establece la fecha legal de emisión y, opcionalmente, la fecha de vencimiento.
3. **Régimen de IVA y Numeración Unificada:**
   - *Régimen General (Con IVA):* Aplica el IVA general (21%), reducido (10%), superreducido (4%) o exento (0%).
   - *Régimen Exento / Sin IVA:* Al marcar la casilla «Factura Exenta de IVA», el IVA se establece al 0% y se incorpora la leyenda legal correspondiente. La numeración mantiene la secuencia unificada `[Prefijo]-[AÑO]-[MES]-[DIA]-[ID]` sin forzar series separadas.
   - *Misma Carpeta Física:* Todas las facturas se guardan en la carpeta unificada mensual de PDFs para una gestión contable más sencilla y sin duplicidades.
4. **Adición de Líneas de Conceptos:**
   - Escribe un concepto libre o selecciona un producto del catálogo mediante el botón **«Catálogo»**.
   - Cada línea cuenta con campos independientes para **Descripción del Producto**, **Detalle / Especificación Técnica** (`detalle_material`), unidades, precio unitario, % IVA y % IRPF.
   - **Tramos por Volumen Automáticos:** Si el producto tiene escalados configurados en el catálogo, el precio unitario se ajustará solo según la cantidad introducida.
5. **Partidas Negativas y Anticipos:**
   - Puedes añadir líneas con importe negativo (ej. *-500,00 €* por un anticipo o entrega a cuenta previa).
   - El sistema deduce proporcionalmente la base imponible y las cuotas de IVA e IRPF de acuerdo a la normativa tributaria.
6. **Partidas al 0% de IVA (Suplidos y Exenciones):**
   - Si incluyes una partida al 0% de IVA dentro de una factura ordinaria gravada al 21%, el sistema preserva el 0% en esa línea sin forzarla al 21%.
7. **Descuento Comercial Aplicado:**
   - Selecciona un descuento global del desplegable para aplicar una bonificación en porcentaje o importe fijo.
8. **Emisión y Guardado Oficial:**
   - Pulsa **«Emitir Factura y Descargar PDF»**. El sistema bloquea el documento, le asigna el correlativo legal consecutivo, genera el PDF oficial y realiza un snapshot de respaldo.

### 4.2. Portada Editorial Opcional
En **Ajustes de Empresa**, puedes activar o desactivar la opción **«Incluir portada editorial en facturas»**:
- **Desactivada (Por Defecto):** Factura administrativa oficial directa de **1 sola página**, ideal para agilidad fiscal y envío a gestorías.
- **Activada:** Dossier comercial completo de 2 o más páginas con portada fotográfica de presentación corporativa, idónea para estudios de arquitectura, publicidad o proyectos de alto valor.

---

## 5. Módulo de Presupuestos: Opciones Comparables y Conversión 1-Clic

SIF PyME incorpora un motor exclusivo para presupuestos y propuestas comerciales multipágina (`/presupuestos`):

### 5.1. Presupuestos con Múltiples Opciones (A/B/C)
En lugar de emitir presupuestos rígidos, puedes presentar varias alternativas en un único documento:
- **Pestaña Opción 1:** Ej. *«Opción A · Acabado Básico»* (1.200 €).
- **Pestaña Opción 2:** Ej. *«Opción B · Acabado Premium con Extras»* (1.850 €).
- **Botón «Duplicar Opción»:** Clona al instante todas las líneas de una opción para ajustar pequeñas variantes sin reescribir.
- **Rango Comercial Automático:** El listado muestra el intervalo presupuestado (`1.200,00 € — 1.850,00 €`) para facilitar el seguimiento comercial.

### 5.2. Aprobación y Facturación Directa en 1 Clic
Cuando el cliente elige una opción:
1. Pulsa **«Facturar…»** en la fila del presupuesto.
2. Selecciona la opción aceptada por el cliente y el tipo de IVA aplicable.
3. El sistema genera de forma automática la factura legal con su serie y correlativo, vincula el presupuesto (estado *Facturado*) y abre la factura emitida.

> [!NOTE]
> **Reapertura y Flexibilidad:** Si tras facturar un presupuesto el cliente decide cambiar a otra opción, la acción **«Reabrir y volver a Borrador»** traslada la factura previa a la papelera lógica y permite facturar la nueva opción sin descuadrar la contabilidad.

---

## 6. Catálogo de Productos y Servicios: Escalados y Atributos

Ubicado en `/productos`, organiza tu oferta comercial mediante búsqueda semántica sin obligarte a memorizar códigos SKU artificiales:

- **Pestaña 1 · Datos Generales:** Nombre comercial, descripción técnica ampliada, precio unitario base, tipo de IVA aplicable (21%, 10%, 4%, 0%) y retención de IRPF.
- **Pestaña 2 · Escalado de Precios por Volumen:**
  - Define tarifas mayoristas o por tramos. Ejemplo:
    - De 1 a 49 uds: `3,50 €`
    - De 50 a 99 uds: `2,90 €`
    - De 100 en adelante (máximo vacío): `2,40 €`
- **Pestaña 3 · Variantes y Colores:**
  - Configura acabados, formatos o colores con muestra visual en paleta hexadecimal y recargos adicionales (+€).
- **Reactivación Automática:** Si diste de baja un producto en el pasado y vuelves a crearlo con el mismo código, el sistema lo reactiva automáticamente preservando su historial.

---

## 7. Módulo de Descuentos Comerciales: Promociones y Visibilidad

Accesible desde la barra lateral en `/descuentos`, permite crear y gestionar políticas comerciales flexibles:

### 7.1. Parámetros del Descuento
- **Nombre:** Identificador comercial (ej. *«Campaña Black Friday 15%»*, *«Descuento Fidelidad 50€»*).
- **Tipo de Descuento:**
  - *Porcentaje (%):* Deducción proporcional sobre la base imponible.
  - *Importe Fijo (€):* Descuento en euros directos.
- **Alcance:**
  - *Todos los productos:* Se aplica globalmente al documento.
  - *Productos específicos:* Selecciona del catálogo qué artículos están sujetos a la promoción.

### 7.2. Visibilidad en Documentos Oficiales
- **Descuento Visible (Desglosado):** En la factura o presupuesto aparece una línea clara de deducción antes de impuestos (ideal para clientes finales que valoran ver el ahorro).
- **Descuento Oculto (Neto en Precio):** El descuento se aplica internamente en el precio unitario efectivo sin mostrarse en el desglose (ideal para tarifas de distribución o acuerdos privados entre empresas).

---

## 8. Directorio de Clientes y Validación Fiscal Oficial

Centralizado en `/clientes`, almacena la información fiscal de tus clientes con blindaje contra errores contables:

- **Validador Algorítmico de NIF, NIE y CIF:**
  - Verifica las letras de control de NIFs de personas físicas, NIEs de residentes extranjeros y dígitos de control CIF de sociedades (S.L., S.A., Cooperativas, etc.). Si se introduce un código erróneo, la aplicación rechaza el guardado para evitar sanciones de la AEAT.
- **Soporte para Clientes Particulares (Sin NIF):**
  - Para ventas a consumidores finales o facturas simplificadas donde no se requiera NIF, basta con registrar el nombre y teléfono/email.
- **Prevención de Duplicados:** La base de datos garantiza la unicidad fiscal: si introduces un NIF existente, te redirige a la ficha activa para evitar dobles registros.
- **Historial Protegido por Snapshot:** Modificar la dirección o razón social de un cliente no altera las facturas emitidas en el pasado, que conservan los datos exactos del momento de expedición.

---

## 9. Seguridad y Auditoría: Historial Time Machine y Papelera Lógica

### 9.1. Auditoría Inmutable *Time Machine*
Cada modificación realizada sobre una factura o presupuesto (edición de importes, adición de líneas, cambios de estado) genera una **versión histórica inmutable**:
- Pulsa **«Historial de Versiones…»** en el inspector lateral para ver la línea temporal completa.
- Puedes inspeccionar cualquier versión previa y pulsar **«Restaurar esta versión»**. El sistema creará una nueva revisión con el contenido restaurado, preservando intacto el historial anterior sin sobreescrituras destructivas.

### 9.2. Papelera de Reciclaje Lógica
En SIF PyME, borrar nunca destruye tus datos por accidente:
- Al eliminar un cliente, factura o presupuesto, el registro pasa a la **Papelera** (`/papelera`).
- **Restauración en 1 Clic:** Recupera documentos borrados con todas sus líneas y PDFs vinculados.
- **Borrado en Cascada Seguro:** Si eliminas un cliente, sus facturas van a la papelera. Si restauras al cliente, recupera su ficha sin reactivar facturas que hubieses enviado a la papelera previamente de forma intencionada.
- **Destrucción Definitiva:** Solo tras pulsar expresamente «Destruir definitivamente» o «Vaciar papelera» se purgan los registros y archivos físicos tras confirmación de seguridad.

---

## 10. Ajustes del Sistema, Series Diferenciadas y Copias de Seguridad

En `/configuracion` se gestionan los parámetros legales del sistema:

### 10.1. Numeración Unificada y Prefijo Configurable
El sistema implementa una numeración estructurada y uniforme para todo el ejercicio:
- **Estructura Oficial:** `[Prefijo]-[AÑO]-[MES]-[DIA]-[ID]` (ej. `FAC-2026-10-29-001`).
- **Prefijo Configurable:** Personalizable desde los ajustes de facturación (por defecto `FAC`).
- **Secuencia Única:** Todas las facturas (con IVA o exentas) comparten la misma secuencia correlativa continua.
- **Número de Inicio Configurable:** Puedes definir el valor numérico inicial con el que arrancar la serie (ej. empezar en `1` o en `1001`).

### 10.2. Motor de Snapshots y Copias de Seguridad
- **Copias Automáticas:** La aplicación realiza un volcado de base de datos (`.db`) con marca de tiempo cada vez que se emite o modifica un documento contable.
- **Copias Manuales en 1 Clic:** Botón **«Crear Copia de Seguridad Ahora»**.
- **Restauración Segura:** Antes de restaurar una copia previa, el sistema genera automáticamente un respaldo de seguridad preventivo con el estado actual para que nunca exista pérdida de datos.

---

## 11. Atajos de Teclado, Paginación y Productividad

SIF PyME permite operar íntegramente sin despegar las manos del teclado:

| Atajo / Control | Pantalla | Acción Ejecutada |
|---|---|---|
| <kbd>Cmd</kbd> / <kbd>Ctrl</kbd> + <kbd>N</kbd> | Global | Abrir formulario para emitir **Nueva Factura** |
| <kbd>Cmd</kbd> / <kbd>Ctrl</kbd> + <kbd>P</kbd> | Global | Abrir formulario para crear **Nuevo Presupuesto** |
| <kbd>Cmd</kbd> / <kbd>Ctrl</kbd> + <kbd>F</kbd> | Listados | Enfocar automáticamente la barra de búsqueda reactiva |
| <kbd>Escape</kbd> | Modales | Cerrar cualquier ventana emergente, modal o inspector lateral |
| <kbd>Enter</kbd> | Diálogos | Confirmar acción principal predeterminada (*Guardar / Aceptar*) |
| <kbd>Tab</kbd> | Formularios | Navegar fluidamente al siguiente campo de entrada |
| **Clic en Fila** | Facturas | Seleccionar factura y desplegar el **Inspector Lateral** |
| **Doble Clic** | Facturas | Abrir la factura en modo de edición completa |

### Paginación Rápida y Totales en Vivo
Al pie de cada tabla dispones de:
- Selector de tamaño de página: **25**, **50** o **100** registros.
- Botones de navegación *Anterior* / *Siguiente*.
- **Barra de Totales en Vivo:** Muestra la suma exacta de Bases Imponibles y Totales facturados correspondientes a los registros visibles filtrados.

---

## 12. Preguntas Frecuentes (FAQ) y Especificaciones Técnicas

### ❓ Preguntas Frecuentes

1. **¿Por qué el botón «Emitir Factura» aparece inactivo?**  
   Ocurre si no se han completado los datos obligatorios del emisor. Accede a **Ajustes de Empresa** y completa la Razón Social y el NIF hasta que el indicador marque *«Configuración completa»*.
2. **¿Puedo cambiar la carpeta donde se guardan los PDFs?**  
   Sí. En **Ajustes de Empresa**, en la sección *Directorio de Almacenamiento de PDFs*, selecciona cualquier carpeta local, unidad compartida o carpeta de nube (iCloud Drive / OneDrive).
3. **¿Cómo modifico una factura emitida con algún dato erróneo?**  
   Haz clic en la factura, pulsa **«Editar Factura»** en el inspector lateral, corrige los importes o conceptos y pulsa guardar. El sistema regenerará el PDF, purgará el documento anterior y dejará constancia en el historial de versiones.
4. **¿Necesito conexión a Internet para usar el programa?**  
   No. El sistema es 100% autónomo y funciona sin conexión de red.
5. **¿Qué ocurre si cambio de ordenador?**  
   Basta con copiar la carpeta `Facturas` o exportar una copia desde Ajustes → *Copias de Seguridad*. Al instalar el programa en tu nuevo equipo y restaurar el respaldo, tendrás todo exactamente igual.

### ⚙️ Especificaciones Técnicas

- **Base de Datos:** SQLite 3.x con modo `WAL` (*Write-Ahead Logging*), claves foráneas y comprobación de integridad.
- **Servidor:** FastAPI ASGI + Uvicorn ejecutándose en bucle local (`127.0.0.1`).
- **Desktop Nativo:** PySide6 (Qt 6.7+) con motor Chromium embebido (`QWebEngineView`).
- **Motor Editorial:** fpdf2 con fuentes TrueType (Inter y Georgia), control dinámico de salto de página y precisión matemática `Decimal` con redondeo comercial bancario (`ROUND_HALF_UP`).
- **Seguridad:** Cero telemetría externa, validación estricta de rutas contra *Path Traversal* y sanitización contra inyección de código.

---

*Manual oficial elaborado y mantenido por el equipo de ingeniería de SIF PyME · Octubre 2026*

