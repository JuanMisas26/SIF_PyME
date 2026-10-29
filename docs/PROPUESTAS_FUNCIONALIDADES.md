# 💡 Propuestas de Nuevas Funcionalidades y Mejoras Futuras — SIF PyME

**Documento de Especificación y Análisis Funcional**  
*Fecha de creación: 22 de octubre de 2026*  
*Estado: Propuestas Aprobadas para Roadmap*

---

## 📌 Resumen Ejecutivo

El presente documento recoge y profundiza el análisis de nuevas capacidades comerciales, financieras, analíticas y de experiencia de usuario para **SIF PyME**. Su objetivo es evolucionar el software desde una solución de facturación y presupuestos sólida hacia una plataforma integral de gestión comercial de alto rendimiento para pequeñas empresas, estudios creativos y profesionales autónomos, preservando en todo momento el diseño nativo inspirado en **macOS Human Interface Guidelines (HIG)** y la velocidad local.

---

## 1. Finanzas Comerciales y Facturación

### 1.1. Gastos de Envío y Transporte (Portes)
* **Objetivo**: Permitir a empresas que comercializan productos físicos (diseño impreso, papelería, artesanía, packaging, textil) imputar el coste logístico de forma clara y fiscalmente precisa.
* **Comportamiento y Experiencia de Usuario**:
  - En la sección inferior del formulario de emisión de facturas y presupuestos (junto al balance de totales), se añade un switch/checkbox nativo: `[✓] Incluir gastos de envío`.
  - Al activarse, se despliegan dos opciones configurables:
    - **Tarifa fija / Tipo de servicio**: Selector rápido (*Envío Estándar 5,90 €*, *Mensajería Urgente 24h 9,90 €*, *Recogida en taller 0,00 €* o *Importe personalizado*).
    - **Regla de Portes Gratuitos**: Posibilidad de configurar en `/configuracion` un umbral de envío gratis (ej. *"Gratis a partir de 100,00 €"*), de forma que el sistema marque automáticamente el envío a 0,00 € indicando el beneficio al cliente.
* **Tratamiento Fiscal y Contable**:
  - Los gastos de envío se integran en la Base Imponible general con su tipo impositivo correspondiente (21% IVA en España).
  - En el documento PDF impreso, se desglosa como una partida final diferenciada o línea de concepto especial con su propia columna de impuestos.

---

### 1.2. Descuentos Comerciales Globales y por Pronto Pago — ✅ IMPLEMENTADA (v1.0.0)
* **Estado:** **Completada e Integrada en v1.0.0 (Octubre 2026)**
* **Objetivo**: Aplicar descuentos al conjunto del pedido o por productos específicos sin necesidad de alterar individualmente los precios unitarios de cada línea.
* **Implementación Realizada**:
  - Módulo completo `/descuentos` con tabla de gestión y modal de creación/edición.
  - Soporte de descuentos en **Porcentaje (`%`)** e **Importe Fijo (`€`)**.
  - **Alcance Configurable**: Aplicable a todos los productos (`todos`) o vinculado a referencias seleccionadas del catálogo (`descuento_productos`).
  - **Control de Visibilidad**: Modalidad *Visible* (desglosado en cabecera y totales de factura/presupuesto) y modalidad *Oculta* (ajuste interno al precio unitario neto sin mención de descuento en el documento impreso).
  - Integración fluida en presupuestos con opciones y conversión automática preservando importes y visibilidad.

---

### 1.3. Facturas Rectificativas y Abonos (Devoluciones)
* **Objetivo**: Cumplir con la estricta normativa contable europea y española (Real Decreto 1619/2012) para correcciones de importes, errores materiales o devoluciones de mercancía sin alterar ni eliminar la serie de facturación original.
* **Comportamiento y Experiencia de Usuario**:
  - En el inspector de una factura ya emitida/pagada, se añade el botón de acción: `Crear Factura Rectificativa / Abono`.
  - El sistema crea un nuevo documento vinculado a la factura origen bajo una serie independiente obligatoria: `REC-[AÑO]-[MES]-[Identificador]` (ej. `REC-2026-10-001`).
  - Permite rectificación parcial (abono de partidas específicas) o total.
  - Genera su propio PDF oficial indicando: *"Factura Rectificativa en sustitución de la factura FAC-XXXX con fecha DD/MM/AAAA"*.

---

### 1.4. Gestión de Pagos Parciales, Anticipos y Señales (Fraccionamiento)
* **Objetivo**: Gestionar con fluidez los cobros escalonados habituales en trabajos por encargo (ej. 50% de señal previa y 50% a la entrega del proyecto).
* **Comportamiento y Experiencia de Usuario**:
  - Pestaña o bloque en el inspector de factura: *Registro de Cobros*.
  - Botón: `+ Añadir Pago Parcial` (Fecha, Importe cobrado, Medio de pago: *Transferencia*, *Bizum*, *TPV*, *Efectivo*).
  - **Indicador Visual de Cobro**:
    - Barra de progreso estilo macOS: `Cobrado: 450,00 € (50%) • Pendiente: 450,00 €`.
    - Estados automáticos de cobro: *Pendiente* (0%), *Cobro Parcial* (>0% y <100%), *Totalmente Pagada* (100%).

---

## 2. Presupuestos Editoriales y Ventas (CRM Ligero)

### 2.1. Plantillas de Presupuestos (Templates Reutilizables)
* **Objetivo**: Reducir drásticamente el tiempo de elaboración de presupuestos recurrentes.
* **Comportamiento**:
  - En cualquier presupuesto terminado con estructura compleja (fases, textos de bienvenida, condiciones comerciales y catálogo de opciones), botón: `Guardar como Plantilla…`.
  - Al crear un nuevo presupuesto, un selector en la cabecera permite: `Cargar desde Plantilla: [Pack Branding Corporativo / Papelería Completa Evento / Consultoría]`.
  - Se precargan al instante todas las partidas, descripciones y condiciones, dejando al usuario únicamente la tarea de asignar el cliente.

---

### 2.2. Envío Directo por Correo Electrónico (`mailto:` y SMTP Integrado)
* **Objetivo**: Agilizar la comunicación con el cliente sin necesidad de abrir manualmente el cliente de correo, buscar el PDF descargado y redactar el email.
* **Comportamiento**:
  - Botón nativo en toolbar e inspector: `Enviar por Correo…`.
  - **Modo 1 (Cero configuración - Protocolo del Sistema)**: Invoca el cliente predeterminado del sistema operativo (Apple Mail en macOS, Outlook/Thunderbird en Windows) con destinatario (`cliente@email.com`), asunto preformateado y cuerpo comercial personalizado.
  - **Modo 2 (Envío Directo SMTP)**: Configuración en `/configuracion` de credenciales SMTP corporativas (Google Workspace, Microsoft 365, servidor propio) para envío desatendido con PDF oficial adjunto en 1 clic.

---

### 2.3. Control de Plazos y Alertas de Vencimiento de Presupuestos
* **Objetivo**: Impulsar la tasa de conversión comercial recordando las propuestas pendientes de decisión.
* **Comportamiento**:
  - Al emitir un presupuesto, se define el campo `fecha_validez` (ej. 15, 30 o 60 días).
  - En la tabla de presupuestos y en la barra lateral:
    - Badges semánticos dinámicos: `Vence en 4 días` (naranja), `Vencido` (rojo).
    - Filtro rápido en sub-barra: *Propuestas por vencer*.

---

## 3. Informes, Inteligencia de Negocio y Gestoría

### 3.1. Exportador Trimestral para Gestoría (Modelos 303 / 130 / 347)
* **Objetivo**: Automatizar la tediosa preparación del cierre fiscal trimestral y anual.
* **Comportamiento**:
  - En la vista de Facturas, botón: `Exportar Trimestre (T1 / T2 / T3 / T4)`.
  - Generación de un archivo en formato **Excel (`.xlsx`) y CSV normalizado** con la estructura exacta exigida por despachos contables y programas de asesoría:
    - *Fecha de Emisión*, *Número de Serie Oficial*, *Razón Social Cliente*, *NIF/CIF*, *Base Imponible*, *% IVA*, *Cuota IVA Repercutido*, *% Retención IRPF*, *Importe Retención*, *Total Facturado*, *Estado de Pago*.
  - **Alerta Anual Modelo 347**: Detección automática y listado de clientes cuyo volumen anual de facturación acumulada supere los **3.005,06 €**.

---

### 3.2. Panel de Control y Analítica Visual (Dashboard)
* **Objetivo**: Brindar a la dirección de la pyme una visión clara e intuitiva de la salud financiera del negocio.
* **Comportamiento**:
  - Nueva pestaña en navegación lateral: `Informes` o `Dashboard`.
  - Widgets interactivos estilo macOS Big Sur+:
    - **Evolución Temporal**: Gráfico de facturación mensual y comparativa con el año anterior.
    - **Tasa de Conversión**: Porcentaje de presupuestos aprobados vs. rechazados o caducados.
    - **Top 5 Clientes**: Clientes más rentables del ejercicio.
    - **Previsión de Tesorería**: Facturas pendientes de cobro y vencidas.

---

## 4. Experiencia de Usuario y Escritorio macOS Pro

### 4.1. Atajos de Teclado del Sistema (Keyboard Shortcuts)
* **Objetivo**: Facilitar una navegación ágil para usuarios avanzados:
  - `⌘ + N` (macOS) / `Ctrl + N` (Windows): Nueva Factura rápida.
  - `⌘ + B` / `Ctrl + B`: Nuevo Presupuesto.
  - `⌘ + F` / `Ctrl + F`: Foco inmediato en el buscador de la tabla activa.
  - `⌘ + P` / `Ctrl + P`: Vista previa o descarga instantánea del PDF del elemento seleccionado.
  - `⌘ + D` / `Ctrl + D`: Duplicar presupuesto o factura existente como borrador.
  - `Escape`: Cerrar paneles modales / Inspector.

---

### 4.2. Modo Oscuro Completo (macOS Dark Mode)
* **Objetivo**: Integración visual perfecta con el modo nocturno del sistema operativo.
* **Comportamiento**:
  - Adaptación automática según preferencia del sistema (`prefers-color-scheme: dark`) con opción de forzado manual en Configuración.
  - Paleta nativa Apple Dark: fondos en gris grafito profundo (`#1C1C1E`), controles elevados (`#2C2C2E`), textos de alta legibilidad (`#F5F5F7`) y acentos en azul eléctrico vibrante (`#0A84FF`).

---

### 4.3. Código QR Fiscal Interoperable (Veri*Factu / TicketBAI Ready)
* **Objetivo**: Anticiparse al marco regulatorio español y europeo de digitalización tributaria (Ley Antifraude y Reglamento Veri*Factu).
* **Comportamiento**:
  - Inclusión en el pie del PDF de un código QR bidimensional que codifica: NIF emisor, número de factura, fecha, importe total y huella criptográfica de encadenamiento.
  - Lectura directa por parte de clientes y administraciones para verificación instantánea del documento.

---

## 5. Matriz de Priorización y Roadmap Recomendado

| ID | Funcionalidad | Impacto en Negocio | Esfuerzo Técnico | Fase Recomendada |
| :---: | :--- | :---: | :---: | :---: |
| **F-01** | **Gastos de Envío configurables + Descuento Global** | 🟢 Muy Alto | 🟢 Bajo (1–2 días) | **Fase 1 (Inmediata)** |
| **F-02** | **Atajos de Teclado del Sistema (`⌘N`, `⌘B`, `⌘F`, `⌘P`)** | 🟢 Alto | 🟢 Muy Bajo (1 día) | **Fase 1 (Inmediata)** |
| **F-03** | **Exportador Trimestral para Gestoría (Excel/CSV)** | 🟢 Muy Alto | 🟢 Bajo (1–2 días) | **Fase 2 (Corto Plazo)** |
| **F-04** | **Cobros Parciales y Fraccionados (Señales)** | 🟡 Alto | 🟡 Medio (2–3 días) | **Fase 2 (Corto Plazo)** |
| **F-05** | **Plantillas Guardables de Presupuestos** | 🟡 Alto | 🟡 Medio (2 días) | **Fase 3 (Medio Plazo)** |
| **F-06** | **Facturas Rectificativas y Abonos Oficiales** | 🟡 Alto | 🟡 Medio (2–3 días) | **Fase 3 (Medio Plazo)** |
| **F-07** | **Panel de Métricas y Analítica Visual (Dashboard)** | 🟡 Medio | 🟡 Medio (3 días) | **Fase 4 (Avanzada)** |
| **F-08** | **Código QR Fiscal (Veri*Factu / TicketBAI Ready)** | 🟡 Medio | 🟡 Medio (2 días) | **Fase 4 (Avanzada)** |
| **F-09** | **Modo Oscuro Completo (macOS Dark Palette)** | 🔵 Experiencia | 🟡 Medio (2–3 días) | **Fase 4 (Avanzada)** |

---

## 6. Próximo Paso Sugerido

Implementar la **Fase 1**, comenzando por la integración de **Gastos de Envío y Descuentos Globales** en el modelo de datos, la interfaz web macOS (facturas y presupuestos) y el motor de generación de PDFs.

