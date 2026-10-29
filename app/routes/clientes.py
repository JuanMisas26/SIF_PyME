import json
import math
from fastapi import APIRouter, Query, Response
from typing import Optional
from app.database import db_connection, get_configuracion
from app.models import ClienteCreate, ClienteUpdate, ClienteResponse
from app.errors import NotFoundError, ConflictError, BusinessRuleError
from app.services.pdf_service import eliminar_pdf_factura, generar_pdf_factura, get_pdf_output_path

router = APIRouter()


@router.get("/clientes")
def listar_clientes(
    response: Response,
    q: Optional[str] = Query(None, description="Buscar por razón social, NIF, teléfono o email"),
    incluir_eliminados: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    paginated: bool = Query(False, description="Devolver respuesta paginada estructurada")
):
    with db_connection() as conn:
        deleted_filter = "" if incluir_eliminados else "WHERE is_deleted = 0"
        if q:
            term = f"%{q.strip()}%"
            cond = "(razon_social LIKE ? OR nif_cif LIKE ? OR telefono LIKE ? OR email LIKE ?)"
            where_clause = f"{deleted_filter} AND {cond}" if deleted_filter else f"WHERE {cond}"
            params = [term, term, term, term]
        else:
            where_clause = deleted_filter
            params = []

        count_query = f"SELECT COUNT(*) FROM clientes {where_clause}"
        total = conn.execute(count_query, params).fetchone()[0]
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        if paginated:
            query = f"SELECT * FROM clientes {where_clause} ORDER BY razon_social LIMIT ? OFFSET ?"
            query_params = list(params) + [page_size, (page - 1) * page_size]
        else:
            if q:
                query = f"SELECT * FROM clientes {where_clause} ORDER BY razon_social LIMIT 25"
                query_params = params
            else:
                query = f"SELECT * FROM clientes {where_clause} ORDER BY razon_social"
                query_params = params

        rows = conn.execute(query, query_params).fetchall()
        items = [dict(r) for r in rows]

        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
            response.headers["X-Total-Pages"] = str(total_pages)

        if paginated:
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        return items


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clientes WHERE id = ? AND is_deleted = 0",
            (cliente_id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Cliente no encontrado")
        return dict(row)


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
def crear_cliente(cliente: ClienteCreate):
    with db_connection() as conn:
        try:
            nif_cif_val = cliente.nif_cif.strip() if (cliente.nif_cif and cliente.nif_cif.strip()) else None
            nombre_val = cliente.razon_social.strip()

            # Evitar creación duplicada por doble clic o doble envío (mismo nombre y NIF)
            if nif_cif_val:
                existing = conn.execute(
                    "SELECT * FROM clientes WHERE nif_cif = ? AND razon_social = ? AND is_deleted = 0",
                    (nif_cif_val, nombre_val)
                ).fetchone()
                if existing:
                    return dict(existing)
            else:
                existing = conn.execute(
                    """SELECT * FROM clientes
                    WHERE razon_social = ? AND nif_cif IS NULL AND is_deleted = 0
                    AND (telefono IS ? OR email IS ?)""",
                    (nombre_val, cliente.telefono.strip() if cliente.telefono else None, cliente.email.strip() if cliente.email else None)
                ).fetchone()
                if existing:
                    return dict(existing)

            cursor = conn.execute(
                """INSERT INTO clientes
                (razon_social, nif_cif, telefono, direccion, codigo_postal, ciudad, provincia, email, forma_pago_defecto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombre_val, nif_cif_val,
                 cliente.telefono.strip() if cliente.telefono else None,
                 cliente.direccion, cliente.codigo_postal, cliente.ciudad,
                 cliente.provincia, cliente.email, cliente.forma_pago_defecto)
            )
            row = conn.execute(
                "SELECT * FROM clientes WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return dict(row)
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ConflictError(f"Ya existe un cliente registrado con el NIF/CIF '{cliente.nif_cif}'")
            raise


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(cliente_id: int, cliente: ClienteUpdate):
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM clientes WHERE id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Cliente no encontrado")

        updates = {k: v for k, v in cliente.model_dump(exclude_unset=True).items()}
        if not updates:
            raise BusinessRuleError("No hay campos para actualizar")

        # Limpiar strings vacíos a None en campos opcionales
        if 'nif_cif' in updates and updates['nif_cif'] is not None and not updates['nif_cif'].strip():
            updates['nif_cif'] = None
        if 'telefono' in updates and updates['telefono'] is not None and not updates['telefono'].strip():
            updates['telefono'] = None

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys() if k != 'updated_at'])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        values = [v for k, v in updates.items() if k != 'updated_at']
        values.append(cliente_id)

        try:
            conn.execute(
                f"UPDATE clientes SET {set_clause} WHERE id = ?",
                values
            )
            row = conn.execute(
                "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
            ).fetchone()
            return dict(row)
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ConflictError(f"Ya existe otro cliente con el NIF/CIF '{cliente.nif_cif}'")
            raise


@router.get("/clientes/{cliente_id}/asociados")
def get_cliente_asociados(cliente_id: int):
    """Devuelve el recuento y listado de facturas y presupuestos activos vinculados al cliente."""
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id, razon_social FROM clientes WHERE id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Cliente no encontrado")

        facturas = conn.execute(
            "SELECT id, numero_factura, total_factura, fecha_emision FROM facturas WHERE cliente_id = ? AND is_deleted = 0",
            (cliente_id,)
        ).fetchall()
        presupuestos = conn.execute(
            "SELECT id, numero_presupuesto, titulo, fecha FROM presupuestos WHERE cliente_id = ? AND is_deleted = 0",
            (cliente_id,)
        ).fetchall()

        return {
            "cliente_id": cliente_id,
            "razon_social": existing["razon_social"],
            "total_facturas": len(facturas),
            "total_presupuestos": len(presupuestos),
            "facturas": [dict(f) for f in facturas],
            "presupuestos": [dict(p) for p in presupuestos]
        }


@router.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int):
    """Soft delete - marca is_deleted=1 en el cliente y en cascada a sus presupuestos y facturas asociados."""
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id, razon_social FROM clientes WHERE id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Cliente no encontrado")

        # Facturas asociadas activas
        facs_activas = conn.execute(
            "SELECT id, numero_factura, fecha_emision, sin_iva FROM facturas WHERE cliente_id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchall()
        for f in facs_activas:
            eliminar_pdf_factura(f['numero_factura'], f['fecha_emision'], sin_iva=bool(f['sin_iva']))
        facs_count = len(facs_activas)

        conn.execute(
            "UPDATE facturas SET is_deleted = 1, deleted_con_cliente = 1, updated_at = CURRENT_TIMESTAMP WHERE cliente_id = ? AND is_deleted = 0",
            (cliente_id,)
        )

        # Presupuestos asociados activos
        pres_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM presupuestos WHERE cliente_id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchone()['cnt']
        conn.execute(
            "UPDATE presupuestos SET is_deleted = 1, deleted_con_cliente = 1, updated_at = CURRENT_TIMESTAMP WHERE cliente_id = ? AND is_deleted = 0",
            (cliente_id,)
        )

        # Cliente
        conn.execute(
            "UPDATE clientes SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cliente_id,)
        )

        return {
            "message": f"Cliente '{existing['razon_social']}' y sus documentos asociados han sido eliminados correctamente.",
            "facturas_eliminadas": facs_count,
            "presupuestos_eliminados": pres_count
        }


@router.post("/clientes/{cliente_id}/restaurar")
def restaurar_cliente(cliente_id: int):
    """Restore a soft-deleted client and only the invoices and budgets deleted during its cascade."""
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id, razon_social FROM clientes WHERE id = ? AND is_deleted = 1", (cliente_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Cliente no encontrado en papelera")

        # Obtener facturas eliminadas con el cliente antes de restaurarlas para regenerar sus PDFs
        facs_a_restaurar = conn.execute(
            "SELECT * FROM facturas WHERE cliente_id = ? AND is_deleted = 1 AND deleted_con_cliente = 1",
            (cliente_id,)
        ).fetchall()

        conn.execute(
            "UPDATE clientes SET is_deleted = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cliente_id,)
        )
        conn.execute(
            "UPDATE facturas SET is_deleted = 0, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE cliente_id = ? AND is_deleted = 1 AND deleted_con_cliente = 1",
            (cliente_id,)
        )
        conn.execute(
            "UPDATE presupuestos SET is_deleted = 0, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE cliente_id = ? AND is_deleted = 1 AND deleted_con_cliente = 1",
            (cliente_id,)
        )

        # Regenerar PDFs en disco para las facturas reactivadas
        cli_dict = dict(existing)
        cli_dict['is_deleted'] = 0
        cfg = get_configuracion()
        for fac_row in facs_a_restaurar:
            fac_dict = dict(fac_row)
            fac_dict['is_deleted'] = 0
            lines = conn.execute("SELECT * FROM lineas_factura WHERE factura_id = ?", (fac_dict['id'],)).fetchall()
            emisor_data = None
            if fac_dict.get('emisor_snapshot'):
                try:
                    emisor_data = json.loads(fac_dict['emisor_snapshot'])
                except Exception:
                    pass
            if not emisor_data:
                emisor_data = cfg
            pdf_path = get_pdf_output_path(fac_dict['numero_factura'], fac_dict['fecha_emision'], sin_iva=bool(fac_dict.get('sin_iva')))
            generar_pdf_factura(fac_dict, [dict(l) for l in lines], cli_dict, pdf_path, emisor_data=emisor_data)

        return {"message": f"Cliente '{existing['razon_social']}' y sus documentos asociados han sido restaurados."}
