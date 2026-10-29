import pytest


def test_api_descuentos_crud_global(client):
    """Prueba el ciclo de vida de un descuento global (todos los productos)."""
    # 1. Crear descuento porcentual global
    res_crear = client.post("/api/descuentos", json={
        "nombre": "Descuento Primavera 15%",
        "codigo": "PRIMAVERA15",
        "tipo": "porcentaje",
        "valor": 15.0,
        "aplica_a": "todos",
        "descripcion": "Promoción estacional para todos los conceptos",
        "activo": True
    })
    assert res_crear.status_code == 201, res_crear.text
    data = res_crear.json()
    desc_id = data["id"]
    assert data["nombre"] == "Descuento Primavera 15%"
    assert data["codigo"] == "PRIMAVERA15"
    assert data["tipo"] == "porcentaje"
    assert data["valor"] == 15.0
    assert data["aplica_a"] == "todos"
    assert data["activo"] is True

    # 2. Consultar por ID
    res_get = client.get(f"/api/descuentos/{desc_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == desc_id

    # 3. Listar descuentos
    res_list = client.get("/api/descuentos")
    assert res_list.status_code == 200
    ids = [d["id"] for d in res_list.json()]
    assert desc_id in ids

    # 4. Actualizar descuento a importe fijo
    res_upd = client.put(f"/api/descuentos/{desc_id}", json={
        "tipo": "fijo",
        "valor": 50.0,
        "descripcion": "Modificado a 50 euros fijos"
    })
    assert res_upd.status_code == 200
    upd_data = res_upd.json()
    assert upd_data["tipo"] == "fijo"
    assert upd_data["valor"] == 50.0
    assert upd_data["descripcion"] == "Modificado a 50 euros fijos"

    # 5. Pausar / Desactivar
    res_pause = client.put(f"/api/descuentos/{desc_id}", json={"activo": False})
    assert res_pause.status_code == 200
    assert res_pause.json()["activo"] is False

    # 6. Eliminar (soft-delete)
    res_del = client.delete(f"/api/descuentos/{desc_id}")
    assert res_del.status_code == 200

    # 7. Ya no debe figurar en la lista activa
    res_list_after = client.get("/api/descuentos")
    ids_after = [d["id"] for d in res_list_after.json()]
    assert desc_id not in ids_after


def test_api_descuentos_vinculado_productos(client):
    """Prueba descuentos vinculados a productos específicos y su filtro por producto_id."""
    # 1. Crear 2 productos
    res_p1 = client.post("/api/productos", json={
        "nombre": "Invitación Clásica A5",
        "descripcion": "Papel artesanal 300g",
        "precio_unitario_base": 5.0
    })
    assert res_p1.status_code == 201
    p1_id = res_p1.json()["id"]

    res_p2 = client.post("/api/productos", json={
        "nombre": "Minuta Menú",
        "descripcion": "Papel vegetal",
        "precio_unitario_base": 2.5
    })
    assert res_p2.status_code == 201
    p2_id = res_p2.json()["id"]

    # 2. Crear descuento vinculado SOLO a producto 1
    res_desc = client.post("/api/descuentos", json={
        "nombre": "Promo Solo Invitación 20%",
        "codigo": "INVITA20",
        "tipo": "porcentaje",
        "valor": 20.0,
        "aplica_a": "productos",
        "producto_ids": [p1_id],
        "activo": True
    })
    assert res_desc.status_code == 201
    desc_id = res_desc.json()["id"]
    assert res_desc.json()["producto_ids"] == [p1_id]

    # 3. Filtrar descuentos aplicables al producto 1 (debe incluirse)
    res_filtro_p1 = client.get(f"/api/descuentos?producto_id={p1_id}")
    assert res_filtro_p1.status_code == 200
    ids_p1 = [d["id"] for d in res_filtro_p1.json()]
    assert desc_id in ids_p1

    # 4. Filtrar descuentos aplicables al producto 2 (NO debe incluirse el específico de p1)
    res_filtro_p2 = client.get(f"/api/descuentos?producto_id={p2_id}")
    assert res_filtro_p2.status_code == 200
    ids_p2 = [d["id"] for d in res_filtro_p2.json()]
    assert desc_id not in ids_p2


def test_descuentos_html_view(client):
    """Comprueba que la vista web /descuentos responde 200."""
    res = client.get("/descuentos")
    assert res.status_code == 200
    assert "Descuentos y Promociones" in res.text

