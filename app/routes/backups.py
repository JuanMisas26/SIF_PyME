from fastapi import APIRouter
from app.services.backup_service import listar_snapshots, crear_snapshot, restaurar_snapshot

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.get("")
def listar_backups():
    """Lista todas las copias de seguridad disponibles en el directorio de backups."""
    return listar_snapshots()


@router.post("/snapshot")
def crear_backup_manual():
    """Crea una copia de seguridad manual de la base de datos."""
    path = crear_snapshot(motivo="manual")
    return {"message": "Copia de seguridad creada correctamente", "path": str(path)}


@router.post("/{filename}/restaurar")
def api_restaurar_backup(filename: str):
    """Restaura la base de datos desde un archivo de backup validado."""
    restaurar_snapshot(filename)
    return {"message": f"Base de datos restaurada correctamente desde {filename}"}
