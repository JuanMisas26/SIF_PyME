import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

import app.database as database_module
import app.paths as paths_module
from main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Crea un entorno de base de datos y PDFs temporal y aislado para la sesión de pruebas."""
    temp_dir = tmp_path_factory.mktemp("sif_test_data")
    test_db_path = temp_dir / "test_facturacion.db"
    test_pdf_dir = temp_dir / "test_pdfs"
    test_backup_dir = temp_dir / "test_backups"

    test_pdf_dir.mkdir(parents=True, exist_ok=True)
    test_backup_dir.mkdir(parents=True, exist_ok=True)

    # Parchear rutas globales en la app
    paths_module.DB_PATH = test_db_path
    paths_module.DATA_DIR = temp_dir
    paths_module.PDF_BASE_DIR = test_pdf_dir
    paths_module.BACKUP_DIR = test_backup_dir
    database_module.DB_PATH = test_db_path
    database_module.DB_DIR = temp_dir

    if hasattr(database_module._local, 'connection') and database_module._local.connection:
        try:
            database_module._local.connection.close()
        except Exception:
            pass
        database_module._local.connection = None

    # Inicializar el esquema
    database_module.init_db()

    yield temp_dir


@pytest.fixture(autouse=True)
def clean_database_tables():
    """Limpia los datos de las tablas antes de cada test para garantizar aislamiento total."""
    with database_module.db_connection() as conn:
        conn.execute("DELETE FROM factura_versiones;")
        conn.execute("DELETE FROM presupuesto_versiones;")
        conn.execute("DELETE FROM presupuesto_lineas;")
        conn.execute("DELETE FROM presupuesto_opciones;")
        conn.execute("DELETE FROM presupuestos;")
        conn.execute("DELETE FROM lineas_factura;")
        conn.execute("DELETE FROM facturas;")
        conn.execute("DELETE FROM clientes;")
        conn.execute("DELETE FROM productos;")
        conn.execute("DELETE FROM configuracion;")
    yield


@pytest.fixture
def client():
    """Retorna un TestClient de FastAPI listo para peticiones HTTP."""
    return TestClient(app)


@pytest.fixture
def emisor_configurado(client):
    """Configura datos fiscales de emisor válidos en la base de datos para pruebas."""
    datos = {
        "nombre": "Empresa de Pruebas S.L.",
        "nif": "B10000008",  # CIF válido
        "direccion": "Calle de Pruebas, 123",
        "codigo_postal": "28001",
        "ciudad": "Madrid",
        "provincia": "Madrid",
        "telefono": "+34 910 000 000",
        "email": "contacto@empresapruebas.es",
        "web": "https://empresapruebas.es",
        "iban": "ES9121000418450200051332",  # IBAN con checksum mod 97 válido
        "serie_defecto": "FAC-2026",
        "iva_defecto": 21.0,
        "irpf_defecto": 0.0,
        "presupuesto_proceso_cierre": "Compromiso de calidad profesional y soporte continuo."
    }
    res = client.put("/api/configuracion", json=datos)
    assert res.status_code == 200, res.text
    return datos

