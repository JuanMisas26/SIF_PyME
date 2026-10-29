import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_crear_y_listar_producto_con_nombre_y_descripcion():
    payload = {
        "codigo": "TEST-NOM-1",
        "nombre": "Tarjetón invitación con ilustración",
        "descripcion": "A5 Papel 300 gr verjurado premium",
        "precio_unitario_base": 1.85,
        "porcentaje_iva": 21.0,
        "aplica_irpf": False
    }
    resp = client.post("/api/productos", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Tarjetón invitación con ilustración"
    assert data["descripcion"] == "A5 Papel 300 gr verjurado premium"
    prod_id = data["id"]

    # Búsqueda por nombre
    resp_busqueda = client.get("/api/productos?q=Tarjetón")
    assert resp_busqueda.status_code == 200
    items = resp_busqueda.json()
    assert any(p["id"] == prod_id and p["nombre"] == "Tarjetón invitación con ilustración" for p in items)

    # Actualizar nombre
    resp_up = client.put(f"/api/productos/{prod_id}", json={"nombre": "Tarjetón invitación actualizado"})
    assert resp_up.status_code == 200
    assert resp_up.json()["nombre"] == "Tarjetón invitación actualizado"
    assert resp_up.json()["descripcion"] == "A5 Papel 300 gr verjurado premium"

    # Batch create como en la colección de Bruno
    batch_payload = [
        {
            "codigo": "SOB-ART-TEST",
            "nombre": "Sobre artesanal",
            "descripcion": "C5 Papel artesanal",
            "precio_unitario_base": 1.50,
            "porcentaje_iva": 21.0,
            "aplica_irpf": False
        }
    ]
    resp_batch = client.post("/api/productos", json=batch_payload)
    assert resp_batch.status_code == 201
    batch_res = resp_batch.json()
    assert len(batch_res) == 1
    assert batch_res[0]["nombre"] == "Sobre artesanal"
    assert batch_res[0]["descripcion"] == "C5 Papel artesanal"

    # Limpieza
    client.delete(f"/api/productos/{prod_id}")
    client.delete(f"/api/productos/{batch_res[0]['id']}")



def test_producto_nombre_obligatorio():
    # Intentar crear producto con nombre vacío
    resp = client.post("/api/productos", json={
        "nombre": "",
        "descripcion": "Descripción válida",
        "precio_unitario_base": 10.0
    })
    assert resp.status_code == 422
    data = resp.json()
    assert any("Nombre del producto" in err["message"] for err in data["errors"])

    # Intentar crear producto sin nombre
    resp2 = client.post("/api/productos", json={
        "descripcion": "Descripción válida",
        "precio_unitario_base": 10.0
    })
    assert resp2.status_code == 422
