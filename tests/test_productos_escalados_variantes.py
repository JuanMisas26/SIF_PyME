import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_crear_producto_con_escalados_y_variantes():
    payload = {
        "codigo": "INV-LUJO",
        "nombre": "Invitación de Boda Premium",
        "descripcion": "Papel artesanal de algodón con sobre forrado",
        "precio_unitario_base": 6.50,
        "porcentaje_iva": 21.0,
        "aplica_irpf": False,
        "porcentaje_irpf": 0.0,
        "escalados": [
            {"cantidad_minima": 1.0, "cantidad_maxima": 49.0, "precio_unitario": 6.50},
            {"cantidad_minima": 50.0, "cantidad_maxima": 99.0, "precio_unitario": 5.20},
            {"cantidad_minima": 100.0, "cantidad_maxima": None, "precio_unitario": 4.10}
        ],
        "variantes": [
            {"tipo_atributo": "Color", "valor": "Blanco Roto", "color_hex": "#F8F8F6", "precio_adicional": 0.0},
            {"tipo_atributo": "Color", "valor": "Verde Oliva", "color_hex": "#556B2F", "precio_adicional": 0.50},
            {"tipo_atributo": "Acabado", "valor": "Relieve Seco", "precio_adicional": 0.80}
        ]
    }

    res = client.post("/api/productos", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    prod_id = data["id"]
    assert data["nombre"] == "Invitación de Boda Premium"
    assert len(data["escalados"]) == 3
    assert len(data["variantes"]) == 3

    # Comprobar consulta individual
    res_get = client.get(f"/api/productos/{prod_id}")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert len(data_get["escalados"]) == 3
    assert len(data_get["variantes"]) == 3

    # Comprobar endpoint de cálculo de precio por volumen
    # 1. Cantidad = 10 (tramo 1-49 -> 6.50)
    res_calc1 = client.get(f"/api/productos/{prod_id}/precio-volumen?cantidad=10")
    assert res_calc1.status_code == 200
    assert res_calc1.json()["precio_unitario"] == 6.50

    # 2. Cantidad = 60 (tramo 50-99 -> 5.20)
    res_calc2 = client.get(f"/api/productos/{prod_id}/precio-volumen?cantidad=60")
    assert res_calc2.status_code == 200
    assert res_calc2.json()["precio_unitario"] == 5.20

    # 3. Cantidad = 150 (tramo >= 100 -> 4.10)
    res_calc3 = client.get(f"/api/productos/{prod_id}/precio-volumen?cantidad=150")
    assert res_calc3.status_code == 200
    assert res_calc3.json()["precio_unitario"] == 4.10

    # 4. Con variante Verde Oliva (+0.50) y cantidad 1 (precio base 6.50 + 0.50 = 7.00)
    var_verde = next(v for v in data_get["variantes"] if v["valor"] == "Verde Oliva")
    res_calc4 = client.get(f"/api/productos/{prod_id}/precio-volumen?cantidad=1&variante_id={var_verde['id']}")
    assert res_calc4.status_code == 200
    assert res_calc4.json()["precio_unitario"] == 7.00

    # 5. Actualizar producto eliminando tramos y modificando variantes
    res_put = client.put(f"/api/productos/{prod_id}", json={
        "nombre": "Invitación de Boda Premium v2",
        "escalados": [
            {"cantidad_minima": 1.0, "cantidad_maxima": None, "precio_unitario": 5.00}
        ],
        "variantes": [
            {"tipo_atributo": "Color", "valor": "Dorado", "color_hex": "#D4AF37", "precio_fijo": 8.00}
        ]
    })
    assert res_put.status_code == 200
    data_put = res_put.json()
    assert data_put["nombre"] == "Invitación de Boda Premium v2"
    assert len(data_put["escalados"]) == 1
    assert len(data_put["variantes"]) == 1
    assert data_put["escalados"][0]["precio_unitario"] == 5.00
    assert data_put["variantes"][0]["precio_fijo"] == 8.00

    # 6. Eliminar producto
    res_del = client.delete(f"/api/productos/{prod_id}")
    assert res_del.status_code == 200


def test_validacion_escalados_rango_invalido():
    payload = {
        "nombre": "Test Rangos",
        "descripcion": "Descripción",
        "precio_unitario_base": 1.0,
        "escalados": [
            {"cantidad_minima": 50.0, "cantidad_maxima": 10.0, "precio_unitario": 0.8}
        ]
    }
    res = client.post("/api/productos", json=payload)
    assert res.status_code == 422


def test_calcular_precio_unitario_sugerido_unitario():
    from app.models import calcular_precio_unitario_sugerido

    # Caso 1: Sin escalados ni variantes
    assert calcular_precio_unitario_sugerido(10.0, [], [], 5) == 10.0

    # Caso 2: Escalados escalonados
    escalados = [
        {"cantidad_minima": 1, "cantidad_maxima": 9, "precio_unitario": 10.0},
        {"cantidad_minima": 10, "cantidad_maxima": 49, "precio_unitario": 8.5},
        {"cantidad_minima": 50, "cantidad_maxima": None, "precio_unitario": 6.0},
    ]
    assert calcular_precio_unitario_sugerido(10.0, escalados, [], 5) == 10.0
    assert calcular_precio_unitario_sugerido(10.0, escalados, [], 10) == 8.5
    assert calcular_precio_unitario_sugerido(10.0, escalados, [], 100) == 6.0

    # Caso 3: Variante con recargo sobre el escalado
    variantes = [
        {"id": 1, "tipo_atributo": "Color", "valor": "Oro", "precio_adicional": 1.5, "precio_fijo": None},
        {"id": 2, "tipo_atributo": "Especial", "valor": "VIP", "precio_adicional": 0.0, "precio_fijo": 25.0},
    ]
    # 100 uds = tramo 6.0 + 1.5 de Oro = 7.5
    assert calcular_precio_unitario_sugerido(10.0, escalados, variantes, 100, variante_id=1) == 7.5
    # Variante con precio fijo sobrescribe todo = 25.0
    assert calcular_precio_unitario_sugerido(10.0, escalados, variantes, 100, variante_id=2) == 25.0

