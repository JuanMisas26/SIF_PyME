import re
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

from app import paths
from app.errors import NotFoundError, ValidationError

MAX_SNAPSHOTS = 50  # Keep last 50 snapshots


def crear_snapshot(motivo: str = "auto") -> Path:
    """
    Create an immediate backup of the database with a timestamp.
    Called automatically after every invoice emission.
    """
    paths.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    motivo_sano = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(motivo))
    backup_filename = f"facturacion_pyme_{timestamp}_{motivo_sano}.db"
    backup_path = paths.BACKUP_DIR / backup_filename

    # Use SQLite's backup API for a safe, consistent copy
    if paths.DB_PATH.exists():
        source_conn = sqlite3.connect(str(paths.DB_PATH))
        dest_conn = sqlite3.connect(str(backup_path))
        try:
            source_conn.backup(dest_conn)
        finally:
            source_conn.close()
            dest_conn.close()

    # Clean up old snapshots (keep MAX_SNAPSHOTS)
    _cleanup_old_snapshots()

    return backup_path


def _cleanup_old_snapshots():
    """Remove oldest snapshots beyond MAX_SNAPSHOTS limit."""
    snapshots = sorted(paths.BACKUP_DIR.glob("facturacion_pyme_*.db"))
    while len(snapshots) > MAX_SNAPSHOTS:
        oldest = snapshots.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


def listar_snapshots() -> list[dict]:
    """list all available backup snapshots with human-readable timestamps."""
    if not paths.BACKUP_DIR.exists():
        return []

    snapshots = []
    for f in sorted(paths.BACKUP_DIR.glob("facturacion_pyme_*.db"), reverse=True):
        stat = f.stat()
        # Intentar extraer la fecha exacta del nombre del archivo: facturacion_pyme_YYYYMMDD_HHMMSS_motivo.db
        fecha_display = None
        parts = f.stem.split("_")
        for i in range(len(parts) - 1):
            if len(parts[i]) == 8 and parts[i].isdigit() and len(parts[i+1]) == 6 and parts[i+1].isdigit():
                try:
                    dt = datetime.strptime(f"{parts[i]}_{parts[i+1]}", "%Y%m%d_%H%M%S")
                    fecha_display = dt.strftime("%d/%m/%Y %H:%M:%S")
                    break
                except Exception:
                    pass
        if not fecha_display:
            fecha_display = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")

        size_kb = round(stat.st_size / 1024, 1)
        snapshots.append({
            'filename': f.name,
            'path': str(f),
            'size_kb': size_kb,
            'tamano_bytes': stat.st_size,
            'created_at': fecha_display,
            'fecha': fecha_display
        })
    return snapshots


def restaurar_snapshot(snapshot_filename: str) -> bool:
    """Restore the database from a specific snapshot."""
    # Validación estricta contra Path Traversal
    if not snapshot_filename or not re.match(r"^facturacion_pyme_[\w\.\-]+\.db$", snapshot_filename):
        raise ValidationError(f"Nombre de archivo de snapshot no válido: {snapshot_filename}")

    snapshot_path = (paths.BACKUP_DIR / snapshot_filename).resolve()
    if snapshot_path.parent != paths.BACKUP_DIR.resolve():
        raise ValidationError("Ruta de snapshot no autorizada fuera del directorio de backups.")

    if not snapshot_path.is_file():
        raise NotFoundError(f"Snapshot no encontrado: {snapshot_filename}")

    # Create a safety backup before restoring
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_path = paths.BACKUP_DIR / f"facturacion_pyme_{timestamp}_pre_restore.db"
    if paths.DB_PATH.exists():
        shutil.copy2(str(paths.DB_PATH), str(safety_path))

    # Restore using SQLite backup API
    source_conn = sqlite3.connect(str(snapshot_path))
    dest_conn = sqlite3.connect(str(paths.DB_PATH))
    try:
        source_conn.backup(dest_conn)
        try:
            import app.database as database_module
            if hasattr(database_module._local, 'connection') and database_module._local.connection:
                try:
                    database_module._local.connection.close()
                except Exception:
                    pass
                database_module._local.connection = None
        except Exception:
            pass
        return True
    finally:
        source_conn.close()
        dest_conn.close()
