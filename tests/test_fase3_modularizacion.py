import pytest
from fastapi.testclient import TestClient


def test_contadores_endpoint(client: TestClient):
    response = client.get("/api/contadores")
    assert response.status_code == 200
    data = response.json()
    assert "facturas" in data
    assert "presupuestos" in data
    assert "clientes" in data
    assert "papelera" in data


def test_backups_endpoints(client: TestClient):
    # List backups
    res_list = client.get("/api/backups")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    # Create snapshot
    res_snap = client.post("/api/backups/snapshot")
    assert res_snap.status_code == 200
    snap_data = res_snap.json()
    assert "path" in snap_data


def test_papelera_endpoints(client: TestClient):
    res_papelera = client.get("/api/papelera")
    assert res_papelera.status_code == 200
    data = res_papelera.json()
    assert "facturas" in data
    assert "presupuestos" in data
    assert "total" in data

    # Empty papelera
    res_vaciar = client.post("/api/papelera/vaciar")
    assert res_vaciar.status_code == 200
    assert "message" in res_vaciar.json()


def test_productos_batch_load(client: TestClient):
    # Create two products with escalados and variantes
    p1 = {
        "codigo": "BATCH-P1",
        "nombre": "Producto Batch 1",
        "descripcion": "Desc",
        "precio_unitario_base": 10.0,
        "porcentaje_iva": 21.0,
        "escalados": [{"cantidad_minima": 5.0, "cantidad_maxima": 10.0, "precio_unitario": 8.0}],
        "variantes": [{"tipo_atributo": "Color", "valor": "Rojo", "precio_adicional": 0.0}]
    }
    p2 = {
        "codigo": "BATCH-P2",
        "nombre": "Producto Batch 2",
        "descripcion": "Desc",
        "precio_unitario_base": 20.0,
        "porcentaje_iva": 21.0,
        "escalados": [{"cantidad_minima": 10.0, "cantidad_maxima": 20.0, "precio_unitario": 15.0}],
        "variantes": [{"tipo_atributo": "Talla", "valor": "S", "precio_adicional": 1.0}]
    }
    r1 = client.post("/api/productos", json=p1)
    assert r1.status_code == 201, r1.text
    r2 = client.post("/api/productos", json=p2)
    assert r2.status_code == 201, r2.text

    res = client.get("/api/productos")
    assert res.status_code == 200
    items = res.json()
    prod_map = {p["codigo"]: p for p in items}
    assert "BATCH-P1" in prod_map
    assert "BATCH-P2" in prod_map
    assert len(prod_map["BATCH-P1"]["escalados"]) == 1
    assert prod_map["BATCH-P1"]["escalados"][0]["cantidad_minima"] == 5.0
    assert len(prod_map["BATCH-P1"]["variantes"]) == 1
    assert len(prod_map["BATCH-P2"]["escalados"]) == 1
    assert len(prod_map["BATCH-P2"]["variantes"]) == 1


def test_presupuesto_batch_lines_multiple_options(client: TestClient):
    # Create client
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente Multi Opciones S.L.",
        "nif_cif": "B10000008",
        "direccion": "Calle 1",
        "ciudad": "Madrid",
        "codigo_postal": "28001"
    })
    assert cli_res.status_code == 201, cli_res.text
    cli = cli_res.json()

    # Create presupuesto with 2 options each having lines
    pres = {
        "numero_presupuesto": "PRES-MULTI-OPT-01",
        "cliente_id": cli["id"],
        "fecha": "2026-10-26",
        "titulo": "Presupuesto con Multiples Opciones",
        "estado": "Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción Estándar",
                "lineas": [
                    {"descripcion": "Línea 1A", "cantidad": 1, "precio_unitario": 50.0},
                    {"descripcion": "Línea 1B", "cantidad": 2, "precio_unitario": 25.0}
                ]
            },
            {
                "nombre_opcion": "Opción Premium",
                "lineas": [
                    {"descripcion": "Línea 2A", "cantidad": 1, "precio_unitario": 120.0}
                ]
            }
        ]
    }
    res_crear = client.post("/api/presupuestos", json=pres)
    assert res_crear.status_code == 200, res_crear.text
    data_creada = res_crear.json()
    assert len(data_creada["opciones"]) == 2
    assert len(data_creada["opciones"][0]["lineas"]) == 2
    assert len(data_creada["opciones"][1]["lineas"]) == 1

    # Fetch detail
    res_det = client.get(f"/api/presupuestos/{data_creada['id']}")
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert len(data_det["opciones"]) == 2
    assert len(data_det["opciones"][0]["lineas"]) == 2
    assert data_det["opciones"][0]["lineas"][0]["descripcion"] == "Línea 1A"
    assert len(data_det["opciones"][1]["lineas"]) == 1
    assert data_det["opciones"][1]["lineas"][0]["descripcion"] == "Línea 2A"
