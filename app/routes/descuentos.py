import math
from fastapi import APIRouter, Query, Response, status
from typing import Optional, Union
from app.database import db_connection
from app.models import (
    DescuentoCreate, DescuentoUpdate, DescuentoResponse,
    PaginatedResponse
)
from app.errors import NotFoundError, ConflictError

router = APIRouter()


def _cargar_productos_descuento(conn, d_dict: dict) -> dict:
    """Carga los IDs y nombres de productos asociados a este descuento."""
    did = d_dict["id"]
    rows = conn.execute(
        """SELECT p.id, COALESCE(p.nombre, p.descripcion) as nombre
        FROM descuento_productos dp
        JOIN productos p ON dp.producto_id = p.id
        WHERE dp.descuento_id = ? AND p.is_deleted = 0
        ORDER BY nombre ASC""",
        (did,)
    ).fetchall()
    d_dict["producto_ids"] = [r["id"] for r in rows]
    d_dict["productos_nombres"] = [r["nombre"] for r in rows]
    d_dict["activo"] = bool(d_dict.get("activo", 1))
    return d_dict


def _guardar_productos_descuento(conn, descuento_id: int, producto_ids: list[int] = None):
    """Sincroniza la tabla de relación descuento_productos."""
    if producto_ids is not None:
        conn.execute("DELETE FROM descuento_productos WHERE descuento_id = ?", (descuento_id,))
        for pid in set(producto_ids):
            conn.execute(
                "INSERT OR IGNORE INTO descuento_productos (descuento_id, producto_id) VALUES (?, ?)",
                (descuento_id, pid)
            )


@router.get("/descuentos", response_model=Union[list[DescuentoResponse], PaginatedResponse[DescuentoResponse]])
def listar_descuentos(
    response: Response,
    q: Optional[str] = Query(None, description="Buscar por nombre, código o descripción"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    aplica_a: Optional[str] = Query(None, description="Filtrar por ámbito: 'todos' o 'productos'"),
    producto_id: Optional[int] = Query(None, description="Buscar descuentos aplicables a un producto (globales o específicos)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    paginated: bool = Query(False, description="Devolver respuesta paginada estructurada")
):
    with db_connection() as conn:
        conditions = ["d.is_deleted = 0"]
        params = []

        if q:
            term = f"%{q.strip()}%"
            conditions.append("(d.nombre LIKE ? OR d.codigo LIKE ? OR d.descripcion LIKE ?)")
            params.extend([term, term, term])

        if activo is not None:
            conditions.append("d.activo = ?")
            params.append(1 if activo else 0)

        if aplica_a:
            conditions.append("d.aplica_a = ?")
            params.append(aplica_a)

        if producto_id is not None:
            # Descuentos globales O descuentos vinculados a este producto
            conditions.append("""(
                d.aplica_a = 'todos' 
                OR EXISTS (
                    SELECT 1 FROM descuento_productos dp 
                    WHERE dp.descuento_id = d.id AND dp.producto_id = ?
                )
            )""")
            params.append(producto_id)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        count_query = f"SELECT COUNT(*) FROM descuentos d {where_clause}"
        total = conn.execute(count_query, params).fetchone()[0]
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        if paginated:
            query = f"SELECT d.* FROM descuentos d {where_clause} ORDER BY d.activo DESC, d.nombre ASC LIMIT ? OFFSET ?"
            query_params = list(params) + [page_size, (page - 1) * page_size]
        else:
            query = f"SELECT d.* FROM descuentos d {where_clause} ORDER BY d.activo DESC, d.nombre ASC"
            query_params = params

        rows = conn.execute(query, query_params).fetchall()
        resultado = []
        if rows:
            desc_ids = [r["id"] for r in rows]
            placeholders = ",".join("?" for _ in desc_ids)
            prod_rows = conn.execute(
                f"""SELECT dp.descuento_id, p.id, COALESCE(p.nombre, p.descripcion) as nombre
                FROM descuento_productos dp
                JOIN productos p ON dp.producto_id = p.id
                WHERE dp.descuento_id IN ({placeholders}) AND p.is_deleted = 0
                ORDER BY nombre ASC""",
                desc_ids
            ).fetchall()

            pids_by_desc = {did: [] for did in desc_ids}
            pnombres_by_desc = {did: [] for did in desc_ids}
            for pr in prod_rows:
                pids_by_desc[pr["descuento_id"]].append(pr["id"])
                pnombres_by_desc[pr["descuento_id"]].append(pr["nombre"])

            for r in rows:
                d_dict = dict(r)
                d_dict["producto_ids"] = pids_by_desc.get(d_dict["id"], [])
                d_dict["productos_nombres"] = pnombres_by_desc.get(d_dict["id"], [])
                d_dict["activo"] = bool(d_dict.get("activo", 1))
                resultado.append(d_dict)

        if paginated:
            return {
                "items": resultado,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

        response.headers["X-Total-Count"] = str(total)
        return resultado


@router.get("/descuentos/{id}", response_model=DescuentoResponse)
def obtener_descuento(id: int):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM descuentos WHERE id = ? AND is_deleted = 0",
            (id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Descuento no encontrado")
        d_dict = _cargar_productos_descuento(conn, dict(row))
        return d_dict


@router.post("/descuentos", response_model=DescuentoResponse, status_code=status.HTTP_201_CREATED)
def crear_descuento(data: DescuentoCreate):
    with db_connection() as conn:
        # Validar código único si se especifica
        codigo = (data.codigo or "").strip().upper() or None
        if codigo:
            existe = conn.execute(
                "SELECT id FROM descuentos WHERE codigo = ? AND is_deleted = 0",
                (codigo,)
            ).fetchone()
            if existe:
                raise ConflictError(f"Ya existe un descuento con el código '{codigo}'")

        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO descuentos
            (nombre, codigo, tipo, valor, aplica_a, descripcion, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data.nombre.strip(),
                codigo,
                data.tipo,
                float(data.valor),
                data.aplica_a,
                (data.descripcion or "").strip() or None,
                1 if data.activo else 0
            )
        )
        descuento_id = cursor.lastrowid

        if data.aplica_a == "productos" and data.producto_ids:
            _guardar_productos_descuento(conn, descuento_id, data.producto_ids)

        row = conn.execute("SELECT * FROM descuentos WHERE id = ?", (descuento_id,)).fetchone()
        d_dict = _cargar_productos_descuento(conn, dict(row))
        return d_dict


@router.put("/descuentos/{id}", response_model=DescuentoResponse)
def actualizar_descuento(id: int, data: DescuentoUpdate):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM descuentos WHERE id = ? AND is_deleted = 0",
            (id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Descuento no encontrado")

        codigo = (data.codigo.strip().upper() if data.codigo else None) if data.codigo is not None else row["codigo"]
        if codigo and codigo != row["codigo"]:
            existe = conn.execute(
                "SELECT id FROM descuentos WHERE codigo = ? AND id != ? AND is_deleted = 0",
                (codigo, id)
            ).fetchone()
            if existe:
                raise ConflictError(f"Ya existe otro descuento con el código '{codigo}'")

        updates = []
        params = []

        if data.nombre is not None:
            updates.append("nombre = ?")
            params.append(data.nombre.strip())
        if data.codigo is not None:
            updates.append("codigo = ?")
            params.append(codigo)
        if data.tipo is not None:
            updates.append("tipo = ?")
            params.append(data.tipo)
        if data.valor is not None:
            updates.append("valor = ?")
            params.append(float(data.valor))
        if data.aplica_a is not None:
            updates.append("aplica_a = ?")
            params.append(data.aplica_a)
        if data.descripcion is not None:
            updates.append("descripcion = ?")
            params.append((data.descripcion or "").strip() or None)
        if data.activo is not None:
            updates.append("activo = ?")
            params.append(1 if data.activo else 0)

        updates.append("updated_at = CURRENT_TIMESTAMP")

        if updates:
            params.append(id)
            conn.execute(
                f"UPDATE descuentos SET {', '.join(updates)} WHERE id = ?",
                params
            )

        nuevo_aplica_a = data.aplica_a if data.aplica_a is not None else row["aplica_a"]
        if nuevo_aplica_a == "productos":
            if data.producto_ids is not None:
                _guardar_productos_descuento(conn, id, data.producto_ids)
        else:
            # Si ahora aplica a todos, limpiamos asociaciones específicas
            if data.aplica_a == "todos":
                _guardar_productos_descuento(conn, id, [])

        updated_row = conn.execute("SELECT * FROM descuentos WHERE id = ?", (id,)).fetchone()
        return _cargar_productos_descuento(conn, dict(updated_row))


@router.delete("/descuentos/{id}")
def eliminar_descuento(id: int):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM descuentos WHERE id = ? AND is_deleted = 0",
            (id,)
        ).fetchone()
        if not row:
            raise NotFoundError("Descuento no encontrado")

        conn.execute(
            "UPDATE descuentos SET is_deleted = 1, activo = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (id,)
        )
        return {"message": "Descuento eliminado correctamente", "id": id}

