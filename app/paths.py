import sys
import sqlite3
from pathlib import Path

# ============================================================
# RECURSOS DE LECTURA (EMPAQUETADOS / DESARROLLO)
# ============================================================
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Modo empaquetado por PyInstaller: recursos extraídos en _MEIPASS
    BUNDLE_ROOT = Path(sys._MEIPASS)
else:
    # Modo desarrollo normal: raíz del proyecto
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent

STATIC_DIR = BUNDLE_ROOT / "app" / "static"
TEMPLATES_DIR = BUNDLE_ROOT / "app" / "templates"
SCHEMA_PATH = BUNDLE_ROOT / "schema.sql"

# ============================================================
# PERSISTENCIA DE DATOS Y ESCRITURA (ESPECÍFICA DE LA PLATAFORMA)
# ============================================================
DESKTOP_DIR = Path.home() / "Desktop"

if sys.platform == "darwin":
    # macOS Estándar (Apple HIG)
    DATA_DIR = Path.home() / "Library" / "Application Support" / "SIF PyME"
    PDF_BASE_DIR = Path.home() / "Documents" / "Facturas" / "PDFs"
    _icloud_container = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    ICLOUD_PDF_DIR = _icloud_container / "Facturas" if _icloud_container.exists() else None
else:
    # Windows / Linux
    DATA_DIR = Path.home() / "Facturas"
    PDF_BASE_DIR = Path.home() / "Facturas" / "PDFs"
    _onedrive = Path.home() / "OneDrive"
    ICLOUD_PDF_DIR = _onedrive / "Facturas" if _onedrive.exists() else None

DB_DIR = DATA_DIR
DB_PATH = DATA_DIR / "facturacion_pyme.db"
BACKUP_DIR = DATA_DIR / "Backups" / "Snapshots"

# Asegurar directorios base de escritura
DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_BASE_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_pdf_storage_dir(db: sqlite3.Connection | None = None) -> Path:
    """
    Obtiene la ruta configurada para el almacenamiento de PDFs de facturas y presupuestos.
    Si el usuario configuró una ruta personalizada en la tabla 'configuracion', la devuelve.
    De lo contrario, devuelve PDF_BASE_DIR por defecto.
    """
    custom_path_str = None
    if db is not None:
        try:
            cursor = db.execute("SELECT valor FROM configuracion WHERE clave = 'pdf_storage_dir'")
            row = cursor.fetchone()
            if row and row[0] and row[0].strip():
                custom_path_str = row[0].strip()
        except Exception:
            pass
    elif DB_PATH.exists():
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("SELECT valor FROM configuracion WHERE clave = 'pdf_storage_dir'")
            row = cursor.fetchone()
            if row and row[0] and row[0].strip():
                custom_path_str = row[0].strip()
        except Exception:
            pass
        finally:
            if conn:
                conn.close()

    if custom_path_str:
        target = Path(custom_path_str).expanduser().resolve()
    else:
        target = PDF_BASE_DIR

    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception:
        target = PDF_BASE_DIR
        target.mkdir(parents=True, exist_ok=True)

    return target


def get_suggested_storage_paths() -> dict:
    """
    Devuelve las rutas sugeridas para el asistente de instalación y ajustes.
    """
    return {
        "local_default": str(PDF_BASE_DIR),
        "icloud": str(ICLOUD_PDF_DIR) if ICLOUD_PDF_DIR else None,
        "desktop": str(DESKTOP_DIR),
        "current": str(get_pdf_storage_dir()),
        "platform": sys.platform,
    }
