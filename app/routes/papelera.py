from fastapi import APIRouter
from app.database import db_connection
from app.services.pdf_service import eliminar_pdf_factura

router = APIRouter(prefix="/papelera", tags=["Papelera"])


@router.get("")
def api_obtener_papelera():
    """Obtiene el listado unificado de facturas y presupuestos en papelera."""
    with db_connection() as conn:
        facturas = conn.execute(
            """SELECT f.id, f.numero_factura, f.fecha_emision, f.total_factura, f.updated_at,
                      c.razon_social as cliente_nombre
               FROM facturas f
               LEFT JOIN clientes c ON f.cliente_id = c.id
               WHERE f.is_deleted = 1
               ORDER BY f.updated_at DESC"""
        ).fetchall()
        presupuestos = conn.execute(
            """SELECT p.id, p.numero_presupuesto, p.fecha, p.titulo, p.updated_at,
                      c.razon_social as cliente_nombre,
                      COALESCE(
                        (SELECT total FROM presupuesto_opciones WHERE presupuesto_id = p.id ORDER BY total DESC LIMIT 1),
                        0.0
                      ) as total_estimado
               FROM presupuestos p
               LEFT JOIN clientes c ON p.cliente_id = c.id
               WHERE p.is_deleted = 1
               ORDER BY p.updated_at DESC"""
        ).fetchall()
        return {
            "facturas": [dict(f) for f in facturas],
            "presupuestos": [dict(p) for p in presupuestos],
            "total": len(facturas) + len(presupuestos)
        }


@router.post("/vaciar")
def api_vaciar_papelera():
    """Vacía definitivamente todos los elementos que se encuentren en la papelera y purga sus PDFs en disco."""
    with db_connection() as conn:
        facturas_en_papelera = conn.execute(
            "SELECT numero_factura, fecha_emision, sin_iva FROM facturas WHERE is_deleted = 1"
        ).fetchall()
        for f in facturas_en_papelera:
            eliminar_pdf_factura(f['numero_factura'], f['fecha_emision'], sin_iva=bool(f['sin_iva']))

        conn.execute("UPDATE presupuestos SET factura_id = NULL, estado = 'Aceptado', updated_at = CURRENT_TIMESTAMP WHERE factura_id IN (SELECT id FROM facturas WHERE is_deleted = 1)")
        conn.execute("DELETE FROM facturas WHERE is_deleted = 1")
        conn.execute("DELETE FROM presupuestos WHERE is_deleted = 1")
        return {"message": "Papelera vaciada completamente"}
