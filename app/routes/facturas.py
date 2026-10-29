import json
import math
from typing import Optional
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse


from app.database import db_connection, get_configuracion, es_configuracion_valida
from app.models import (
    FacturaCreate, FacturaUpdate, FacturaUpdateFull,
    FacturaResponse, ESTADOS_FACTURA_VALIDOS
)
from app.errors import NotFoundError, BusinessRuleError
from app.services.pdf_service import (
    generar_numero_factura, generar_pdf_factura,
    calcular_totales_linea, calcular_totales_factura,
    get_pdf_output_path, eliminar_pdf_factura
)
from app.services.backup_service import crear_snapshot
from app.services.version_service import (
    crear_version_factura, listar_versiones_factura,
    obtener_detalle_version_factura, restaurar_version_factura
)

router = APIRouter()


def round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


@router.get("/facturas")
def listar_facturas(
    response: Response,
    q: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    sin_iva: Optional[bool] = Query(None, description="Filtrar por facturas sin IVA (True) o con IVA (False)"),
    cliente_id: Optional[int] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    incluir_eliminadas: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    paginated: bool = Query(False, description="Devolver respuesta paginada estructurada")
):
    with db_connection() as conn:
        conditions = []
        params = []

        if not incluir_eliminadas:
            conditions.append("f.is_deleted = 0")

        if sin_iva is not None:
            if sin_iva:
                conditions.append("(f.sin_iva = 1 OR f.iva_total = 0)")
            else:
                conditions.append("(f.iva_total > 0 AND (f.sin_iva = 0 OR f.sin_iva IS NULL))")

        if estado:
            if estado == "SIN_IVA":
                conditions.append("(f.sin_iva = 1 OR f.iva_total = 0)")
            elif estado == "CON_IVA":
                conditions.append("(f.iva_total > 0 AND (f.sin_iva = 0 OR f.sin_iva IS NULL))")
            else:
                conditions.append("f.estado = ?")
                params.append(estado)

        if cliente_id:
            conditions.append("f.cliente_id = ?")
            params.append(cliente_id)

        if fecha_desde:
            conditions.append("f.fecha_emision >= ?")
            params.append(str(fecha_desde))

        if fecha_hasta:
            conditions.append("f.fecha_emision <= ?")
            params.append(str(fecha_hasta))

        if q:
            conditions.append("(f.numero_factura LIKE ? OR c.razon_social LIKE ? OR c.nif_cif LIKE ? OR c.telefono LIKE ? OR c.email LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term, term, term, term])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_query = f"""
            SELECT COUNT(*)
            FROM facturas f
            LEFT JOIN clientes c ON f.cliente_id = c.id
            {where_clause}
        """
        total = conn.execute(count_query, params).fetchone()[0]
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        offset = (page - 1) * page_size
        query = f"""
            SELECT f.*, c.razon_social as cliente_razon_social, c.nif_cif as cliente_nif_cif,
                   c.telefono as cliente_telefono, c.email as cliente_email
            FROM facturas f
            LEFT JOIN clientes c ON f.cliente_id = c.id
            {where_clause}
            ORDER BY f.fecha_emision DESC, f.correlativo DESC
            LIMIT ? OFFSET ?
        """
        query_params = list(params) + [page_size, offset]
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


@router.get("/facturas/{factura_id}", response_model=FacturaResponse)
def obtener_factura(factura_id: int):
    with db_connection() as conn:
        row = conn.execute(
            """SELECT f.*, c.razon_social as cliente_razon_social, c.nif_cif as cliente_nif_cif,
                      c.telefono as cliente_telefono, c.email as cliente_email,
                      c.direccion as cliente_direccion, c.ciudad as cliente_ciudad,
                      c.provincia as cliente_provincia, c.forma_pago_defecto as cliente_forma_pago
            FROM facturas f
            LEFT JOIN clientes c ON f.cliente_id = c.id
            WHERE f.id = ? AND f.is_deleted = 0""",
            (factura_id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Factura no encontrada")

        factura = dict(row)
        # Get lines
        lineas = conn.execute(
            "SELECT * FROM lineas_factura WHERE factura_id = ?",
            (factura_id,)
        ).fetchall()
        factura['lineas'] = [dict(l) for l in lineas]
        return factura


@router.post("/facturas", status_code=201)
def crear_factura(factura: FacturaCreate):
    with db_connection() as conn:
        # Verify client exists
        cliente = conn.execute(
            "SELECT * FROM clientes WHERE id = ? AND is_deleted = 0",
            (factura.cliente_id,)
        ).fetchone()
        if not cliente:
            raise NotFoundError("El cliente seleccionado no existe o ha sido eliminado")

        # Verify company configuration is valid
        config = get_configuracion()
        if not es_configuracion_valida(config):
            raise BusinessRuleError(
                "No se puede emitir la factura: debe configurar los datos fiscales de la empresa (Nombre y NIF) en Configuración.",
                error_code="EMISOR_CONFIG_MISSING"
            )

        # Prepare lines and calculate totals
        es_sin_iva = bool(factura.sin_iva)
        lineas_data = [l.model_dump() for l in factura.lineas]
        if es_sin_iva:
            for ld in lineas_data:
                ld['porcentaje_iva'] = 0.0
        totales = calcular_totales_factura(lineas_data)
        sin_iva_flag = 1 if (es_sin_iva or totales['iva_total'] == 0) else 0

        # Generar número correlativo diferenciado según régimen de IVA (con IVA o sin IVA)
        if sin_iva_flag:
            serie = config.get("serie_sin_iva") or "Factura Sin IVA Nº"
        else:
            serie = config.get("serie_defecto") or "Factura Nº"

        numero_factura, correlativo = generar_numero_factura(
            conn,
            serie=serie,
            fecha=factura.fecha_emision,
            sin_iva=bool(sin_iva_flag)
        )

        # Snapshot emisor
        emisor_snapshot = json.dumps(config, ensure_ascii=False)

        desc_id = getattr(factura, 'descuento_id', None)
        desc_nom = getattr(factura, 'descuento_nombre', None)
        desc_tipo = getattr(factura, 'descuento_tipo', None)
        desc_val = float(getattr(factura, 'descuento_valor', 0.0) or 0.0)
        desc_imp = float(getattr(factura, 'descuento_importe_total', 0.0) or 0.0)
        desc_vis = 1 if (getattr(factura, 'descuento_visible', True) is not False) else 0

        # Insert invoice header
        cursor = conn.execute(
            """INSERT INTO facturas
            (numero_factura, serie, correlativo, fecha_emision, fecha_vencimiento,
             cliente_id, base_imponible_total, iva_total, irpf_total, total_factura,
             sin_iva, estado, observaciones, emisor_snapshot,
             descuento_id, descuento_nombre, descuento_tipo, descuento_valor,
             descuento_importe_total, descuento_visible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                numero_factura, serie, correlativo,
                str(factura.fecha_emision),
                str(factura.fecha_vencimiento) if factura.fecha_vencimiento else None,
                factura.cliente_id,
                totales['base_imponible_total'],
                totales['iva_total'],
                totales['irpf_total'],
                totales['total_factura'],
                sin_iva_flag,
                factura.estado,
                factura.observaciones,
                emisor_snapshot,
                desc_id, desc_nom, desc_tipo, desc_val, desc_imp, desc_vis
            )
        )
        factura_id = cursor.lastrowid

        # Insert lines
        for linea_data in lineas_data:
            totales_linea = calcular_totales_linea(linea_data)
            conn.execute(
                """INSERT INTO lineas_factura
                (factura_id, producto_id, descripcion, detalle_material, cantidad, precio_unitario,
                 porcentaje_descuento, porcentaje_iva, porcentaje_irpf, subtotal_base,
                 descuento_id, precio_unitario_original)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    factura_id,
                    linea_data.get('producto_id'),
                    linea_data['descripcion'].strip(),
                    linea_data.get('detalle_material') or None,
                    linea_data.get('cantidad', 1.0),
                    linea_data.get('precio_unitario', 0.0),
                    linea_data.get('porcentaje_descuento', 0.0),
                    0.0 if es_sin_iva else linea_data.get('porcentaje_iva', 21.0),
                    linea_data.get('porcentaje_irpf', 0.0),
                    totales_linea['subtotal_base'],
                    linea_data.get('descuento_id'),
                    linea_data.get('precio_unitario_original')
                )
            )

        # Generate PDF
        factura_db = conn.execute(
            "SELECT * FROM facturas WHERE id = ?", (factura_id,)
        ).fetchone()
        factura_dict = dict(factura_db)

        lineas_db = conn.execute(
            "SELECT * FROM lineas_factura WHERE factura_id = ?", (factura_id,)
        ).fetchall()
        lineas_list = [dict(l) for l in lineas_db]

        cliente_dict = dict(cliente)

        pdf_path = get_pdf_output_path(numero_factura, factura.fecha_emision, sin_iva=bool(sin_iva_flag))
        generar_pdf_factura(factura_dict, lineas_list, cliente_dict, pdf_path, emisor_data=config)

        # Registrar versión inicial (v1)
        crear_version_factura(conn, factura_id, motivo="Emisión inicial de factura")

    # Create automatic backup after invoice emission
    try:
        crear_snapshot(motivo=f"factura_{numero_factura.replace('-', '_')}")
    except Exception:
        pass  # Backup failure should not block invoice creation

    return {
        "id": factura_id,
        "numero_factura": numero_factura,
        "base_imponible_total": totales['base_imponible_total'],
        "iva_total": totales['iva_total'],
        "irpf_total": totales['irpf_total'],
        "total_factura": totales['total_factura'],
        "sin_iva": bool(sin_iva_flag),
        "descuento_id": desc_id,
        "descuento_nombre": desc_nom,
        "descuento_tipo": desc_tipo,
        "descuento_valor": desc_val,
        "descuento_importe_total": desc_imp,
        "descuento_visible": bool(desc_vis),
        "pdf_path": str(pdf_path),
        "message": "Factura creada y PDF generado correctamente"
    }


@router.get("/facturas/{factura_id}/pdf")
def descargar_pdf(factura_id: int, download: bool = Query(False)):
    with db_connection() as conn:
        factura = conn.execute(
            """SELECT f.*, c.razon_social, c.nif_cif, c.telefono, c.email, c.direccion, c.codigo_postal, c.ciudad, c.provincia
            FROM facturas f JOIN clientes c ON f.cliente_id = c.id
            WHERE f.id = ? AND f.is_deleted = 0""",
            (factura_id,)
        ).fetchone()
        if not factura:
            raise NotFoundError("Factura no encontrada")

        factura_dict = dict(factura)
        pdf_path = get_pdf_output_path(factura_dict['numero_factura'], factura_dict['fecha_emision'], sin_iva=bool(factura_dict.get('sin_iva')))

        lineas = conn.execute(
            "SELECT * FROM lineas_factura WHERE factura_id = ?",
            (factura_id,)
        ).fetchall()
        cliente = conn.execute(
            "SELECT * FROM clientes WHERE id = ?",
            (factura_dict['cliente_id'],)
        ).fetchone()

        emisor_data = None
        if factura_dict.get('emisor_snapshot'):
            try:
                emisor_data = json.loads(factura_dict['emisor_snapshot'])
            except Exception:
                pass
        if not emisor_data:
            emisor_data = get_configuracion()

        generar_pdf_factura(
            factura_dict,
            [dict(l) for l in lineas],
            dict(cliente) if cliente else {},
            pdf_path,
            emisor_data=emisor_data
        )

        return FileResponse(
            path=str(pdf_path),
            media_type='application/pdf',
            filename=f"{factura_dict['numero_factura']}.pdf",
            content_disposition_type="attachment" if download else "inline"
        )


@router.put("/facturas/{factura_id}")
def actualizar_factura(factura_id: int, data: FacturaUpdateFull):
    with db_connection() as conn:
        factura_existente = conn.execute(
            "SELECT * FROM facturas WHERE id = ? AND is_deleted = 0", (factura_id,)
        ).fetchone()
        if not factura_existente:
            raise NotFoundError("Factura no encontrada")

        cliente_id = data.cliente_id if data.cliente_id is not None else factura_existente['cliente_id']
        cliente = conn.execute(
            "SELECT * FROM clientes WHERE id = ? AND is_deleted = 0", (cliente_id,)
        ).fetchone()
        if not cliente:
            raise NotFoundError("El cliente seleccionado no existe o ha sido eliminado")

        fecha_emision = data.fecha_emision or factura_existente['fecha_emision']
        if isinstance(fecha_emision, str):
            fecha_emision = date.fromisoformat(fecha_emision)

        fecha_vencimiento = data.fecha_vencimiento if data.fecha_vencimiento is not None else factura_existente['fecha_vencimiento']
        if isinstance(fecha_vencimiento, str):
            fecha_vencimiento = date.fromisoformat(fecha_vencimiento)

        if fecha_vencimiento and fecha_emision and fecha_vencimiento < fecha_emision:
            raise BusinessRuleError("La fecha de vencimiento no puede ser anterior a la fecha de emisión")

        observaciones = data.observaciones if data.observaciones is not None else factura_existente['observaciones']
        estado = data.estado if data.estado is not None else factura_existente['estado']
        if estado not in ESTADOS_FACTURA_VALIDOS:
            raise BusinessRuleError(f"Estado '{estado}' no válido. Opciones: {sorted(ESTADOS_FACTURA_VALIDOS)}")

        es_sin_iva = data.sin_iva if data.sin_iva is not None else bool(factura_existente['sin_iva'])

        if data.lineas is not None:
            if len(data.lineas) == 0:
                raise BusinessRuleError("La factura debe contener al menos una línea")

            lineas_payload = [l.model_dump() for l in data.lineas]
            if es_sin_iva:
                for lp in lineas_payload:
                    lp['porcentaje_iva'] = 0.0
            else:
                for lp in lineas_payload:
                    if lp.get('porcentaje_iva') is None:
                        lp['porcentaje_iva'] = 21.0

            totales = calcular_totales_factura(lineas_payload)
            base_imponible_total = totales['base_imponible_total']
            iva_total = totales['iva_total']
            irpf_total = totales['irpf_total']
            total_factura = totales['total_factura']

            conn.execute("DELETE FROM lineas_factura WHERE factura_id = ?", (factura_id,))
            for idx, linea in enumerate(data.lineas, start=1):
                linea_data = linea.model_dump()
                totales_linea = calcular_totales_linea(linea_data)
                conn.execute(
                    """INSERT INTO lineas_factura (
                        factura_id, producto_id, descripcion, detalle_material, cantidad,
                        precio_unitario, porcentaje_descuento, porcentaje_iva,
                        porcentaje_irpf, subtotal_base, descuento_id, precio_unitario_original
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        factura_id,
                        linea_data.get('producto_id'),
                        linea.descripcion.strip(),
                        linea_data.get('detalle_material') or None,
                        linea.cantidad,
                        linea.precio_unitario,
                        linea_data.get('porcentaje_descuento', 0.0),
                        0.0 if es_sin_iva else (linea_data.get('porcentaje_iva') if linea_data.get('porcentaje_iva') is not None else 21.0),
                        linea_data.get('porcentaje_irpf', 0.0),
                        totales_linea['subtotal_base'],
                        linea_data.get('descuento_id'),
                        linea_data.get('precio_unitario_original')
                    )
                )
        else:
            base_imponible_total = factura_existente['base_imponible_total']
            iva_total = factura_existente['iva_total']
            irpf_total = factura_existente['irpf_total']
            total_factura = factura_existente['total_factura']

        sin_iva_flag = 1 if (es_sin_iva or iva_total == 0) else 0

        antiguo_sin_iva = bool(factura_existente['sin_iva'])
        nuevo_sin_iva = bool(sin_iva_flag)
        cambio_regimen = (antiguo_sin_iva != nuevo_sin_iva)

        config = get_configuracion()
        if cambio_regimen:
            if nuevo_sin_iva:
                nueva_serie = config.get("serie_sin_iva") or "Factura Sin IVA Nº"
            else:
                nueva_serie = config.get("serie_defecto") or "Factura Nº"

            nuevo_numero, nuevo_correlativo = generar_numero_factura(
                conn,
                serie=nueva_serie,
                fecha=fecha_emision,
                sin_iva=bool(nuevo_sin_iva)
            )
        else:
            nuevo_numero = factura_existente['numero_factura']
            nueva_serie = factura_existente['serie']
            nuevo_correlativo = factura_existente['correlativo']

        desc_id = data.descuento_id if data.descuento_id is not None else factura_existente['descuento_id']
        desc_nom = data.descuento_nombre if data.descuento_nombre is not None else factura_existente['descuento_nombre']
        desc_tipo = data.descuento_tipo if data.descuento_tipo is not None else factura_existente['descuento_tipo']
        desc_val = data.descuento_valor if data.descuento_valor is not None else (factura_existente['descuento_valor'] or 0.0)
        desc_imp = data.descuento_importe_total if data.descuento_importe_total is not None else (factura_existente['descuento_importe_total'] or 0.0)
        desc_vis = (1 if data.descuento_visible else 0) if data.descuento_visible is not None else (factura_existente['descuento_visible'] if factura_existente['descuento_visible'] is not None else 1)

        conn.execute(
            """UPDATE facturas SET
                numero_factura = ?,
                serie = ?,
                correlativo = ?,
                cliente_id = ?,
                fecha_emision = ?,
                fecha_vencimiento = ?,
                observaciones = ?,
                estado = ?,
                sin_iva = ?,
                base_imponible_total = ?,
                iva_total = ?,
                irpf_total = ?,
                total_factura = ?,
                descuento_id = ?,
                descuento_nombre = ?,
                descuento_tipo = ?,
                descuento_valor = ?,
                descuento_importe_total = ?,
                descuento_visible = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (
                nuevo_numero,
                nueva_serie,
                nuevo_correlativo,
                cliente_id,
                fecha_emision.isoformat() if hasattr(fecha_emision, 'isoformat') else str(fecha_emision),
                fecha_vencimiento.isoformat() if hasattr(fecha_vencimiento, 'isoformat') else (str(fecha_vencimiento) if fecha_vencimiento else None),
                observaciones,
                estado,
                sin_iva_flag,
                base_imponible_total,
                iva_total,
                irpf_total,
                total_factura,
                desc_id,
                desc_nom,
                desc_tipo,
                desc_val,
                desc_imp,
                desc_vis,
                factura_id
            )
        )

        factura_db = conn.execute("SELECT * FROM facturas WHERE id = ?", (factura_id,)).fetchone()
        factura_dict = dict(factura_db)
        lineas_db = conn.execute("SELECT * FROM lineas_factura WHERE factura_id = ?", (factura_id,)).fetchall()
        lineas_list = [dict(l) for l in lineas_db]
        cliente_dict = dict(cliente)

        # Si la fecha de emisión o el régimen fiscal cambiaron, la ruta del PDF cambiará.
        # Eliminamos el PDF en la ruta previa para evitar archivos huérfanos.
        antigua_fecha = str(factura_existente['fecha_emision'])[:10]
        nueva_fecha = str(fecha_emision)[:10]
        antiguo_sin_iva = bool(factura_existente['sin_iva'])
        nuevo_sin_iva = bool(factura_dict.get('sin_iva'))
        if antigua_fecha != nueva_fecha or cambio_regimen or factura_existente['numero_factura'] != factura_dict['numero_factura']:
            eliminar_pdf_factura(factura_existente['numero_factura'], factura_existente['fecha_emision'], sin_iva=antiguo_sin_iva)

        pdf_path = get_pdf_output_path(factura_dict['numero_factura'], fecha_emision, sin_iva=bool(factura_dict.get('sin_iva')))
        generar_pdf_factura(factura_dict, lineas_list, cliente_dict, pdf_path, emisor_data=config)

        # Registrar versión tras modificación
        regimen_str = "Sin IVA" if nuevo_sin_iva else "Con IVA"
        motivo_version = (
            f"Modificación de datos (cambio de régimen a {regimen_str}: {factura_dict['numero_factura']})"
            if cambio_regimen else "Modificación de datos y líneas"
        )
        crear_version_factura(conn, factura_id, motivo=motivo_version)

    try:
        crear_snapshot(motivo=f"actualizar_factura_{factura_dict['numero_factura'].replace('-', '_')}")
    except Exception:
        pass

    return {
        "id": factura_id,
        "numero_factura": factura_dict['numero_factura'],
        "total_factura": total_factura,
        "pdf_path": str(pdf_path),
        "message": "Factura actualizada y PDF regenerado correctamente"
    }


@router.put("/facturas/{factura_id}/estado")
def actualizar_estado(factura_id: int, update: FacturaUpdate):
    estados_validos = ['Borrador', 'Emitida', 'Pagada', 'Vencida', 'Anulada']
    if update.estado not in estados_validos:
        raise BusinessRuleError(f"Estado '{update.estado}' no válido. Opciones: {estados_validos}")

    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM facturas WHERE id = ? AND is_deleted = 0", (factura_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Factura no encontrada")

        conn.execute(
            "UPDATE facturas SET estado = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (update.estado, factura_id)
        )
        crear_version_factura(conn, factura_id, motivo=f"Cambio de estado a {update.estado}")
        return {"message": f"Estado actualizado a '{update.estado}'"}


@router.delete("/facturas/{factura_id}")
def eliminar_factura(factura_id: int):
    """Soft delete - never physically deletes the invoice from DB, but cleans its active PDF."""
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id, numero_factura, fecha_emision, sin_iva FROM facturas WHERE id = ? AND is_deleted = 0", (factura_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Factura no encontrada")
        conn.execute(
            "UPDATE facturas SET is_deleted = 1, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (factura_id,)
        )
        # Si había presupuestos vinculados a esta factura, desvincular o devolver a 'Aceptado'
        conn.execute(
            """UPDATE presupuestos
               SET factura_id = NULL, estado = 'Aceptado', updated_at = CURRENT_TIMESTAMP
               WHERE factura_id = ?""",
            (factura_id,)
        )
        # Eliminar el archivo PDF activo de disco
        eliminar_pdf_factura(existing['numero_factura'], existing['fecha_emision'], sin_iva=bool(existing['sin_iva']))
        return {"message": f"Factura {existing['numero_factura']} eliminada correctamente"}


# --- Endpoints de Versiones y Recuperación ---

@router.get("/facturas/{factura_id}/versiones")
def api_listar_versiones_factura(factura_id: int):
    return listar_versiones_factura(factura_id)


@router.get("/facturas/{factura_id}/versiones/{numero_version}")
def api_obtener_version_factura(factura_id: int, numero_version: int):
    return obtener_detalle_version_factura(factura_id, numero_version)


@router.post("/facturas/{factura_id}/versiones/{numero_version}/restaurar")
def api_restaurar_version_factura(factura_id: int, numero_version: int):
    return restaurar_version_factura(factura_id, numero_version)


@router.post("/facturas/{factura_id}/restaurar")
def restaurar_factura_papelera(factura_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute("SELECT * FROM facturas WHERE id = ? AND is_deleted = 1", (factura_id,)).fetchone()
        if not existing:
            raise NotFoundError("Factura no encontrada en papelera")
        cursor.execute("UPDATE facturas SET is_deleted = 0, deleted_con_cliente = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (factura_id,))
        crear_version_factura(conn, factura_id, motivo="Restaurada desde la papelera")

        # Regenerar inmediatamente el archivo PDF oficial en disco
        factura_dict = dict(existing)
        factura_dict['is_deleted'] = 0
        lineas = conn.execute("SELECT * FROM lineas_factura WHERE factura_id = ?", (factura_id,)).fetchall()
        cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (factura_dict['cliente_id'],)).fetchone()
        
        emisor_data = None
        if factura_dict.get('emisor_snapshot'):
            try:
                emisor_data = json.loads(factura_dict['emisor_snapshot'])
            except Exception:
                pass
        if not emisor_data:
            emisor_data = get_configuracion()

        pdf_path = get_pdf_output_path(factura_dict['numero_factura'], factura_dict['fecha_emision'], sin_iva=bool(factura_dict.get('sin_iva')))
        generar_pdf_factura(
            factura_dict,
            [dict(l) for l in lineas],
            dict(cliente) if cliente else {},
            pdf_path,
            emisor_data=emisor_data
        )

        return {"message": f"Factura {existing['numero_factura']} recuperada correctamente"}


@router.delete("/facturas/{factura_id}/destruir")
def destruir_factura_definitivamente(factura_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute("SELECT id, numero_factura, fecha_emision, sin_iva FROM facturas WHERE id = ?", (factura_id,)).fetchone()
        if not existing:
            raise NotFoundError("Factura no encontrada")
        cursor.execute("UPDATE presupuestos SET factura_id = NULL, estado = 'Aceptado', updated_at = CURRENT_TIMESTAMP WHERE factura_id = ?", (factura_id,))
        cursor.execute("DELETE FROM facturas WHERE id = ?", (factura_id,))

        # Eliminar el archivo PDF físico de disco si existiese
        eliminar_pdf_factura(existing['numero_factura'], existing['fecha_emision'], sin_iva=bool(existing['sin_iva']))

        return {"message": f"Factura {existing['numero_factura']} eliminada permanentemente"}
