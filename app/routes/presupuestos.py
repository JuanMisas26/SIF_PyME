import math
from fastapi import APIRouter, Response, Query
from typing import Optional
from datetime import date
import re
import json

from app.database import db_connection, get_configuracion, es_configuracion_valida
from app.models import (
    PresupuestoCreate,
    PresupuestoUpdate,
    PresupuestoEstadoUpdate,
    PresupuestoResponse,
    PresupuestoDetailResponse,
    PresupuestoOpcionResponse,
    PresupuestoLineaResponse,
    ClienteResponse,
    PresupuestoConvertirFacturaRequest,
    PresupuestoPreviewRequest,
    round2,
)
from app.errors import NotFoundError, ConflictError, BusinessRuleError, ValidationError
from app.services.presupuesto_pdf_service import generar_pdf_presupuesto
from app.services.pdf_service import generar_numero_factura, generar_pdf_factura, get_pdf_output_path, calcular_totales_factura, eliminar_pdf_factura
from app.services.version_service import (
    crear_version_presupuesto, listar_versiones_presupuesto,
    obtener_detalle_version_presupuesto, restaurar_version_presupuesto,
    crear_version_factura
)

router = APIRouter(prefix="/presupuestos", tags=["Presupuestos"])


def slugify_nombre(nombre: str) -> str:
    """Convierte un nombre en slug limpio para el identificador YYYY-MM-DD-nombre."""
    slug = nombre.lower().strip()
    slug = re.sub(r'[áàäâ]', 'a', slug)
    slug = re.sub(r'[éèëê]', 'e', slug)
    slug = re.sub(r'[íìïî]', 'i', slug)
    slug = re.sub(r'[óòöô]', 'o', slug)
    slug = re.sub(r'[úùüû]', 'u', slug)
    slug = re.sub(r'ñ', 'n', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug or "cliente"


@router.get("/siguiente-numero")
def sugerir_numero_presupuesto(cliente_nombre: Optional[str] = None):
    """Genera una sugerencia de código con formato YYYY-MM-DD-nombre."""
    hoy = date.today().strftime("%Y-%m-%d")
    nombre_slug = slugify_nombre(cliente_nombre) if cliente_nombre else "nuevo-cliente"
    base_sugerida = f"{hoy}-{nombre_slug}"

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT numero_presupuesto FROM presupuestos WHERE numero_presupuesto = ?", (base_sugerida,))
        if cursor.fetchone():
            # Añadir sufijo numérico si ya existe uno igual hoy (incluso en papelera)
            contador = 2
            while True:
                candidato = f"{base_sugerida}-{contador}"
                cursor.execute("SELECT numero_presupuesto FROM presupuestos WHERE numero_presupuesto = ?", (candidato,))
                if not cursor.fetchone():
                    return {"sugerencia": candidato}
                contador += 1

        return {"sugerencia": base_sugerida}


@router.get("")
def listar_presupuestos(
    response: Response,
    q: Optional[str] = Query(None, description="Búsqueda por número, título o cliente"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    paginated: bool = Query(False, description="Devolver respuesta paginada estructurada")
):
    with db_connection() as conn:
        cursor = conn.cursor()

        count_query = """
            SELECT COUNT(*)
            FROM presupuestos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE p.is_deleted = 0
        """
        count_params = []
        if estado:
            count_query += " AND p.estado = ?"
            count_params.append(estado)
        if cliente_id:
            count_query += " AND p.cliente_id = ?"
            count_params.append(cliente_id)
        if q:
            count_query += " AND (p.numero_presupuesto LIKE ? OR p.titulo LIKE ? OR c.razon_social LIKE ?)"
            term = f"%{q.strip()}%"
            count_params.extend([term, term, term])

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        query = """
            SELECT p.id, p.numero_presupuesto, p.cliente_id, c.razon_social as cliente_nombre,
                   c.nif_cif as cliente_nif, c.telefono as cliente_telefono, c.email as cliente_email,
                   p.fecha, p.fecha_validez, p.titulo, p.subtitulo, p.estado,
                   p.porcentaje_iva, p.porcentaje_irpf, p.sin_iva,
                   p.factura_id, f.numero_factura, p.opcion_aprobada_id, p.created_at,
                   (SELECT nombre_opcion FROM presupuesto_opciones WHERE id = p.opcion_aprobada_id) as opcion_aprobada_nombre,
                   (SELECT total FROM presupuesto_opciones WHERE id = p.opcion_aprobada_id) as opcion_aprobada_total,
                   (SELECT MIN(total) FROM presupuesto_opciones WHERE presupuesto_id = p.id) as total_minimo,
                   (SELECT MAX(total) FROM presupuesto_opciones WHERE presupuesto_id = p.id) as total_maximo,
                   (SELECT COUNT(*) FROM presupuesto_opciones WHERE presupuesto_id = p.id) as cantidad_opciones
            FROM presupuestos p
            JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN facturas f ON p.factura_id = f.id
            WHERE p.is_deleted = 0
        """
        params = []

        if estado:
            query += " AND p.estado = ?"
            params.append(estado)
        if cliente_id:
            query += " AND p.cliente_id = ?"
            params.append(cliente_id)
        if q:
            query += " AND (p.numero_presupuesto LIKE ? OR p.titulo LIKE ? OR c.razon_social LIKE ?)"
            term = f"%{q.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY p.fecha DESC, p.id DESC"

        if paginated:
            query += " LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append(PresupuestoResponse(
                id=r["id"],
                numero_presupuesto=r["numero_presupuesto"],
                cliente_id=r["cliente_id"],
                cliente_nombre=r["cliente_nombre"],
                cliente_nif=r["cliente_nif"],
                cliente_telefono=r["cliente_telefono"],
                cliente_email=r["cliente_email"],
                fecha=r["fecha"],
                fecha_validez=r["fecha_validez"],
                titulo=r["titulo"],
                subtitulo=r["subtitulo"],
                estado=r["estado"],
                total_minimo=r["total_minimo"] or 0.0,
                total_maximo=r["total_maximo"] or 0.0,
                cantidad_opciones=r["cantidad_opciones"] or 0,
                porcentaje_iva=r["porcentaje_iva"] if "porcentaje_iva" in r.keys() and r["porcentaje_iva"] is not None else 21.0,
                porcentaje_irpf=r["porcentaje_irpf"] if "porcentaje_irpf" in r.keys() and r["porcentaje_irpf"] is not None else 0.0,
                sin_iva=bool(r["sin_iva"]) if "sin_iva" in r.keys() and r["sin_iva"] is not None else False,
                factura_id=r["factura_id"],
                numero_factura=r["numero_factura"],
                opcion_aprobada_id=r["opcion_aprobada_id"],
                opcion_aprobada_nombre=r["opcion_aprobada_nombre"],
                opcion_aprobada_total=r["opcion_aprobada_total"],
                created_at=r["created_at"]
            ))

    if response:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        response.headers["X-Total-Pages"] = str(total_pages)

    if paginated:
        return {
            "items": [r.model_dump() for r in result],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    return result


@router.post("", response_model=PresupuestoDetailResponse)
def crear_presupuesto(data: PresupuestoCreate):
    with db_connection() as conn:
        cursor = conn.cursor()

        # Validar que el cliente existe
        cursor.execute("SELECT id FROM clientes WHERE id = ? AND is_deleted = 0", (data.cliente_id,))
        if not cursor.fetchone():
            raise NotFoundError("Cliente no encontrado o inactivo", field="cliente_id")

        # Validar número de presupuesto único
        cursor.execute("SELECT id FROM presupuestos WHERE numero_presupuesto = ? AND is_deleted = 0", (data.numero_presupuesto,))
        if cursor.fetchone():
            raise ConflictError(f"El identificador de presupuesto '{data.numero_presupuesto}' ya está en uso.", field="numero_presupuesto")

        cursor.execute("""
            INSERT INTO presupuestos (numero_presupuesto, cliente_id, fecha, fecha_validez, titulo, subtitulo, estado, observaciones,
                                      porcentaje_iva, porcentaje_irpf, sin_iva)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.numero_presupuesto.strip(),
            data.cliente_id,
            data.fecha.isoformat(),
            data.fecha_validez.isoformat() if data.fecha_validez else None,
            data.titulo.strip(),
            data.subtitulo.strip() if data.subtitulo else None,
            data.estado,
            data.observaciones,
            data.porcentaje_iva if data.porcentaje_iva is not None else 21.0,
            data.porcentaje_irpf if data.porcentaje_irpf is not None else 0.0,
            1 if getattr(data, 'sin_iva', False) else 0
        ))
        presupuesto_id = cursor.lastrowid

        # Insertar opciones y líneas
        for orden_op, op in enumerate(data.opciones, 1):
            subtotal_op = 0.0
            for l in op.lineas:
                subtotal_op += round2(l.cantidad * l.precio_unitario)

            desc_id = getattr(op, 'descuento_id', None)
            desc_nom = getattr(op, 'descuento_nombre', None)
            desc_tipo = getattr(op, 'descuento_tipo', None)
            desc_val = float(getattr(op, 'descuento_valor', 0.0) or 0.0)
            desc_imp = float(getattr(op, 'descuento_importe_total', 0.0) or 0.0)
            desc_vis = 1 if (getattr(op, 'descuento_visible', True) is not False) else 0

            cursor.execute("""
                INSERT INTO presupuesto_opciones (presupuesto_id, nombre_opcion, descripcion_corta, orden, subtotal, total,
                                                 descuento_id, descuento_nombre, descuento_tipo, descuento_valor, descuento_importe_total, descuento_visible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                presupuesto_id,
                op.nombre_opcion.strip(),
                op.descripcion_corta.strip() if op.descripcion_corta else None,
                op.orden or orden_op,
                subtotal_op,
                subtotal_op,
                desc_id, desc_nom, desc_tipo, desc_val, desc_imp, desc_vis
            ))
            opcion_id = cursor.lastrowid

            for orden_l, l in enumerate(op.lineas, 1):
                tot_l = round2(l.cantidad * l.precio_unitario)
                cursor.execute("""
                    INSERT INTO presupuesto_lineas (opcion_id, descripcion, detalle_material, cantidad, precio_unitario, total, orden, descuento_id, precio_unitario_original)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opcion_id,
                    l.descripcion.strip(),
                    l.detalle_material.strip() if l.detalle_material else None,
                    l.cantidad,
                    l.precio_unitario,
                    tot_l,
                    l.orden or orden_l,
                    getattr(l, 'descuento_id', None),
                    getattr(l, 'precio_unitario_original', None)
                ))

        crear_version_presupuesto(conn, presupuesto_id, motivo="Creación inicial del presupuesto")

    return obtener_detalle_presupuesto(presupuesto_id)


def obtener_detalle_presupuesto(presupuesto_id: int) -> PresupuestoDetailResponse:
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, c.razon_social, c.nif_cif, c.telefono, c.direccion, c.codigo_postal, c.ciudad, c.provincia, c.email, c.forma_pago_defecto
            FROM presupuestos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE p.id = ? AND p.is_deleted = 0
        """, (presupuesto_id,))
        row = cursor.fetchone()
        if not row:
            raise NotFoundError("Presupuesto no encontrado")

        cliente = ClienteResponse(
            id=row["cliente_id"],
            razon_social=row["razon_social"],
            nif_cif=row["nif_cif"],
            telefono=row["telefono"],
            direccion=row["direccion"],
            codigo_postal=row["codigo_postal"],
            ciudad=row["ciudad"],
            provincia=row["provincia"],
            email=row["email"],
            forma_pago_defecto=row["forma_pago_defecto"] or "Transferencia bancaria"
        )

        # Opciones
        cursor.execute("""
            SELECT * FROM presupuesto_opciones
            WHERE presupuesto_id = ?
            ORDER BY orden ASC, id ASC
        """, (presupuesto_id,))
        rows_op = cursor.fetchall()

        op_ids = [ro["id"] for ro in rows_op]
        lineas_por_opcion = {op_id: [] for op_id in op_ids}
        if op_ids:
            placeholders = ",".join("?" for _ in op_ids)
            cursor.execute(f"""
                SELECT * FROM presupuesto_lineas
                WHERE opcion_id IN ({placeholders})
                ORDER BY orden ASC, id ASC
            """, op_ids)
            for rl in cursor.fetchall():
                lineas_por_opcion[rl["opcion_id"]].append(PresupuestoLineaResponse(
                    id=rl["id"],
                    opcion_id=rl["opcion_id"],
                    descripcion=rl["descripcion"],
                    detalle_material=rl["detalle_material"] or "",
                    cantidad=rl["cantidad"],
                    precio_unitario=rl["precio_unitario"],
                    total=rl["total"],
                    orden=rl["orden"],
                    descuento_id=rl["descuento_id"] if "descuento_id" in rl.keys() else None,
                    precio_unitario_original=rl["precio_unitario_original"] if "precio_unitario_original" in rl.keys() else None
                ))

        opciones = []
        for ro in rows_op:
            opciones.append(PresupuestoOpcionResponse(
                id=ro["id"],
                presupuesto_id=ro["presupuesto_id"],
                nombre_opcion=ro["nombre_opcion"],
                descripcion_corta=ro["descripcion_corta"],
                orden=ro["orden"],
                subtotal=ro["subtotal"],
                total=ro["total"],
                descuento_id=ro["descuento_id"] if "descuento_id" in ro.keys() else None,
                descuento_nombre=ro["descuento_nombre"] if "descuento_nombre" in ro.keys() else None,
                descuento_tipo=ro["descuento_tipo"] if "descuento_tipo" in ro.keys() else None,
                descuento_valor=ro["descuento_valor"] if "descuento_valor" in ro.keys() and ro["descuento_valor"] is not None else 0.0,
                descuento_importe_total=ro["descuento_importe_total"] if "descuento_importe_total" in ro.keys() and ro["descuento_importe_total"] is not None else 0.0,
                descuento_visible=bool(ro["descuento_visible"]) if "descuento_visible" in ro.keys() and ro["descuento_visible"] is not None else True,
                lineas=lineas_por_opcion.get(ro["id"], [])
            ))

        op_aprobada = next((o for o in opciones if o.id == row["opcion_aprobada_id"]), None) if row["opcion_aprobada_id"] else None
        return PresupuestoDetailResponse(
            id=row["id"],
            numero_presupuesto=row["numero_presupuesto"],
            cliente_id=row["cliente_id"],
            cliente=cliente,
            fecha=row["fecha"],
            fecha_validez=row["fecha_validez"],
            titulo=row["titulo"],
            subtitulo=row["subtitulo"],
            estado=row["estado"],
            porcentaje_iva=row["porcentaje_iva"] if "porcentaje_iva" in row.keys() and row["porcentaje_iva"] is not None else 21.0,
            porcentaje_irpf=row["porcentaje_irpf"] if "porcentaje_irpf" in row.keys() and row["porcentaje_irpf"] is not None else 0.0,
            sin_iva=bool(row["sin_iva"]) if "sin_iva" in row.keys() and row["sin_iva"] is not None else False,
            factura_id=row["factura_id"],
            opcion_aprobada_id=row["opcion_aprobada_id"],
            opcion_aprobada_nombre=op_aprobada.nombre_opcion if op_aprobada else None,
            opcion_aprobada_total=op_aprobada.total if op_aprobada else None,
            observaciones=row["observaciones"],
            opciones=opciones,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


@router.get("/{id}", response_model=PresupuestoDetailResponse)
def get_presupuesto(id: int):
    return obtener_detalle_presupuesto(id)


@router.put("/{id}", response_model=PresupuestoDetailResponse)
def actualizar_presupuesto(id: int, data: PresupuestoUpdate):
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id, estado, factura_id, opcion_aprobada_id FROM presupuestos WHERE id = ? AND is_deleted = 0", (id,))
        presupuesto_actual = cursor.fetchone()
        if not presupuesto_actual:
            raise NotFoundError("Presupuesto no encontrado")

        if presupuesto_actual["estado"] == "Facturado" or presupuesto_actual["factura_id"]:
            raise BusinessRuleError(
                f"No se puede modificar directamente un presupuesto en estado 'Facturado'. "
                f"Para editarlo, debe volver primero a estado Borrador."
            )

        if data.numero_presupuesto:
            cursor.execute("SELECT id FROM presupuestos WHERE numero_presupuesto = ? AND id != ? AND is_deleted = 0", (data.numero_presupuesto, id))
            if cursor.fetchone():
                raise ConflictError(f"El identificador '{data.numero_presupuesto}' ya pertenece a otro presupuesto.", field="numero_presupuesto")

        campos = []
        valores = []

        if data.numero_presupuesto is not None:
            campos.append("numero_presupuesto = ?")
            valores.append(data.numero_presupuesto.strip())
        if data.cliente_id is not None:
            campos.append("cliente_id = ?")
            valores.append(data.cliente_id)
        if data.fecha is not None:
            campos.append("fecha = ?")
            valores.append(data.fecha.isoformat())
        if data.fecha_validez is not None:
            campos.append("fecha_validez = ?")
            valores.append(data.fecha_validez.isoformat())
        if data.titulo is not None:
            campos.append("titulo = ?")
            valores.append(data.titulo.strip())
        if data.subtitulo is not None:
            campos.append("subtitulo = ?")
            valores.append(data.subtitulo.strip())
        if data.observaciones is not None:
            campos.append("observaciones = ?")
            valores.append(data.observaciones)
        if data.estado is not None:
            campos.append("estado = ?")
            valores.append(data.estado)
        if data.opcion_aprobada_id is not None:
            campos.append("opcion_aprobada_id = ?")
            valores.append(data.opcion_aprobada_id)
        if data.porcentaje_iva is not None:
            campos.append("porcentaje_iva = ?")
            valores.append(data.porcentaje_iva)
        if data.porcentaje_irpf is not None:
            campos.append("porcentaje_irpf = ?")
            valores.append(data.porcentaje_irpf)
        if data.sin_iva is not None:
            campos.append("sin_iva = ?")
            valores.append(1 if data.sin_iva else 0)

        if campos:
            campos.append("updated_at = CURRENT_TIMESTAMP")
            valores.append(id)
            cursor.execute(f"UPDATE presupuestos SET {', '.join(campos)} WHERE id = ?", valores)

        # Si se envían nuevas opciones, reemplazarlas
        if data.opciones is not None:
            opcion_previa_id = presupuesto_actual["opcion_aprobada_id"]
            nombre_aprobada_previa = None
            if opcion_previa_id:
                cursor.execute("SELECT nombre_opcion FROM presupuesto_opciones WHERE id = ?", (opcion_previa_id,))
                row_op = cursor.fetchone()
                if row_op:
                    nombre_aprobada_previa = row_op["nombre_opcion"]

            cursor.execute("DELETE FROM presupuesto_opciones WHERE presupuesto_id = ?", (id,))
            nueva_aprobada_id = None

            for orden_op, op in enumerate(data.opciones, 1):
                subtotal_op = sum(round2(l.cantidad * l.precio_unitario) for l in op.lineas)

                desc_id = getattr(op, 'descuento_id', None)
                desc_nom = getattr(op, 'descuento_nombre', None)
                desc_tipo = getattr(op, 'descuento_tipo', None)
                desc_val = float(getattr(op, 'descuento_valor', 0.0) or 0.0)
                desc_imp = float(getattr(op, 'descuento_importe_total', 0.0) or 0.0)
                desc_vis = 1 if (getattr(op, 'descuento_visible', True) is not False) else 0

                cursor.execute("""
                    INSERT INTO presupuesto_opciones (presupuesto_id, nombre_opcion, descripcion_corta, orden, subtotal, total,
                                                     descuento_id, descuento_nombre, descuento_tipo, descuento_valor, descuento_importe_total, descuento_visible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    id,
                    op.nombre_opcion.strip(),
                    op.descripcion_corta.strip() if op.descripcion_corta else None,
                    op.orden or orden_op,
                    subtotal_op,
                    subtotal_op,
                    desc_id, desc_nom, desc_tipo, desc_val, desc_imp, desc_vis
                ))
                opcion_id = cursor.lastrowid
                if nombre_aprobada_previa and op.nombre_opcion.strip().lower() == nombre_aprobada_previa.strip().lower():
                    nueva_aprobada_id = opcion_id

                for orden_l, l in enumerate(op.lineas, 1):
                    tot_l = round2(l.cantidad * l.precio_unitario)
                    cursor.execute("""
                        INSERT INTO presupuesto_lineas (opcion_id, descripcion, detalle_material, cantidad, precio_unitario, total, orden, descuento_id, precio_unitario_original)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        opcion_id,
                        l.descripcion.strip(),
                        l.detalle_material.strip() if l.detalle_material else None,
                        l.cantidad,
                        l.precio_unitario,
                        tot_l,
                        l.orden or orden_l,
                        getattr(l, 'descuento_id', None),
                        getattr(l, 'precio_unitario_original', None)
                    ))

            if data.opcion_aprobada_id is None and opcion_previa_id:
                cursor.execute("UPDATE presupuestos SET opcion_aprobada_id = ? WHERE id = ?", (nueva_aprobada_id, id))

        crear_version_presupuesto(conn, id, motivo="Modificación de opciones y líneas")

    return obtener_detalle_presupuesto(id)


@router.patch("/{id}/estado")
def cambiar_estado_presupuesto(id: int, data: PresupuestoEstadoUpdate):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, numero_presupuesto, estado, factura_id, opcion_aprobada_id FROM presupuestos WHERE id = ? AND is_deleted = 0", (id,))
        p = cursor.fetchone()
        if not p:
            raise NotFoundError("Presupuesto no encontrado")

        if data.estado == "Facturado" and not p["factura_id"]:
            raise BusinessRuleError("Para marcar como Facturado, use la opción de Facturar / Convertir a factura.")

        if data.opcion_aprobada_id is not None:
            cursor.execute("SELECT id FROM presupuesto_opciones WHERE id = ? AND presupuesto_id = ?", (data.opcion_aprobada_id, id))
            if not cursor.fetchone():
                raise NotFoundError("La opción seleccionada no pertenece a este presupuesto")

        nueva_opcion_aprobada = p["opcion_aprobada_id"]
        if data.opcion_aprobada_id is not None:
            nueva_opcion_aprobada = data.opcion_aprobada_id
        elif data.estado == "Borrador":
            nueva_opcion_aprobada = None

        # Si regresa a Borrador y tenía una factura generada vinculada:
        factura_id_a_desvincular = p["factura_id"]
        nuevo_factura_id = p["factura_id"]
        factura_num = ""
        factura_absorbida = False
        sync_iva = None
        sync_irpf = None
        sync_sin_iva = None

        if data.estado == "Borrador" and factura_id_a_desvincular:
            nuevo_factura_id = None
            cursor.execute("SELECT numero_factura, fecha_emision, sin_iva, iva_total, irpf_total FROM facturas WHERE id = ?", (factura_id_a_desvincular,))
            fac_row = cursor.fetchone()
            if fac_row:
                factura_num = fac_row["numero_factura"]
                sync_sin_iva = bool(fac_row["sin_iva"])

            cursor.execute("SELECT * FROM lineas_factura WHERE factura_id = ? ORDER BY id ASC", (factura_id_a_desvincular,))
            fac_lineas = cursor.fetchall()

            # Opción del presupuesto a sincronizar
            opcion_target_id = p["opcion_aprobada_id"]
            if not opcion_target_id:
                cursor.execute("SELECT id FROM presupuesto_opciones WHERE presupuesto_id = ? ORDER BY orden ASC, id ASC LIMIT 1", (id,))
                op_row = cursor.fetchone()
                if op_row:
                    opcion_target_id = op_row["id"]

            if opcion_target_id and fac_lineas:
                factura_absorbida = True
                cursor.execute("DELETE FROM presupuesto_lineas WHERE opcion_id = ?", (opcion_target_id,))
                subtotal_op = 0.0

                for idx_l, lf in enumerate(fac_lineas, 1):
                    cant = float(lf["cantidad"]) if lf["cantidad"] is not None else 1.0
                    pu = float(lf["precio_unitario"]) if lf["precio_unitario"] is not None else 0.0
                    dto = float(lf["porcentaje_descuento"]) if lf["porcentaje_descuento"] is not None else 0.0
                    pu_efectivo = round2(pu * (1 - dto / 100)) if dto else pu
                    tot_l = round2(cant * pu_efectivo)
                    subtotal_op += tot_l

                    if lf["porcentaje_iva"] is not None and not (pu < 0):
                        sync_iva = 0.0 if sync_sin_iva else float(lf["porcentaje_iva"])
                    if lf["porcentaje_irpf"] is not None and not (pu < 0):
                        sync_irpf = float(lf["porcentaje_irpf"])

                    cursor.execute("""
                        INSERT INTO presupuesto_lineas (opcion_id, descripcion, detalle_material, cantidad, precio_unitario, total, orden, descuento_id, precio_unitario_original)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        opcion_target_id,
                        lf["descripcion"] or "Producto",
                        lf["detalle_material"] or "",
                        cant,
                        pu_efectivo,
                        tot_l,
                        idx_l,
                        lf["descuento_id"],
                        lf["precio_unitario_original"]
                    ))

                subtotal_op = round2(subtotal_op)
                cursor.execute("UPDATE presupuesto_opciones SET subtotal = ?, total = ? WHERE id = ?", (subtotal_op, subtotal_op, opcion_target_id))

            cursor.execute("UPDATE facturas SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (factura_id_a_desvincular,))
            crear_version_factura(conn, factura_id_a_desvincular, motivo=f"Desvinculada y movida a papelera: sus líneas y modificaciones fueron sincronizadas en el presupuesto {p['numero_presupuesto']} al reabrirlo a Borrador")
            # Purgar archivo PDF activo de disco
            if fac_row:
                eliminar_pdf_factura(fac_row["numero_factura"], fac_row["fecha_emision"], sin_iva=bool(fac_row["sin_iva"]))

        campos_update = ["estado = ?", "opcion_aprobada_id = ?", "factura_id = ?", "updated_at = CURRENT_TIMESTAMP"]
        valores_update = [data.estado, nueva_opcion_aprobada, nuevo_factura_id]

        if data.porcentaje_iva is not None:
            campos_update.append("porcentaje_iva = ?")
            valores_update.append(data.porcentaje_iva)
        elif sync_iva is not None:
            campos_update.append("porcentaje_iva = ?")
            valores_update.append(sync_iva)

        if data.porcentaje_irpf is not None:
            campos_update.append("porcentaje_irpf = ?")
            valores_update.append(data.porcentaje_irpf)
        elif sync_irpf is not None:
            campos_update.append("porcentaje_irpf = ?")
            valores_update.append(sync_irpf)

        if data.sin_iva is not None:
            campos_update.append("sin_iva = ?")
            valores_update.append(1 if data.sin_iva else 0)
        elif sync_sin_iva is not None:
            campos_update.append("sin_iva = ?")
            valores_update.append(1 if sync_sin_iva else 0)

        valores_update.append(id)
        cursor.execute(
            f"UPDATE presupuestos SET {', '.join(campos_update)} WHERE id = ?",
            valores_update
        )
        motivo_default = (
            f"Reabierto a Borrador absorbiendo modificaciones de factura {factura_num} (anterior: {p['estado']})"
            if (data.estado == "Borrador" and factura_absorbida and factura_num)
            else (
                f"Reabierto a Borrador para modificación (anterior: {p['estado']})"
                if data.estado == "Borrador" and p["estado"] in ("Aceptado", "Facturado")
                else f"Estado cambiado a {data.estado}"
            )
        )
        motivo_version = data.motivo or motivo_default
        crear_version_presupuesto(conn, id, motivo=motivo_version)
        return {
            "message": f"Estado actualizado a {data.estado}",
            "estado": data.estado,
            "opcion_aprobada_id": nueva_opcion_aprobada,
            "factura_absorbida": factura_absorbida
        }


@router.delete("/{id}")
def eliminar_presupuesto(id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, estado, factura_id FROM presupuestos WHERE id = ? AND is_deleted = 0", (id,))
        row = cursor.fetchone()
        if not row:
            raise NotFoundError("Presupuesto no encontrado")
        if row["factura_id"]:
            raise BusinessRuleError("No se puede eliminar un presupuesto que ya ha sido convertido en factura.")

        cursor.execute("UPDATE presupuestos SET is_deleted = 1, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
    return {"message": "Presupuesto eliminado correctamente", "id": id}


@router.post("/preview-pdf")
def previsualizar_pdf_presupuesto(data: PresupuestoPreviewRequest):
    config = get_configuracion()
    cliente_nombre = data.cliente_nombre or ""
    if data.cliente_id and not cliente_nombre:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT razon_social FROM clientes WHERE id = ? AND is_deleted = 0", (data.cliente_id,))
            row = cursor.fetchone()
            if row:
                cliente_nombre = row["razon_social"]

    opciones_dict = []
    for idx_op, op in enumerate(data.opciones, 1):
        lineas_dict = []
        tot_op = 0.0
        for idx_l, l in enumerate(op.lineas, 1):
            cant = float(l.cantidad) if l.cantidad is not None else 1.0
            pu = float(l.precio_unitario) if l.precio_unitario is not None else 0.0
            tot_l = round2(cant * pu)
            tot_op += tot_l
            lineas_dict.append({
                "descripcion": l.descripcion or f"Producto {idx_l}",
                "detalle_material": l.detalle_material or "",
                "cantidad": cant,
                "total": tot_l
            })
        opciones_dict.append({
            "nombre_opcion": op.nombre_opcion or f"Opción {idx_op}",
            "total": tot_op,
            "lineas": lineas_dict
        })

    if not opciones_dict:
        opciones_dict = [{
            "nombre_opcion": "Opción 1",
            "total": 0.0,
            "lineas": [{"descripcion": "Producto", "detalle_material": "", "cantidad": 1, "total": 0.0}]
        }]

    dict_presupuesto = {
        "numero_presupuesto": data.numero_presupuesto or "BORRADOR",
        "cliente_nombre": cliente_nombre,
        "fecha": data.fecha or date.today(),
        "titulo": data.titulo or "Presupuesto de Servicios",
        "subtitulo": data.subtitulo or "Precios para el diseño de invitaciones de boda",
        "condiciones_texto": data.condiciones_texto,
        "opciones": opciones_dict
    }

    pdf_bytes = generar_pdf_presupuesto(dict_presupuesto, config)
    filename = f"{dict_presupuesto['numero_presupuesto']}_preview.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/{id}/pdf")
def descargar_pdf_presupuesto(id: int, opcion_id: Optional[int] = Query(None), download: bool = Query(False)):
    detalle = obtener_detalle_presupuesto(id)
    config = get_configuracion()
    cliente_nombre = detalle.cliente.razon_social if detalle.cliente else ""

    opciones_a_incluir = detalle.opciones
    if opcion_id is not None:
        op_filtrada = [op for op in detalle.opciones if op.id == opcion_id]
        if op_filtrada:
            opciones_a_incluir = op_filtrada
    elif detalle.opcion_aprobada_id is not None:
        op_aprobada = [op for op in detalle.opciones if op.id == detalle.opcion_aprobada_id]
        if op_aprobada:
            opciones_a_incluir = op_aprobada

    dict_presupuesto = {
        "numero_presupuesto": detalle.numero_presupuesto,
        "cliente_nombre": cliente_nombre,
        "fecha": detalle.fecha,
        "titulo": detalle.titulo,
        "subtitulo": detalle.subtitulo or "Precios para el diseño de invitaciones de boda",
        "opciones": [
            {
                "nombre_opcion": op.nombre_opcion,
                "total": op.total,
                "lineas": [
                    {
                        "descripcion": l.descripcion,
                        "detalle_material": l.detalle_material,
                        "cantidad": l.cantidad,
                        "total": l.total
                    } for l in op.lineas
                ]
            } for op in opciones_a_incluir
        ]
    }

    pdf_bytes = generar_pdf_presupuesto(dict_presupuesto, config)
    filename = f"{detalle.numero_presupuesto}.pdf"

    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"{disposition}; filename={filename}"}
    )


@router.post("/{id}/convertir-factura")
@router.post("/{id}/convertir-a-factura")
def convertir_presupuesto_a_factura(id: int, req: PresupuestoConvertirFacturaRequest):
    detalle = obtener_detalle_presupuesto(id)

    if detalle.factura_id:
        raise BusinessRuleError(f"Este presupuesto ya fue convertido en la factura ID #{detalle.factura_id}.")

    opcion_elegida = next((op for op in detalle.opciones if op.id == req.opcion_id), None)
    if not opcion_elegida:
        raise NotFoundError("La opción seleccionada no pertenece a este presupuesto.")

    config = get_configuracion()
    if not es_configuracion_valida(config):
        raise BusinessRuleError(
            "No se puede emitir la factura: debe configurar los datos fiscales de la empresa (Nombre y NIF) en Configuración.",
            error_code="EMISOR_CONFIG_MISSING"
        )
    fecha_emision = req.fecha_emision or date.today()

    es_sin_iva = bool(req.sin_iva or (req.porcentaje_iva == 0))
    porcentaje_iva = 0.0 if es_sin_iva else (req.porcentaje_iva if req.porcentaje_iva is not None else 21.0)
    porcentaje_irpf = req.porcentaje_irpf if req.porcentaje_irpf is not None else 0.0

    lineas_insertar = []
    if req.tipo_facturacion == "anticipo":
        importe = req.importe_anticipo if req.importe_anticipo is not None else round2(opcion_elegida.total * 0.5)
        lineas_insertar.append({
            "descripcion": f"Pago inicial / Reserva según {detalle.titulo} ({detalle.numero_presupuesto} - {opcion_elegida.nombre_opcion})",
            "cantidad": 1.0,
            "precio_unitario": importe,
            "porcentaje_descuento": 0.0,
            "porcentaje_iva": 0.0 if es_sin_iva else porcentaje_iva,
            "porcentaje_irpf": porcentaje_irpf,
            "subtotal_base": importe
        })
    else:
        for l in opcion_elegida.lineas:
            sub = round2(l.cantidad * l.precio_unitario)
            lineas_insertar.append({
                "descripcion": l.descripcion,
                "detalle_material": l.detalle_material or None,
                "cantidad": l.cantidad,
                "precio_unitario": l.precio_unitario,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 0.0 if es_sin_iva else porcentaje_iva,
                "porcentaje_irpf": porcentaje_irpf,
                "subtotal_base": sub,
                "descuento_id": getattr(l, "descuento_id", None),
                "precio_unitario_original": getattr(l, "precio_unitario_original", None)
            })

    # Considerar descuento global de la opción si existe y no fue repartido por línea
    desc_val = opcion_elegida.descuento_valor or 0.0
    desc_imp = opcion_elegida.descuento_importe_total or 0.0
    desc_tipo = opcion_elegida.descuento_tipo

    # Si hay un descuento global en la opción y tipo_facturacion es 'total', aplicarlo sobre las líneas
    if req.tipo_facturacion != "anticipo" and desc_val > 0 and not any(l.get("descuento_id") for l in lineas_insertar):
        if desc_tipo == "porcentaje":
            for l in lineas_insertar:
                l["porcentaje_descuento"] = desc_val
                l["subtotal_base"] = round2(l["cantidad"] * l["precio_unitario"] * (1 - desc_val / 100))
        elif desc_tipo == "fijo" and desc_imp > 0:
            subtotal_bruto = sum(l["subtotal_base"] for l in lineas_insertar)
            if subtotal_bruto > 0:
                factor = max(0.0, (subtotal_bruto - desc_imp) / subtotal_bruto)
                for l in lineas_insertar:
                    l["subtotal_base"] = round2(l["subtotal_base"] * factor)

    # Calcular totales de factura con desglose proporcional de IVA e IRPF
    totales = calcular_totales_factura(lineas_insertar)
    base_imponible_total = totales["base_imponible_total"]
    iva_total = totales["iva_total"]
    irpf_total = totales["irpf_total"]
    total_factura = totales["total_factura"]
    sin_iva_flag = 1 if (es_sin_iva or iva_total == 0) else 0

    if req.serie:
        serie = req.serie
    elif sin_iva_flag:
        serie = config.get("serie_sin_iva") or "Factura Sin IVA Nº"
    else:
        serie = config.get("serie_defecto") or "Factura Nº"

    with db_connection() as conn:
        numero_factura, correlativo = generar_numero_factura(
            conn,
            serie=serie,
            fecha=fecha_emision,
            sin_iva=bool(sin_iva_flag)
        )
        serie_insert = serie
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO facturas (
                numero_factura, serie, correlativo, fecha_emision,
                cliente_id, base_imponible_total, iva_total, irpf_total,
                total_factura, sin_iva, estado, observaciones, emisor_snapshot,
                descuento_id, descuento_nombre, descuento_tipo, descuento_valor,
                descuento_importe_total, descuento_visible
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Emitida', ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            numero_factura,
            serie_insert,
            correlativo,
            fecha_emision.isoformat(),
            detalle.cliente_id,
            base_imponible_total,
            iva_total,
            irpf_total,
            total_factura,
            sin_iva_flag,
            None,
            json.dumps(config, ensure_ascii=False),
            opcion_elegida.descuento_id,
            opcion_elegida.descuento_nombre,
            opcion_elegida.descuento_tipo,
            opcion_elegida.descuento_valor or 0.0,
            opcion_elegida.descuento_importe_total or 0.0,
            1 if opcion_elegida.descuento_visible is not False else 0
        ))
        factura_id = cursor.lastrowid

        for l in lineas_insertar:
            cursor.execute("""
                INSERT INTO lineas_factura (
                    factura_id, descripcion, detalle_material, cantidad, precio_unitario,
                    porcentaje_descuento, porcentaje_iva, porcentaje_irpf, subtotal_base,
                    descuento_id, precio_unitario_original
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                factura_id,
                l["descripcion"],
                l.get("detalle_material"),
                l["cantidad"],
                l["precio_unitario"],
                l.get("porcentaje_descuento", 0.0),
                l["porcentaje_iva"],
                l["porcentaje_irpf"],
                l["subtotal_base"],
                l.get("descuento_id"),
                l.get("precio_unitario_original")
            ))

        # Actualizar presupuesto a Facturado y registrar la factura vinculada
        cursor.execute("""
            UPDATE presupuestos
            SET estado = 'Facturado', factura_id = ?, opcion_aprobada_id = ?,
                porcentaje_iva = ?, porcentaje_irpf = ?, sin_iva = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (factura_id, opcion_elegida.id, porcentaje_iva, porcentaje_irpf, sin_iva_flag, id))

        crear_version_factura(conn, factura_id, motivo=f"Generada desde presupuesto {detalle.numero_presupuesto}")
        crear_version_presupuesto(conn, id, motivo=f"Aprobada opción {opcion_elegida.nombre_opcion} y convertida a factura {numero_factura}")

    # Generar inmediatamente el archivo PDF oficial de la factura emitida
    pdf_path = get_pdf_output_path(numero_factura, fecha_emision, sin_iva=bool(sin_iva_flag))
    factura_dict = {
        "id": factura_id,
        "numero_factura": numero_factura,
        "serie": serie,
        "correlativo": correlativo,
        "fecha_emision": fecha_emision.isoformat(),
        "fecha_vencimiento": None,
        "cliente_id": detalle.cliente_id,
        "base_imponible_total": base_imponible_total,
        "iva_total": iva_total,
        "irpf_total": irpf_total,
        "total_factura": total_factura,
        "sin_iva": sin_iva_flag,
        "estado": "Emitida",
        "observaciones": None    
    }
    cliente_dict = {
        "razon_social": (detalle.cliente.razon_social if detalle.cliente else "Cliente"),
        "nif_cif": (detalle.cliente.nif_cif if detalle.cliente else None),
        "telefono": (detalle.cliente.telefono if detalle.cliente else "") or "",
        "email": (detalle.cliente.email if detalle.cliente else "") or "",
        "direccion": (detalle.cliente.direccion if detalle.cliente else "") or "",
        "ciudad": (detalle.cliente.ciudad if detalle.cliente else "") or "",
        "codigo_postal": (detalle.cliente.codigo_postal if detalle.cliente else "") or ""
    }
    with db_connection() as conn:
        cli_row = conn.execute("SELECT * FROM clientes WHERE id = ?", (detalle.cliente_id,)).fetchone()
        if cli_row:
            cliente_dict = dict(cli_row)

    generar_pdf_factura(factura_dict, lineas_insertar, cliente_dict, pdf_path, emisor_data=config)

    return {
        "message": "Presupuesto convertido a factura correctamente",
        "presupuesto_id": id,
        "factura_id": factura_id,
        "numero_factura": numero_factura,
        "total_factura": total_factura,
        "redirect_url": f"/api/facturas/{factura_id}/pdf"
    }


# --- Endpoints de Versiones y Papelera de Presupuestos ---

@router.get("/{id}/versiones")
def api_listar_versiones_presupuesto(id: int):
    return listar_versiones_presupuesto(id)


@router.get("/{id}/versiones/{numero_version}")
def api_obtener_version_presupuesto(id: int, numero_version: int):
    return obtener_detalle_version_presupuesto(id, numero_version)


@router.post("/{id}/versiones/{numero_version}/restaurar")
def api_restaurar_version_presupuesto(id: int, numero_version: int):
    return restaurar_version_presupuesto(id, numero_version)


@router.post("/{id}/restaurar")
def restaurar_presupuesto_papelera(id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT id, numero_presupuesto FROM presupuestos WHERE id = ? AND is_deleted = 1", (id,)).fetchone()
        if not row:
            raise NotFoundError("Presupuesto no encontrado en papelera")
        cursor.execute("UPDATE presupuestos SET is_deleted = 0, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
        crear_version_presupuesto(conn, id, motivo="Restaurado desde la papelera")
        return {"message": f"Presupuesto {row['numero_presupuesto']} recuperado correctamente"}


@router.delete("/{id}/destruir")
def destruir_presupuesto_definitivamente(id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT id, numero_presupuesto FROM presupuestos WHERE id = ?", (id,)).fetchone()
        if not row:
            raise NotFoundError("Presupuesto no encontrado")
        cursor.execute("DELETE FROM presupuestos WHERE id = ?", (id,))
        return {"message": f"Presupuesto {row['numero_presupuesto']} eliminado permanentemente"}
