import json
import sqlite3
from typing import Any
from app.database import db_connection, get_configuracion
from app.services.pdf_service import generar_numero_factura, generar_pdf_factura, get_pdf_output_path, eliminar_pdf_factura
from app.errors import NotFoundError


def crear_version_factura(conn: sqlite3.Connection, factura_id: int, motivo: str = "Modificación") -> int:
    """Crea una instantánea inmutable en factura_versiones para la factura indicada."""
    cursor = conn.cursor()
    row_f = cursor.execute("SELECT * FROM facturas WHERE id = ?", (factura_id,)).fetchone()
    if not row_f:
        return 0

    factura_dict = dict(row_f)
    row_lineas = cursor.execute(
        "SELECT * FROM lineas_factura WHERE factura_id = ? ORDER BY id ASC",
        (factura_id,)
    ).fetchall()
    lineas_list = [dict(l) for l in row_lineas]

    row_cli = None
    if factura_dict.get("cliente_id"):
        row_cli = cursor.execute(
            "SELECT id, razon_social, nif_cif, direccion, email, telefono FROM clientes WHERE id = ?",
            (factura_dict["cliente_id"],)
        ).fetchone()

    snapshot = {
        "factura": factura_dict,
        "lineas": lineas_list,
        "cliente": dict(row_cli) if row_cli else None
    }

    row_ver = cursor.execute(
        "SELECT COALESCE(MAX(numero_version), 0) + 1 FROM factura_versiones WHERE factura_id = ?",
        (factura_id,)
    ).fetchone()
    next_ver = row_ver[0] if row_ver else 1

    cursor.execute(
        """INSERT INTO factura_versiones 
           (factura_id, numero_version, motivo, snapshot_data, total_factura)
           VALUES (?, ?, ?, ?, ?)""",
        (factura_id, next_ver, motivo, json.dumps(snapshot, ensure_ascii=False), factura_dict.get("total_factura", 0.0))
    )
    return next_ver


def crear_version_presupuesto(conn: sqlite3.Connection, presupuesto_id: int, motivo: str = "Modificación") -> int:
    """Crea una instantánea inmutable en presupuesto_versiones para el presupuesto indicado."""
    cursor = conn.cursor()
    row_p = cursor.execute("SELECT * FROM presupuestos WHERE id = ?", (presupuesto_id,)).fetchone()
    if not row_p:
        return 0

    presupuesto_dict = dict(row_p)
    row_opciones = cursor.execute(
        "SELECT * FROM presupuesto_opciones WHERE presupuesto_id = ? ORDER BY orden ASC, id ASC",
        (presupuesto_id,)
    ).fetchall()

    opciones_list = []
    total_estimado = 0.0
    for op in row_opciones:
        op_dict = dict(op)
        row_lineas = cursor.execute(
            "SELECT * FROM presupuesto_lineas WHERE opcion_id = ? ORDER BY orden ASC, id ASC",
            (op["id"],)
        ).fetchall()
        op_dict["lineas"] = [dict(l) for l in row_lineas]
        opciones_list.append(op_dict)
        op_total = op_dict.get("total") or 0.0
        if op_dict["id"] == presupuesto_dict.get("opcion_aprobada_id") or op_total > total_estimado:
            total_estimado = op_total

    row_cli = None
    if presupuesto_dict.get("cliente_id"):
        row_cli = cursor.execute(
            "SELECT id, razon_social, nif_cif, direccion, email, telefono FROM clientes WHERE id = ?",
            (presupuesto_dict["cliente_id"],)
        ).fetchone()

    snapshot = {
        "presupuesto": presupuesto_dict,
        "opciones": opciones_list,
        "cliente": dict(row_cli) if row_cli else None
    }

    row_ver = cursor.execute(
        "SELECT COALESCE(MAX(numero_version), 0) + 1 FROM presupuesto_versiones WHERE presupuesto_id = ?",
        (presupuesto_id,)
    ).fetchone()
    next_ver = row_ver[0] if row_ver else 1

    cursor.execute(
        """INSERT INTO presupuesto_versiones
           (presupuesto_id, numero_version, motivo, snapshot_data, total_estimado)
           VALUES (?, ?, ?, ?, ?)""",
        (presupuesto_id, next_ver, motivo, json.dumps(snapshot, ensure_ascii=False), total_estimado)
    )
    return next_ver


def listar_versiones_factura(factura_id: int) -> list[dict[str, Any]]:
    """Obtiene el historial cronológico de versiones de una factura."""
    with db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """SELECT id, factura_id, numero_version, motivo, snapshot_data, total_factura, created_at
               FROM factura_versiones
               WHERE factura_id = ?
               ORDER BY numero_version DESC""",
            (factura_id,)
        ).fetchall()

        if not rows:
            # Si la factura existe pero aún no tiene versiones registradas, crear versión inicial
            f_exist = cursor.execute("SELECT id FROM facturas WHERE id = ?", (factura_id,)).fetchone()
            if f_exist:
                try:
                    crear_version_factura(conn, factura_id, motivo="Estado inicial del documento")
                    rows = cursor.execute(
                        """SELECT id, factura_id, numero_version, motivo, snapshot_data, total_factura, created_at
                           FROM factura_versiones
                           WHERE factura_id = ?
                           ORDER BY numero_version DESC""",
                        (factura_id,)
                    ).fetchall()
                except Exception:
                    pass

        resultado = []
        for r in rows:
            data = json.loads(r["snapshot_data"])
            lineas = data.get("lineas", [])
            resultado.append({
                "id": r["id"],
                "factura_id": r["factura_id"],
                "numero_version": r["numero_version"],
                "motivo": r["motivo"],
                "total_factura": r["total_factura"],
                "created_at": r["created_at"],
                "num_lineas": len(lineas),
                "cliente": data.get("cliente")
            })
        return resultado


def obtener_detalle_version_factura(factura_id: int, numero_version: int) -> dict[str, Any]:
    """Obtiene el detalle completo de una versión específica de factura."""
    with db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            """SELECT id, factura_id, numero_version, motivo, snapshot_data, total_factura, created_at
               FROM factura_versiones
               WHERE factura_id = ? AND numero_version = ?""",
            (factura_id, numero_version)
        ).fetchone()
        if not row:
            raise NotFoundError(f"Versión v{numero_version} de la factura no encontrada")

        parsed = json.loads(row["snapshot_data"])
        return {
            "id": row["id"],
            "factura_id": row["factura_id"],
            "numero_version": row["numero_version"],
            "motivo": row["motivo"],
            "total_factura": row["total_factura"],
            "created_at": row["created_at"],
            "snapshot": parsed
        }


def restaurar_version_factura(factura_id: int, numero_version: int) -> dict[str, Any]:
    """Restaura una factura al estado de una versión previa, gestionando régimen de IVA, numeración y archivos PDF."""
    with db_connection() as conn:
        cursor = conn.cursor()

        # 1. Obtener la factura actual en BD
        factura_actual = cursor.execute(
            "SELECT * FROM facturas WHERE id = ?",
            (factura_id,)
        ).fetchone()
        if not factura_actual:
            raise NotFoundError(f"Factura {factura_id} no encontrada")

        # 2. Obtener la versión a restaurar
        row_v = cursor.execute(
            "SELECT snapshot_data FROM factura_versiones WHERE factura_id = ? AND numero_version = ?",
            (factura_id, numero_version)
        ).fetchone()
        if not row_v:
            raise NotFoundError(f"Versión v{numero_version} no encontrada para restaurar")

        snapshot = json.loads(row_v["snapshot_data"])
        f_data = snapshot["factura"]
        lineas_data = snapshot["lineas"]

        antiguo_sin_iva = bool(factura_actual["sin_iva"])
        nuevo_sin_iva = bool(f_data.get("sin_iva", 0))
        cambio_regimen = (antiguo_sin_iva != nuevo_sin_iva)

        config = get_configuracion()
        fecha_emision = f_data.get("fecha_emision")

        # 3. Determinar número, serie y correlativo
        # Si la versión snapshot ya tenía su propio número (por ejemplo, si v1 era con IVA y v2 era sin IVA,
        # restaurar a v1 puede recuperar el número que tenía v1 si no colisiona, o si cambió de régimen,
        # asegurar que pertenezca a la serie correcta).
        numero_version_snap = f_data.get("numero_factura")
        serie_version_snap = f_data.get("serie")
        correlativo_version_snap = f_data.get("correlativo")

        if cambio_regimen:
            # Comprobar si el número original de la versión a restaurar ya tenía la serie correcta
            serie_esperada = (config.get("serie_sin_iva") or "Factura Sin IVA Nº") if nuevo_sin_iva else (config.get("serie_defecto") or "Factura Nº")
            
            # Si el snapshot tenía un número de esa serie y no colisiona con otra factura distinta
            usar_snap_num = False
            if numero_version_snap and serie_version_snap == serie_esperada:
                colision = cursor.execute(
                    "SELECT id FROM facturas WHERE numero_factura = ? AND id != ?",
                    (numero_version_snap, factura_id)
                ).fetchone()
                if not colision:
                    usar_snap_num = True

            if usar_snap_num:
                nuevo_numero = numero_version_snap
                nueva_serie = serie_version_snap
                nuevo_correlativo = correlativo_version_snap
            else:
                nuevo_numero, nuevo_correlativo = generar_numero_factura(
                    conn,
                    serie=serie_esperada,
                    fecha=fecha_emision,
                    sin_iva=nuevo_sin_iva
                )
                nueva_serie = serie_esperada
        else:
            # Mismo régimen: mantenemos el número actual de la factura a menos que sea necesario
            nuevo_numero = factura_actual["numero_factura"]
            nueva_serie = factura_actual["serie"]
            nuevo_correlativo = factura_actual["correlativo"]

        # 4. Actualizar cabecera de la factura en BD
        cursor.execute(
            """UPDATE facturas SET
                numero_factura = ?,
                serie = ?,
                correlativo = ?,
                fecha_emision = ?,
                fecha_vencimiento = ?,
                cliente_id = ?,
                base_imponible_total = ?,
                iva_total = ?,
                irpf_total = ?,
                total_factura = ?,
                sin_iva = ?,
                descuento_id = ?,
                descuento_nombre = ?,
                descuento_tipo = ?,
                descuento_valor = ?,
                descuento_importe_total = ?,
                descuento_visible = ?,
                observaciones = ?,
                emisor_snapshot = ?,
                updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                nuevo_numero,
                nueva_serie,
                nuevo_correlativo,
                fecha_emision,
                f_data.get("fecha_vencimiento"),
                f_data.get("cliente_id"),
                f_data.get("base_imponible_total", 0.0),
                f_data.get("iva_total", 0.0),
                f_data.get("irpf_total", 0.0),
                f_data.get("total_factura", 0.0),
                1 if nuevo_sin_iva else 0,
                f_data.get("descuento_id"),
                f_data.get("descuento_nombre"),
                f_data.get("descuento_tipo"),
                f_data.get("descuento_valor", 0.0),
                f_data.get("descuento_importe_total", 0.0),
                f_data.get("descuento_visible", 1),
                f_data.get("observaciones"),
                f_data.get("emisor_snapshot"),
                factura_id
            )
        )

        # 5. Reemplazar líneas
        cursor.execute("DELETE FROM lineas_factura WHERE factura_id = ?", (factura_id,))
        for l in lineas_data:
            cursor.execute(
                """INSERT INTO lineas_factura
                   (factura_id, producto_id, descripcion, detalle_material, cantidad, precio_unitario,
                    porcentaje_descuento, porcentaje_iva, porcentaje_irpf, subtotal_base,
                    descuento_id, precio_unitario_original)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    factura_id,
                    l.get("producto_id"),
                    l.get("descripcion", ""),
                    l.get("detalle_material"),
                    l.get("cantidad", 1.0),
                    l.get("precio_unitario", 0.0),
                    l.get("porcentaje_descuento", 0.0),
                    l.get("porcentaje_iva", 21.0),
                    l.get("porcentaje_irpf", 0.0),
                    l.get("subtotal_base", 0.0),
                    l.get("descuento_id"),
                    l.get("precio_unitario_original")
                )
            )

        # 6. Registrar nueva versión de reversión
        regimen_str = "Sin IVA" if nuevo_sin_iva else "Con IVA"
        motivo_version = (
            f"Restaurada a partir de versión v{numero_version} (cambio a {regimen_str}: {nuevo_numero})"
            if cambio_regimen else
            f"Restaurada a partir de versión v{numero_version}"
        )
        nueva_version = crear_version_factura(conn, factura_id, motivo=motivo_version)

        # 7. Gestión de archivos PDF: eliminar el anterior si cambió régimen, fecha o número
        antigua_fecha = str(factura_actual["fecha_emision"])[:10]
        nueva_fecha = str(fecha_emision)[:10]
        if antigua_fecha != nueva_fecha or cambio_regimen or factura_actual["numero_factura"] != nuevo_numero:
            eliminar_pdf_factura(factura_actual["numero_factura"], factura_actual["fecha_emision"], sin_iva=antiguo_sin_iva)

        # Obtener los datos frescos de la factura y cliente para el PDF
        factura_actualizada = dict(cursor.execute("SELECT * FROM facturas WHERE id = ?", (factura_id,)).fetchone())
        cli_dict = snapshot.get("cliente")
        if not cli_dict and factura_actualizada.get("cliente_id"):
            cli_row = cursor.execute("SELECT * FROM clientes WHERE id = ?", (factura_actualizada["cliente_id"],)).fetchone()
            cli_dict = dict(cli_row) if cli_row else {}

        pdf_path = get_pdf_output_path(nuevo_numero, fecha_emision, sin_iva=nuevo_sin_iva)
        emisor_data = None
        if factura_actualizada.get("emisor_snapshot"):
            try:
                emisor_data = json.loads(factura_actualizada["emisor_snapshot"])
            except Exception:
                pass
        if not emisor_data:
            emisor_data = config

        generar_pdf_factura(factura_actualizada, lineas_data, cli_dict or {}, pdf_path, emisor_data=emisor_data)

        return {
            "message": f"Factura restaurada exitosamente a partir de la versión v{numero_version}",
            "nueva_version": nueva_version,
            "numero_factura": nuevo_numero,
            "pdf_path": str(pdf_path)
        }


def listar_versiones_presupuesto(presupuesto_id: int) -> list[dict[str, Any]]:
    """Obtiene el historial cronológico de versiones de un presupuesto."""
    with db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """SELECT id, presupuesto_id, numero_version, motivo, snapshot_data, total_estimado, created_at
               FROM presupuesto_versiones
               WHERE presupuesto_id = ?
               ORDER BY numero_version DESC""",
            (presupuesto_id,)
        ).fetchall()

        if not rows:
            # Si el presupuesto existe pero aún no tiene versiones registradas, crear versión inicial
            p_exist = cursor.execute("SELECT id FROM presupuestos WHERE id = ?", (presupuesto_id,)).fetchone()
            if p_exist:
                try:
                    crear_version_presupuesto(conn, presupuesto_id, motivo="Estado inicial del documento")
                    rows = cursor.execute(
                        """SELECT id, presupuesto_id, numero_version, motivo, snapshot_data, total_estimado, created_at
                           FROM presupuesto_versiones
                           WHERE presupuesto_id = ?
                           ORDER BY numero_version DESC""",
                        (presupuesto_id,)
                    ).fetchall()
                except Exception:
                    pass

        resultado = []
        for r in rows:
            data = json.loads(r["snapshot_data"])
            opciones = data.get("opciones", [])
            total_lineas = sum(len(op.get("lineas", [])) for op in opciones)
            resultado.append({
                "id": r["id"],
                "presupuesto_id": r["presupuesto_id"],
                "numero_version": r["numero_version"],
                "motivo": r["motivo"],
                "total_estimado": r["total_estimado"],
                "created_at": r["created_at"],
                "num_opciones": len(opciones),
                "num_lineas": total_lineas,
                "cliente": data.get("cliente")
            })
        return resultado


def obtener_detalle_version_presupuesto(presupuesto_id: int, numero_version: int) -> dict[str, Any]:
    """Obtiene el detalle completo de una versión específica de presupuesto."""
    with db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            """SELECT id, presupuesto_id, numero_version, motivo, snapshot_data, total_estimado, created_at
               FROM presupuesto_versiones
               WHERE presupuesto_id = ? AND numero_version = ?""",
            (presupuesto_id, numero_version)
        ).fetchone()
        if not row:
            raise NotFoundError(f"Versión v{numero_version} del presupuesto no encontrada")

        parsed = json.loads(row["snapshot_data"])
        return {
            "id": row["id"],
            "presupuesto_id": row["presupuesto_id"],
            "numero_version": row["numero_version"],
            "motivo": row["motivo"],
            "total_estimado": row["total_estimado"],
            "created_at": row["created_at"],
            "snapshot": parsed
        }


def restaurar_version_presupuesto(presupuesto_id: int, numero_version: int) -> dict[str, Any]:
    """Restaura un presupuesto al estado exacto de una versión previa, creando una nueva versión de registro."""
    with db_connection() as conn:
        cursor = conn.cursor()
        row_v = cursor.execute(
            "SELECT snapshot_data FROM presupuesto_versiones WHERE presupuesto_id = ? AND numero_version = ?",
            (presupuesto_id, numero_version)
        ).fetchone()
        if not row_v:
            raise NotFoundError(f"Versión v{numero_version} no encontrada para restaurar")

        snapshot = json.loads(row_v["snapshot_data"])
        p_data = snapshot["presupuesto"]
        opciones_data = snapshot["opciones"]

        # Obtener presupuesto actual para gestionar posibles desvinculaciones
        curr_p = cursor.execute(
            "SELECT estado, factura_id, numero_presupuesto FROM presupuestos WHERE id = ?",
            (presupuesto_id,)
        ).fetchone()

        target_estado = p_data.get("estado", "Borrador")
        target_factura_id = p_data.get("factura_id")

        # Si el presupuesto actual tenía factura y la versión a restaurar es Borrador (o no tenía factura):
        if curr_p and curr_p["factura_id"] and (target_estado == "Borrador" or not target_factura_id):
            fac_id = curr_p["factura_id"]
            target_factura_id = None
            fac_row = cursor.execute("SELECT numero_factura, fecha_emision, sin_iva FROM facturas WHERE id = ?", (fac_id,)).fetchone()
            if fac_row:
                eliminar_pdf_factura(fac_row["numero_factura"], fac_row["fecha_emision"], sin_iva=bool(fac_row["sin_iva"]))
            cursor.execute("UPDATE facturas SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (fac_id,))
            crear_version_factura(conn, fac_id, motivo=f"Cancelada y movida a papelera por restauración del presupuesto {curr_p['numero_presupuesto']} a versión v{numero_version}")

        # 1. Borrar opciones actuales (cascada a presupuesto_lineas)
        cursor.execute("DELETE FROM presupuesto_opciones WHERE presupuesto_id = ?", (presupuesto_id,))

        # 2. Reinsertar opciones y líneas construyendo mapa de IDs (incluyendo campos de descuento)
        id_map = {}
        for orden_op, op in enumerate(opciones_data, 1):
            cursor.execute(
                """INSERT INTO presupuesto_opciones
                   (presupuesto_id, nombre_opcion, descripcion_corta, orden, subtotal, total,
                    descuento_id, descuento_nombre, descuento_tipo, descuento_valor, descuento_importe_total, descuento_visible)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    presupuesto_id,
                    op.get("nombre_opcion", f"Opción {orden_op}"),
                    op.get("descripcion_corta"),
                    op.get("orden", orden_op),
                    op.get("subtotal", 0.0),
                    op.get("total", 0.0),
                    op.get("descuento_id"),
                    op.get("descuento_nombre"),
                    op.get("descuento_tipo"),
                    op.get("descuento_valor", 0.0),
                    op.get("descuento_importe_total", 0.0),
                    op.get("descuento_visible", 1)
                )
            )
            nueva_op_id = cursor.lastrowid
            if "id" in op:
                id_map[op["id"]] = nueva_op_id

            for orden_l, l in enumerate(op.get("lineas", []), 1):
                cursor.execute(
                    """INSERT INTO presupuesto_lineas
                       (opcion_id, descripcion, detalle_material, cantidad, precio_unitario, total, orden,
                        descuento_id, precio_unitario_original)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        nueva_op_id,
                        l.get("descripcion", ""),
                        l.get("detalle_material"),
                        l.get("cantidad", 1.0),
                        l.get("precio_unitario", 0.0),
                        l.get("total", 0.0),
                        l.get("orden", orden_l),
                        l.get("descuento_id"),
                        l.get("precio_unitario_original")
                    )
                )

        # 3. Determinar opción aprobada
        target_opcion_aprobada = None
        if target_estado in ["Aceptado", "Facturado"] and p_data.get("opcion_aprobada_id"):
            target_opcion_aprobada = id_map.get(p_data.get("opcion_aprobada_id"))

        # 4. Actualizar cabecera con impuestos, régimen sin_iva, descuentos, estado y opción aprobada
        cursor.execute(
            """UPDATE presupuestos SET
                cliente_id = ?,
                fecha = ?,
                fecha_validez = ?,
                titulo = ?,
                subtitulo = ?,
                porcentaje_iva = ?,
                porcentaje_irpf = ?,
                sin_iva = ?,
                descuento_id = ?,
                descuento_nombre = ?,
                descuento_tipo = ?,
                descuento_valor = ?,
                descuento_importe_total = ?,
                descuento_visible = ?,
                estado = ?,
                observaciones = ?,
                opcion_aprobada_id = ?,
                factura_id = ?,
                updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                p_data.get("cliente_id"),
                p_data.get("fecha"),
                p_data.get("fecha_validez"),
                p_data.get("titulo", "Presupuesto"),
                p_data.get("subtitulo", ""),
                p_data.get("porcentaje_iva", 21.0),
                p_data.get("porcentaje_irpf", 0.0),
                p_data.get("sin_iva", 0),
                p_data.get("descuento_id"),
                p_data.get("descuento_nombre"),
                p_data.get("descuento_tipo"),
                p_data.get("descuento_valor", 0.0),
                p_data.get("descuento_importe_total", 0.0),
                p_data.get("descuento_visible", 1),
                target_estado,
                p_data.get("observaciones"),
                target_opcion_aprobada,
                target_factura_id,
                presupuesto_id
            )
        )

        # 5. Registrar nueva versión de reversión
        nueva_version = crear_version_presupuesto(
            conn,
            presupuesto_id,
            motivo=f"Restaurado a partir de versión v{numero_version} (Estado: {target_estado})"
        )

        return {
            "message": f"Presupuesto restaurado exitosamente a partir de la versión v{numero_version}",
            "nueva_version": nueva_version
        }
