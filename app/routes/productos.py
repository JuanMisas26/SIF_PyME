import math
from fastapi import APIRouter, Query, Response
from typing import Optional, Union
from app.database import db_connection
from app.models import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    calcular_precio_unitario_sugerido
)
from app.errors import NotFoundError, ConflictError

router = APIRouter()


def _cargar_hijos_producto(conn, producto_dict: dict) -> dict:
    """Carga los tramos de escalado por volumen y variantes para un producto."""
    pid = producto_dict["id"]
    esc_rows = conn.execute(
        "SELECT * FROM producto_escalados WHERE producto_id = ? ORDER BY cantidad_minima ASC",
        (pid,)
    ).fetchall()
    producto_dict["escalados"] = [dict(r) for r in esc_rows]

    var_rows = conn.execute(
        "SELECT * FROM producto_variantes WHERE producto_id = ? ORDER BY id ASC",
        (pid,)
    ).fetchall()
    producto_dict["variantes"] = [dict(r) for r in var_rows]
    return producto_dict


def _guardar_hijos_producto(conn, producto_id: int, escalados: list = None, variantes: list = None):
    """Inserta o sincroniza los tramos y variantes de un producto."""
    if escalados is not None:
        conn.execute("DELETE FROM producto_escalados WHERE producto_id = ?", (producto_id,))
        for esc in escalados:
            e_data = esc.model_dump() if hasattr(esc, "model_dump") else esc
            conn.execute(
                """INSERT INTO producto_escalados
                (producto_id, cantidad_minima, cantidad_maxima, precio_unitario)
                VALUES (?, ?, ?, ?)""",
                (producto_id,
                 float(e_data.get("cantidad_minima", 1.0)),
                 float(e_data["cantidad_maxima"]) if e_data.get("cantidad_maxima") is not None else None,
                 float(e_data.get("precio_unitario", 0.0)))
            )

    if variantes is not None:
        conn.execute("DELETE FROM producto_variantes WHERE producto_id = ?", (producto_id,))
        for var in variantes:
            v_data = var.model_dump() if hasattr(var, "model_dump") else var
            conn.execute(
                """INSERT INTO producto_variantes
                (producto_id, tipo_atributo, valor, sku_variante, precio_adicional, precio_fijo, color_hex)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (producto_id,
                 (v_data.get("tipo_atributo") or "Color").strip(),
                 (v_data.get("valor") or "").strip(),
                 (v_data.get("sku_variante") or "").strip() or None,
                 float(v_data.get("precio_adicional", 0.0) or 0.0),
                 float(v_data["precio_fijo"]) if v_data.get("precio_fijo") is not None else None,
                 (v_data.get("color_hex") or "").strip() or None)
            )


@router.get("/productos")
def listar_productos(
    response: Response,
    q: Optional[str] = Query(None, description="Buscar por nombre, descripción o código"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    paginated: bool = Query(False, description="Devolver respuesta paginada estructurada")
):
    with db_connection() as conn:
        if q:
            term = f"%{q.strip()}%"
            where_clause = "WHERE is_deleted = 0 AND (nombre LIKE ? OR descripcion LIKE ? OR codigo LIKE ?)"
            params = [term, term, term]
        else:
            where_clause = "WHERE is_deleted = 0"
            params = []

        count_query = f"SELECT COUNT(*) FROM productos {where_clause}"
        total = conn.execute(count_query, params).fetchone()[0]
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        if paginated:
            query = f"SELECT * FROM productos {where_clause} ORDER BY COALESCE(nombre, descripcion) LIMIT ? OFFSET ?"
            query_params = list(params) + [page_size, (page - 1) * page_size]
        else:
            if q:
                query = f"SELECT * FROM productos {where_clause} ORDER BY COALESCE(nombre, descripcion) LIMIT 50"
                query_params = params
            else:
                query = f"SELECT * FROM productos {where_clause} ORDER BY COALESCE(nombre, descripcion)"
                query_params = params

        rows = conn.execute(query, query_params).fetchall()
        resultado = []
        if rows:
            prod_ids = [r["id"] for r in rows]
            placeholders = ",".join("?" for _ in prod_ids)
            escalados_by_prod = {pid: [] for pid in prod_ids}
            variantes_by_prod = {pid: [] for pid in prod_ids}

            esc_rows = conn.execute(
                f"SELECT * FROM producto_escalados WHERE producto_id IN ({placeholders}) ORDER BY cantidad_minima ASC",
                prod_ids
            ).fetchall()
            for e in esc_rows:
                escalados_by_prod[e["producto_id"]].append(dict(e))

            var_rows = conn.execute(
                f"SELECT * FROM producto_variantes WHERE producto_id IN ({placeholders}) ORDER BY id ASC",
                prod_ids
            ).fetchall()
            for v in var_rows:
                variantes_by_prod[v["producto_id"]].append(dict(v))

            for r in rows:
                p_dict = dict(r)
                p_dict["escalados"] = escalados_by_prod.get(p_dict["id"], [])
                p_dict["variantes"] = variantes_by_prod.get(p_dict["id"], [])
                resultado.append(p_dict)

        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
            response.headers["X-Total-Pages"] = str(total_pages)

        if paginated:
            return {
                "items": resultado,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        return resultado


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM productos WHERE id = ? AND is_deleted = 0",
            (producto_id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Producto no encontrado")
        return _cargar_hijos_producto(conn, dict(row))


@router.get("/productos/{producto_id}/precio-volumen")
def consultar_precio_volumen(
    producto_id: int,
    cantidad: float = Query(1.0, ge=0.01),
    variante_id: Optional[int] = Query(None)
):
    """Calcula y devuelve el precio unitario sugerido según el volumen y la variante seleccionada."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM productos WHERE id = ? AND is_deleted = 0", (producto_id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Producto no encontrado")
        prod_dict = _cargar_hijos_producto(conn, dict(row))

        precio_unitario = calcular_precio_unitario_sugerido(
            precio_base=prod_dict["precio_unitario_base"],
            escalados=prod_dict.get("escalados", []),
            variantes=prod_dict.get("variantes", []),
            cantidad=cantidad,
            variante_id=variante_id
        )
        return {
            "producto_id": producto_id,
            "cantidad": cantidad,
            "variante_id": variante_id,
            "precio_unitario": precio_unitario,
            "precio_base": prod_dict["precio_unitario_base"],
            "tiene_escalado": len(prod_dict.get("escalados", [])) > 0
        }


@router.post("/productos", status_code=201)
def crear_producto(producto: Union[ProductoCreate, list[ProductoCreate]]):
    with db_connection() as conn:
        try:
            if isinstance(producto, list):
                insertados = []
                for item in producto:
                    codigo_val = item.codigo.strip() if item.codigo else None
                    cursor = conn.execute(
                        """INSERT INTO productos
                        (codigo, nombre, descripcion, precio_unitario_base, porcentaje_iva, aplica_irpf, porcentaje_irpf)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(codigo) DO UPDATE SET
                            nombre=excluded.nombre,
                            descripcion=excluded.descripcion,
                            precio_unitario_base=excluded.precio_unitario_base,
                            porcentaje_iva=excluded.porcentaje_iva,
                            aplica_irpf=excluded.aplica_irpf,
                            porcentaje_irpf=excluded.porcentaje_irpf,
                            is_deleted=0
                        RETURNING id
                        """,
                        (codigo_val,
                         item.nombre.strip() if item.nombre else None,
                         item.descripcion.strip(),
                         item.precio_unitario_base,
                         item.porcentaje_iva,
                         int(item.aplica_irpf),
                         item.porcentaje_irpf)
                    )
                    ret_row = cursor.fetchone()
                    prod_id = ret_row[0] if ret_row else cursor.lastrowid
                    if not prod_id and codigo_val:
                        found = conn.execute("SELECT id FROM productos WHERE codigo = ?", (codigo_val,)).fetchone()
                        if found:
                            prod_id = found["id"]

                    if item.escalados or item.variantes:
                        _guardar_hijos_producto(conn, prod_id, item.escalados, item.variantes)
                    row = conn.execute("SELECT * FROM productos WHERE id = ?", (prod_id,)).fetchone()
                    if row:
                        insertados.append(_cargar_hijos_producto(conn, dict(row)))
                return insertados
            else:
                codigo_val = producto.codigo.strip() if producto.codigo else None
                if codigo_val:
                    existente = conn.execute("SELECT id, is_deleted FROM productos WHERE codigo = ?", (codigo_val,)).fetchone()
                    if existente:
                        if existente["is_deleted"] == 0:
                            raise ConflictError("Ya existe un producto con ese código")
                        else:
                            # Reactivar producto previamente dado de baja / eliminado
                            prod_id = existente["id"]
                            conn.execute(
                                """UPDATE productos SET
                                    nombre = ?,
                                    descripcion = ?,
                                    precio_unitario_base = ?,
                                    porcentaje_iva = ?,
                                    aplica_irpf = ?,
                                    porcentaje_irpf = ?,
                                    is_deleted = 0
                                WHERE id = ?""",
                                (
                                    producto.nombre.strip() if producto.nombre else None,
                                    producto.descripcion.strip(),
                                    producto.precio_unitario_base,
                                    producto.porcentaje_iva,
                                    int(producto.aplica_irpf),
                                    producto.porcentaje_irpf,
                                    prod_id
                                )
                            )
                            if producto.escalados is not None or producto.variantes is not None:
                                _guardar_hijos_producto(conn, prod_id, producto.escalados, producto.variantes)
                            row = conn.execute("SELECT * FROM productos WHERE id = ?", (prod_id,)).fetchone()
                            return _cargar_hijos_producto(conn, dict(row))

                cursor = conn.execute(
                    """INSERT INTO productos
                    (codigo, nombre, descripcion, precio_unitario_base, porcentaje_iva, aplica_irpf, porcentaje_irpf)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING id""",
                    (codigo_val,
                     producto.nombre.strip() if producto.nombre else None,
                     producto.descripcion.strip(),
                     producto.precio_unitario_base,
                     producto.porcentaje_iva,
                     int(producto.aplica_irpf),
                     producto.porcentaje_irpf)
                )
                ret_row = cursor.fetchone()
                prod_id = ret_row[0] if ret_row else cursor.lastrowid
                if producto.escalados or producto.variantes:
                    _guardar_hijos_producto(conn, prod_id, producto.escalados, producto.variantes)
                row = conn.execute(
                    "SELECT * FROM productos WHERE id = ?", (prod_id,)
                ).fetchone()
                return _cargar_hijos_producto(conn, dict(row))
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ConflictError("Ya existe un producto con ese código")
            raise


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(producto_id: int, producto: ProductoUpdate):
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM productos WHERE id = ? AND is_deleted = 0", (producto_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Producto no encontrado")

        dumped = producto.model_dump(exclude_unset=True)
        escalados_in = dumped.pop("escalados", None)
        variantes_in = dumped.pop("variantes", None)

        if 'codigo' in dumped and dumped['codigo'] is not None and not str(dumped['codigo']).strip():
            dumped['codigo'] = None

        if dumped:
            set_clause = ", ".join([f"{k} = ?" for k in dumped.keys()])
            values = list(dumped.values())
            values.append(producto_id)
            try:
                conn.execute(
                    f"UPDATE productos SET {set_clause} WHERE id = ?",
                    values
                )
            except Exception as e:
                if "UNIQUE" in str(e):
                    raise ConflictError(f"Ya existe un producto con el código '{producto.codigo}'")
                raise

        # Sincronizar escalados y variantes si se enviaron
        _guardar_hijos_producto(conn, producto_id, escalados_in, variantes_in)

        row = conn.execute(
            "SELECT * FROM productos WHERE id = ?", (producto_id,)
        ).fetchone()
        return _cargar_hijos_producto(conn, dict(row))


@router.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: int):
    """Soft delete."""
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM productos WHERE id = ? AND is_deleted = 0", (producto_id,)
        ).fetchone()
        if not existing:
            raise NotFoundError("Producto no encontrado")
        conn.execute(
            "UPDATE productos SET is_deleted = 1 WHERE id = ?",
            (producto_id,)
        )
        return {"message": "Producto eliminado correctamente"}
