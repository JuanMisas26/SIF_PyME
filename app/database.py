import sqlite3
import threading
from contextlib import contextmanager
import app.paths as paths
from app.paths import DB_DIR, SCHEMA_PATH

# Thread-local storage for connections
_local = threading.local()
_db_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Get or create a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        paths.DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(paths.DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.connection = conn
    return _local.connection


def get_db() -> sqlite3.Connection:
    """Get the database connection for the current thread."""
    return _get_connection()


def init_db():
    """Initialize the database schema from schema.sql and perform migrations."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = _get_connection()
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn.executescript(schema)
        conn.commit()
    else:
        # Inline schema fallback
        conn.executescript("""
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
            CREATE TABLE IF NOT EXISTS producto_escalados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                cantidad_minima REAL NOT NULL DEFAULT 1.0,
                cantidad_maxima REAL,
                precio_unitario REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
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

            CREATE TABLE IF NOT EXISTS descuento_productos (
                descuento_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                PRIMARY KEY (descuento_id, producto_id),
                FOREIGN KEY (descuento_id) REFERENCES descuentos(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_descuento_prod_prod ON descuento_productos(producto_id);

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
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            );
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
            CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas(cliente_id);
            CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha_emision);
            CREATE INDEX IF NOT EXISTS idx_facturas_estado ON facturas(estado);
            CREATE INDEX IF NOT EXISTS idx_clientes_busqueda ON clientes(razon_social, nif_cif, telefono, email);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_nif_cif ON clientes(nif_cif) WHERE nif_cif IS NOT NULL AND nif_cif != '' AND is_deleted = 0;

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
        """)
        conn.commit()

    # Migration: Asegurar columnas añadidas en bases de datos existentes
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(facturas)")
        columnas_facturas = [col[1] for col in cursor.fetchall()]
        if "emisor_snapshot" not in columnas_facturas:
            cursor.execute("ALTER TABLE facturas ADD COLUMN emisor_snapshot TEXT")
            conn.commit()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        conn.commit()

        # Configuración por defecto para documentos editoriales y facturación comercial
        defaults_presupuesto = {
            "serie_defecto": "Factura Nº",
            "numero_inicio_factura": "1",
            "serie_sin_iva": "Factura Sin IVA Nº",
            "numero_inicio_factura_sin_iva": "1",
            "presupuesto_instagram": "",
            "presupuesto_email": "",
            "presupuesto_bienvenida_titulo": "Bienvenidos",
            "presupuesto_bienvenida_subtitulo": "Propuesta de servicios y condiciones comerciales",
            "presupuesto_bienvenida_texto": "Le agradecemos su interés en nuestros servicios profesionales. Presentamos a continuación nuestra propuesta detallada con el alcance de las partidas, especificaciones técnicas y condiciones económicas adaptadas a sus necesidades.\n\nQuedamos a su entera disposición para resolver cualquier duda o ajustar la propuesta según sus preferencias.",
            "presupuesto_condiciones": "• Validez de la oferta: Este presupuesto tiene una validez de 30 días naturales a partir de su fecha de emisión.\n• Forma de pago: 50% a la aceptación del presupuesto y 50% a la finalización y entrega del trabajo, salvo pacto en contrario.\n• Plazos de entrega: Los plazos acordados comenzarán a contar a partir de la recepción de toda la información y material necesario.\n• Modificaciones: Cualquier modificación o ampliación sobre el alcance inicial será presupuestada por separado.\n• Impuestos: Los precios indicados no incluyen IVA salvo que se indique expresamente lo contrario.",
            "presupuesto_proceso_titulo": "Proceso de trabajo",
            "presupuesto_proceso_subtitulo": "Fases del proyecto y tiempos de ejecución",
            "proceso_fase1_titulo": "Planificación y requerimientos",
            "proceso_fase1_puntos": "• Definición del alcance\n• Elaboración de propuesta\n• Aprobación y confirmación\n• Calendario de trabajo",
            "proceso_fase2_titulo": "Desarrollo inicial",
            "proceso_fase2_puntos": "• Ejecución de tareas iniciales\n• Presentación de avances\n• Selección de opciones\n• Primera revisión",
            "proceso_fase3_titulo": "Revisiones y ajustes",
            "proceso_fase3_puntos": "• Aplicación de comentarios\n• Validación de especificaciones\n• Control de calidad\n• Aprobación final",
            "proceso_fase4_titulo": "Entrega y cierre",
            "proceso_fase4_puntos": "• Puesta en marcha / Entrega final\n• Validación de conformidad\n• Soporte y garantía\n• Facturación final",
            "presupuesto_proceso_cierre": "Nuestro compromiso se basa en ofrecer un servicio riguroso, adaptado a los más altos estándares de calidad y con una comunicación fluida durante todas las etapas de ejecución.",
            "factura_condiciones": "Factura emitida de acuerdo con la legislación vigente. El pago deberá realizarse dentro del plazo acordado mediante transferencia bancaria al IBAN indicado en este documento."
        }
        for clave_def, val_def in defaults_presupuesto.items():
            cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)", (clave_def, val_def))
        conn.commit()

        # Migration: lineas_factura (concepto_id -> producto_id)
        cursor.execute("PRAGMA table_info(lineas_factura)")
        columnas_lineas = [col[1] for col in cursor.fetchall()]
        if "producto_id" not in columnas_lineas:
            if "concepto_id" in columnas_lineas:
                try:
                    cursor.execute("ALTER TABLE lineas_factura RENAME COLUMN concepto_id TO producto_id")
                    conn.commit()
                except Exception:
                    cursor.execute("ALTER TABLE lineas_factura ADD COLUMN producto_id INTEGER")
                    cursor.execute("UPDATE lineas_factura SET producto_id = concepto_id")
                    conn.commit()
            else:
                cursor.execute("ALTER TABLE lineas_factura ADD COLUMN producto_id INTEGER")
                conn.commit()

        # Migration: Productos (nombre column)
        cursor.execute("PRAGMA table_info(productos)")
        columnas_productos = [col[1] for col in cursor.fetchall()]
        if "nombre" not in columnas_productos:
            cursor.execute("ALTER TABLE productos ADD COLUMN nombre TEXT")
            cursor.execute("UPDATE productos SET nombre = descripcion WHERE nombre IS NULL OR nombre = ''")
            conn.commit()

        # Migration: Clientes (telefono y nif_cif nullable)
        cursor.execute("PRAGMA table_info(clientes)")
        info_clientes = cursor.fetchall()
        columnas_clientes = {col[1]: col for col in info_clientes}

        if "telefono" not in columnas_clientes:
            cursor.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT")
            conn.commit()

        # Si nif_cif tiene restricción NOT NULL (col[3] == 1), recrear tabla clientes
        if "nif_cif" in columnas_clientes and columnas_clientes["nif_cif"][3] == 1:
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes_migracion (
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
                )
            """)
            cursor.execute("""
                INSERT INTO clientes_migracion (id, razon_social, nif_cif, telefono, direccion, codigo_postal, ciudad, provincia, email, forma_pago_defecto, created_at, updated_at, is_deleted)
                SELECT id, razon_social, NULLIF(TRIM(nif_cif), ''), telefono, direccion, codigo_postal, ciudad, provincia, email, forma_pago_defecto, created_at, updated_at, is_deleted
                FROM clientes
            """)
            cursor.execute("DROP TABLE clientes")
            cursor.execute("ALTER TABLE clientes_migracion RENAME TO clientes")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_busqueda ON clientes(razon_social, nif_cif, telefono, email)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_nif_cif ON clientes(nif_cif) WHERE nif_cif IS NOT NULL AND nif_cif != '' AND is_deleted = 0")
            cursor.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        else:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_busqueda ON clientes(razon_social, nif_cif, telefono, email)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_nif_cif ON clientes(nif_cif) WHERE nif_cif IS NOT NULL AND nif_cif != '' AND is_deleted = 0")
            conn.commit()

        # Migration: Tablas de historial de versiones (Time Machine)
        cursor.execute("""
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
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factura_versiones_id ON factura_versiones(factura_id)")

        cursor.execute("""
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
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_presupuesto_versiones_id ON presupuesto_versiones(presupuesto_id)")

        # Optimización de Rendimiento e Índices (FKs y Partial Indexes para registros activos)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lineas_factura_factura_id ON lineas_factura(factura_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lineas_factura_producto_id ON lineas_factura(producto_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_activas ON facturas(fecha_emision DESC) WHERE is_deleted = 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_cliente_activas ON facturas(cliente_id) WHERE is_deleted = 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_presupuestos_activos ON presupuestos(fecha DESC) WHERE is_deleted = 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_presupuestos_cliente_activos ON presupuestos(cliente_id) WHERE is_deleted = 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activos ON productos(nombre) WHERE is_deleted = 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_activos ON clientes(razon_social) WHERE is_deleted = 0")

        # Migration: columna detalle_material en lineas_factura
        cursor.execute("PRAGMA table_info(lineas_factura)")
        cols_lf = [c[1] for c in cursor.fetchall()]
        if "detalle_material" not in cols_lf:
            cursor.execute("ALTER TABLE lineas_factura ADD COLUMN detalle_material TEXT")

        # Migration: Tablas de escalados de precios por volumen y variantes de producto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS producto_escalados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                cantidad_minima REAL NOT NULL DEFAULT 1.0,
                cantidad_maxima REAL,
                precio_unitario REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_producto_escalados_prod ON producto_escalados(producto_id)")

        cursor.execute("""
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
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_producto_variantes_prod ON producto_variantes(producto_id)")

        # Migration: columna sin_iva en facturas
        cursor.execute("PRAGMA table_info(facturas)")
        cols_facturas = [c[1] for c in cursor.fetchall()]
        if "sin_iva" not in cols_facturas:
            cursor.execute("ALTER TABLE facturas ADD COLUMN sin_iva INTEGER DEFAULT 0")

        # Migration: columnas de impuestos y régimen en presupuestos
        cursor.execute("PRAGMA table_info(presupuestos)")
        cols_presupuestos = [c[1] for c in cursor.fetchall()]
        if "porcentaje_iva" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN porcentaje_iva REAL DEFAULT 21.0")
        if "porcentaje_irpf" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN porcentaje_irpf REAL DEFAULT 0.0")
        if "sin_iva" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN sin_iva INTEGER DEFAULT 0")

        # Migration: tablas descuentos y descuento_productos
        cursor.execute("""
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
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_descuentos_activo ON descuentos(activo, is_deleted)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS descuento_productos (
                descuento_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                PRIMARY KEY (descuento_id, producto_id),
                FOREIGN KEY (descuento_id) REFERENCES descuentos(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_descuento_prod_prod ON descuento_productos(producto_id)")

        # Migration: columnas de descuento en facturas
        cursor.execute("PRAGMA table_info(facturas)")
        cols_fac = [c[1] for c in cursor.fetchall()]
        if "descuento_id" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_id INTEGER")
        if "descuento_nombre" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_nombre TEXT")
        if "descuento_tipo" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_tipo TEXT")
        if "descuento_valor" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_valor REAL DEFAULT 0.0")
        if "descuento_importe_total" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_importe_total REAL DEFAULT 0.0")
        if "descuento_visible" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN descuento_visible INTEGER DEFAULT 1")
        if "deleted_con_cliente" not in cols_fac:
            cursor.execute("ALTER TABLE facturas ADD COLUMN deleted_con_cliente INTEGER DEFAULT 0")

        # Migration: columnas de descuento en lineas_factura
        cursor.execute("PRAGMA table_info(lineas_factura)")
        cols_lfac = [c[1] for c in cursor.fetchall()]
        if "descuento_id" not in cols_lfac:
            cursor.execute("ALTER TABLE lineas_factura ADD COLUMN descuento_id INTEGER")
        if "precio_unitario_original" not in cols_lfac:
            cursor.execute("ALTER TABLE lineas_factura ADD COLUMN precio_unitario_original REAL")

        # Migration: columnas de descuento en presupuestos
        if "descuento_id" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_id INTEGER")
        if "descuento_nombre" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_nombre TEXT")
        if "descuento_tipo" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_tipo TEXT")
        if "descuento_valor" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_valor REAL DEFAULT 0.0")
        if "descuento_importe_total" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_importe_total REAL DEFAULT 0.0")
        if "descuento_visible" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN descuento_visible INTEGER DEFAULT 1")
        if "deleted_con_cliente" not in cols_presupuestos:
            cursor.execute("ALTER TABLE presupuestos ADD COLUMN deleted_con_cliente INTEGER DEFAULT 0")

        # Migration: columnas de descuento en presupuesto_opciones
        cursor.execute("PRAGMA table_info(presupuesto_opciones)")
        cols_popc = [c[1] for c in cursor.fetchall()]
        if "descuento_id" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_id INTEGER")
        if "descuento_nombre" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_nombre TEXT")
        if "descuento_tipo" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_tipo TEXT")
        if "descuento_valor" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_valor REAL DEFAULT 0.0")
        if "descuento_importe_total" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_importe_total REAL DEFAULT 0.0")
        if "descuento_visible" not in cols_popc:
            cursor.execute("ALTER TABLE presupuesto_opciones ADD COLUMN descuento_visible INTEGER DEFAULT 1")

        # Migration: columnas de descuento en presupuesto_lineas
        cursor.execute("PRAGMA table_info(presupuesto_lineas)")
        cols_plin = [c[1] for c in cursor.fetchall()]
        if "descuento_id" not in cols_plin:
            cursor.execute("ALTER TABLE presupuesto_lineas ADD COLUMN descuento_id INTEGER")
        if "precio_unitario_original" not in cols_plin:
            cursor.execute("ALTER TABLE presupuesto_lineas ADD COLUMN precio_unitario_original REAL")

        conn.commit()
    except Exception as e:
        print(f"Error en migración: {e}")


def get_configuracion() -> dict:
    """Obtiene toda la configuración en forma de diccionario."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM configuracion")
    rows = cursor.fetchall()
    return {row["clave"]: (row["valor"] if row["valor"] is not None else "") for row in rows}


def set_configuracion(valores: dict):
    """Guarda o actualiza valores de configuración en la tabla clave-valor."""
    with db_connection() as conn:
        cursor = conn.cursor()
        for clave, valor in valores.items():
            str_val = "" if valor is None else str(valor).strip()
            cursor.execute("""
                INSERT INTO configuracion (clave, valor)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
            """, (clave, str_val))


def es_configuracion_valida(config: dict = None) -> bool:
    """Verifica si los datos fiscales mínimos (nombre y nif) están presentes y no vacíos."""
    if config is None:
        config = get_configuracion()
    nombre = config.get("nombre", "").strip()
    nif = config.get("nif", "").strip()
    return bool(nombre and nif)


@contextmanager
def db_connection():
    """Context manager for database transactions with automatic commit/rollback."""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close_db():
    """Close the current thread's database connection."""
    if hasattr(_local, 'connection') and _local.connection is not None:
        _local.connection.close()
        _local.connection = None

