-- Tabla de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razon_social TEXT NOT NULL,
    nif_cif TEXT,
    telefono TEXT,
    direccion TEXT,
    codigo_postal TEXT,
    ciudad TEXT,
    provincia TEXT,
    email TEXT,
    forma_pago_defecto TEXT DEFAULT 'Transferencia bancaria',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

-- Tabla de Catálogo de Productos/Servicios
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,
    nombre TEXT,
    descripcion TEXT NOT NULL,
    precio_unitario_base REAL NOT NULL DEFAULT 0.0,
    porcentaje_iva REAL NOT NULL DEFAULT 21.0,
    aplica_irpf INTEGER DEFAULT 0,
    porcentaje_irpf REAL DEFAULT 15.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

-- Tabla de Tramos de Precios por Cantidad / Volumen
CREATE TABLE IF NOT EXISTS producto_escalados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    cantidad_minima REAL NOT NULL DEFAULT 1.0,
    cantidad_maxima REAL,
    precio_unitario REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

-- Tabla de Variantes y Atributos de Producto (Colores, Acabados, Tamaños)
CREATE TABLE IF NOT EXISTS producto_variantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    tipo_atributo TEXT NOT NULL DEFAULT 'Color',
    valor TEXT NOT NULL,
    sku_variante TEXT,
    precio_adicional REAL DEFAULT 0.0,
    precio_fijo REAL,
    color_hex TEXT,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_producto_escalados_prod ON producto_escalados(producto_id);
CREATE INDEX IF NOT EXISTS idx_producto_variantes_prod ON producto_variantes(producto_id);

-- Tabla Encabezado de Facturas
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura TEXT UNIQUE NOT NULL,
    serie TEXT DEFAULT 'Factura Nº',
    correlativo INTEGER NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE,
    cliente_id INTEGER NOT NULL,
    base_imponible_total REAL NOT NULL DEFAULT 0.0,
    iva_total REAL NOT NULL DEFAULT 0.0,
    irpf_total REAL NOT NULL DEFAULT 0.0,
    total_factura REAL NOT NULL DEFAULT 0.0,
    sin_iva INTEGER DEFAULT 0,
    estado TEXT CHECK(estado IN ('Borrador', 'Emitida', 'Pagada', 'Vencida', 'Anulada')) DEFAULT 'Emitida',
    observaciones TEXT,
    emisor_snapshot TEXT,
    descuento_id INTEGER,
    descuento_nombre TEXT,
    descuento_tipo TEXT,
    descuento_valor REAL DEFAULT 0.0,
    descuento_importe_total REAL DEFAULT 0.0,
    descuento_visible INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0,
    deleted_con_cliente INTEGER DEFAULT 0,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Tabla de Configuración Clave-Valor
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT
);

-- Tabla de Líneas de Factura
CREATE TABLE IF NOT EXISTS lineas_factura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    producto_id INTEGER,
    descripcion TEXT NOT NULL,
    detalle_material TEXT,
    cantidad REAL NOT NULL DEFAULT 1.0,
    precio_unitario REAL NOT NULL DEFAULT 0.0,
    porcentaje_descuento REAL DEFAULT 0.0,
    porcentaje_iva REAL DEFAULT 21.0,
    porcentaje_irpf REAL DEFAULT 0.0,
    subtotal_base REAL NOT NULL DEFAULT 0.0,
    descuento_id INTEGER,
    precio_unitario_original REAL,
    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Tabla de Presupuestos
CREATE TABLE IF NOT EXISTS presupuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_presupuesto TEXT UNIQUE NOT NULL,
    cliente_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    fecha_validez DATE,
    titulo TEXT NOT NULL DEFAULT 'Presupuesto',
    subtitulo TEXT DEFAULT '',
    porcentaje_iva REAL DEFAULT 21.0,
    porcentaje_irpf REAL DEFAULT 0.0,
    sin_iva INTEGER DEFAULT 0,
    estado TEXT CHECK(estado IN ('Borrador', 'Enviado', 'Aceptado', 'Rechazado', 'Facturado')) DEFAULT 'Borrador',
    factura_id INTEGER,
    opcion_aprobada_id INTEGER,
    observaciones TEXT,
    descuento_id INTEGER,
    descuento_nombre TEXT,
    descuento_tipo TEXT,
    descuento_valor REAL DEFAULT 0.0,
    descuento_importe_total REAL DEFAULT 0.0,
    descuento_visible INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0,
    deleted_con_cliente INTEGER DEFAULT 0,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (factura_id) REFERENCES facturas(id)
);

-- Tabla de Opciones / Variantes de Presupuesto
CREATE TABLE IF NOT EXISTS presupuesto_opciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presupuesto_id INTEGER NOT NULL,
    nombre_opcion TEXT NOT NULL,
    descripcion_corta TEXT,
    orden INTEGER DEFAULT 1,
    subtotal REAL DEFAULT 0.0,
    total REAL DEFAULT 0.0,
    descuento_id INTEGER,
    descuento_nombre TEXT,
    descuento_tipo TEXT,
    descuento_valor REAL DEFAULT 0.0,
    descuento_importe_total REAL DEFAULT 0.0,
    descuento_visible INTEGER DEFAULT 1,
    FOREIGN KEY (presupuesto_id) REFERENCES presupuestos(id) ON DELETE CASCADE
);

-- Tabla de Líneas de Opciones de Presupuesto
CREATE TABLE IF NOT EXISTS presupuesto_lineas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opcion_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    detalle_material TEXT,
    cantidad REAL NOT NULL DEFAULT 1.0,
    precio_unitario REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    orden INTEGER DEFAULT 1,
    descuento_id INTEGER,
    precio_unitario_original REAL,
    FOREIGN KEY (opcion_id) REFERENCES presupuesto_opciones(id) ON DELETE CASCADE
);

-- Tabla de Descuentos y Promociones
CREATE TABLE IF NOT EXISTS descuentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    codigo TEXT UNIQUE,
    tipo TEXT CHECK(tipo IN ('porcentaje', 'fijo')) NOT NULL DEFAULT 'porcentaje',
    valor REAL NOT NULL DEFAULT 0.0,
    aplica_a TEXT CHECK(aplica_a IN ('todos', 'productos')) NOT NULL DEFAULT 'todos',
    descripcion TEXT,
    activo INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_descuentos_activo ON descuentos(activo, is_deleted);

-- Tabla de Vinculación Descuento - Productos Específicos
CREATE TABLE IF NOT EXISTS descuento_productos (
    descuento_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    PRIMARY KEY (descuento_id, producto_id),
    FOREIGN KEY (descuento_id) REFERENCES descuentos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_descuento_prod_prod ON descuento_productos(producto_id);

-- Índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha_emision);
CREATE INDEX IF NOT EXISTS idx_facturas_estado ON facturas(estado);
CREATE INDEX IF NOT EXISTS idx_clientes_busqueda ON clientes(razon_social, nif_cif, telefono, email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_nif_cif ON clientes(nif_cif) WHERE nif_cif IS NOT NULL AND nif_cif != '' AND is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_presupuestos_cliente ON presupuestos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_presupuestos_fecha ON presupuestos(fecha);
CREATE INDEX IF NOT EXISTS idx_presupuestos_estado ON presupuestos(estado);
CREATE INDEX IF NOT EXISTS idx_presupuesto_opciones_presupuesto ON presupuesto_opciones(presupuesto_id);
CREATE INDEX IF NOT EXISTS idx_presupuesto_lineas_opcion ON presupuesto_lineas(opcion_id);
CREATE INDEX IF NOT EXISTS idx_lineas_factura_factura_id ON lineas_factura(factura_id);
CREATE INDEX IF NOT EXISTS idx_lineas_factura_producto_id ON lineas_factura(producto_id);
CREATE INDEX IF NOT EXISTS idx_facturas_activas ON facturas(fecha_emision DESC) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_facturas_cliente_activas ON facturas(cliente_id) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_presupuestos_activos ON presupuestos(fecha DESC) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_presupuestos_cliente_activos ON presupuestos(cliente_id) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_productos_activos ON productos(nombre) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_clientes_activos ON clientes(razon_social) WHERE is_deleted = 0;

-- Tabla de Versiones Históricas de Facturas
CREATE TABLE IF NOT EXISTS factura_versiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    numero_version INTEGER NOT NULL,
    motivo TEXT DEFAULT 'Modificación',
    snapshot_data TEXT NOT NULL,
    total_factura REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
    UNIQUE (factura_id, numero_version)
);
CREATE INDEX IF NOT EXISTS idx_factura_versiones_id ON factura_versiones(factura_id);

-- Tabla de Versiones Históricas de Presupuestos
CREATE TABLE IF NOT EXISTS presupuesto_versiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presupuesto_id INTEGER NOT NULL,
    numero_version INTEGER NOT NULL,
    motivo TEXT DEFAULT 'Modificación',
    snapshot_data TEXT NOT NULL,
    total_estimado REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presupuesto_id) REFERENCES presupuestos(id) ON DELETE CASCADE,
    UNIQUE (presupuesto_id, numero_version)
);
CREATE INDEX IF NOT EXISTS idx_presupuesto_versiones_id ON presupuesto_versiones(presupuesto_id);
