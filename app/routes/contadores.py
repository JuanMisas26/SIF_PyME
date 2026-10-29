from fastapi import APIRouter
from app.database import db_connection

router = APIRouter(tags=["Contadores"])


@router.get("/contadores")
def obtener_contadores():
    """Obtiene los contadores globales para las insignias del sidebar y panel de control."""
    with db_connection() as conn:
        facturas = conn.execute("SELECT COUNT(*) FROM facturas WHERE is_deleted = 0").fetchone()[0]
        presupuestos = conn.execute("SELECT COUNT(*) FROM presupuestos WHERE is_deleted = 0").fetchone()[0]
        clientes = conn.execute("SELECT COUNT(*) FROM clientes WHERE is_deleted = 0").fetchone()[0]
        productos = conn.execute("SELECT COUNT(*) FROM productos WHERE is_deleted = 0").fetchone()[0]
        descuentos = conn.execute("SELECT COUNT(*) FROM descuentos WHERE is_deleted = 0 AND activo = 1").fetchone()[0]
        papelera = conn.execute("SELECT (SELECT COUNT(*) FROM facturas WHERE is_deleted = 1) + (SELECT COUNT(*) FROM presupuestos WHERE is_deleted = 1)").fetchone()[0]
        return {
            "facturas": facturas,
            "presupuestos": presupuestos,
            "clientes": clientes,
            "productos": productos,
            "descuentos": descuentos,
            "papelera": papelera
        }
