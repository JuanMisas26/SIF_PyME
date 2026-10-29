import pytest
from app.database import init_db, db_connection, set_configuracion


def test_sec01_backup_path_traversal_and_validation(client):
    """SEC-01: Path traversal y nombres inválidos deben ser bloqueados, y no existentes con 404."""
    # 1. Path traversal (bloqueado por routing o validación -> 404 o 422)
    res_traversal = client.post("/api/backups/..%2F..%2Ftest.db/restaurar")
    assert res_traversal.status_code in [404, 422]

    # 2. Nombre inválido que no cumple con el patrón facturacion_pyme_*.db
    res_invalid = client.post("/api/backups/malicious_payload.db/restaurar")
    assert res_invalid.status_code == 422
    assert res_invalid.json()["error_code"] == "VALIDATION_ERROR"

    # 3. Nombre válido pero archivo inexistente -> 404
    res_not_found = client.post("/api/backups/facturacion_pyme_20261231_235959_noexiste.db/restaurar")
    assert res_not_found.status_code == 404
    assert res_not_found.json()["error_code"] == "NOT_FOUND"


def test_log01_restaurar_version_factura_preserva_descuentos_y_sin_iva(client, emisor_configurado):
    """LOG-01: Restaurar versión previa de factura debe preservar descuentos y régimen sin_iva."""
    # Crear cliente con CIF válido
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente TimeMachine Factura",
        "nif_cif": "B10000008"
    })
    assert cli_res.status_code == 201
    cliente_id = cli_res.json()["id"]

    # 1. Crear factura con descuento y sin IVA
    payload_v1 = {
        "cliente_id": cliente_id,
        "fecha_emision": "2026-06-01",
        "sin_iva": True,
        "descuento_id": 1,
        "descuento_nombre": "PROMO10",
        "descuento_tipo": "porcentaje",
        "descuento_valor": 10.0,
        "descuento_importe_total": 50.0,
        "descuento_visible": True,
        "lineas": [
            {
                "descripcion": "Servicio de Consultoría",
                "cantidad": 1.0,
                "precio_unitario": 450.0,
                "precio_unitario_original": 500.0,
                "descuento_id": 1,
                "porcentaje_iva": 0.0
            }
        ]
    }
    f_res = client.post("/api/facturas", json=payload_v1)
    assert f_res.status_code == 201
    f_id = f_res.json()["id"]

    # 2. Modificar la factura para crear versión 2 (quitando descuento y sin_iva=False)
    payload_v2 = {
        "sin_iva": False,
        "descuento_id": None,
        "descuento_valor": 0.0,
        "descuento_importe_total": 0.0,
        "lineas": [
            {
                "descripcion": "Servicio de Consultoría Modificado",
                "cantidad": 2.0,
                "precio_unitario": 500.0,
                "porcentaje_iva": 21.0
            }
        ]
    }
    f_put = client.put(f"/api/facturas/{f_id}", json=payload_v2)
    assert f_put.status_code == 200

    # 3. Restaurar versión 1
    res_rest = client.post(f"/api/facturas/{f_id}/versiones/1/restaurar")
    assert res_rest.status_code == 200

    # 4. Comprobar que los campos de descuento y sin_iva han sido restaurados
    res_get = client.get(f"/api/facturas/{f_id}")
    assert res_get.status_code == 200
    f_restaurada = res_get.json()
    assert f_restaurada["sin_iva"] is True
    assert f_restaurada["descuento_id"] == 1
    assert f_restaurada["descuento_valor"] == 10.0
    assert f_restaurada["descuento_importe_total"] == 50.0
    assert f_restaurada["lineas"][0]["precio_unitario_original"] == 500.0
    assert f_restaurada["lineas"][0]["descuento_id"] == 1


def test_log01_restaurar_version_presupuesto_preserva_descuentos_y_sin_iva(client):
    """LOG-01: Restaurar versión previa de presupuesto debe preservar opciones, líneas con descuento e impuestos."""
    # Crear cliente
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente TimeMachine Presupuesto"
    })
    assert cli_res.status_code in [200, 201]
    cliente_id = cli_res.json()["id"]

    # 1. Crear presupuesto con opciones, descuentos y sin IVA
    payload_p1 = {
        "numero_presupuesto": "PRE-TM-001",
        "cliente_id": cliente_id,
        "titulo": "Presupuesto Proyecto Alfa",
        "subtitulo": "Subtítulo Alfa",
        "opciones": [
            {
                "nombre_opcion": "Opción Principal",
                "descuento_id": 2,
                "descuento_nombre": "DTO20",
                "descuento_tipo": "porcentaje",
                "descuento_valor": 20.0,
                "descuento_importe_total": 40.0,
                "descuento_visible": True,
                "lineas": [
                    {
                        "descripcion": "Partida 1",
                        "cantidad": 2.0,
                        "precio_unitario": 80.0,
                        "precio_unitario_original": 100.0,
                        "descuento_id": 2
                    }
                ]
            }
        ]
    }
    p_res = client.post("/api/presupuestos", json=payload_p1)
    assert p_res.status_code == 200
    p_id = p_res.json()["id"]

    # 2. Modificar el presupuesto para crear versión 2
    payload_p2 = {
        "titulo": "Presupuesto Modificado",
        "opciones": [
            {
                "nombre_opcion": "Opción Modificada Sin Descuento",
                "lineas": [
                    {
                        "descripcion": "Partida Modificada",
                        "cantidad": 1.0,
                        "precio_unitario": 300.0
                    }
                ]
            }
        ]
    }
    p_put = client.put(f"/api/presupuestos/{p_id}", json=payload_p2)
    assert p_put.status_code == 200

    # 3. Restaurar versión 1
    res_rest = client.post(f"/api/presupuestos/{p_id}/versiones/1/restaurar")
    assert res_rest.status_code == 200

    # 4. Comprobar que la opción y partida restaurada contienen los descuentos
    res_get = client.get(f"/api/presupuestos/{p_id}")
    assert res_get.status_code == 200
    p_rest = res_get.json()
    assert p_rest["titulo"] == "Presupuesto Proyecto Alfa"
    assert len(p_rest["opciones"]) == 1
    op_rest = p_rest["opciones"][0]
    assert op_rest["descuento_id"] == 2
    assert op_rest["descuento_valor"] == 20.0
    assert op_rest["lineas"][0]["precio_unitario_original"] == 100.0
    assert op_rest["lineas"][0]["descuento_id"] == 2


def test_log02_convertir_presupuesto_requiere_emisor_configurado(client):
    """LOG-02: Convertir presupuesto a factura debe fallar si falta Nombre o NIF en Configuración."""
    # Desconfigurar datos fiscales del emisor
    set_configuracion({"nombre": "", "nif": ""})

    # Crear cliente y presupuesto
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Conversión Fiscal"})
    cliente_id = cli_res.json()["id"]

    p_res = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-FISCAL-001",
        "cliente_id": cliente_id,
        "titulo": "Presupuesto Fiscal Test",
        "opciones": [
            {
                "nombre_opcion": "Opción 1",
                "lineas": [{"descripcion": "Item 1", "cantidad": 1.0, "precio_unitario": 100.0}]
            }
        ]
    })
    p_id = p_res.json()["id"]
    op_id = p_res.json()["opciones"][0]["id"]

    # Intentar convertir sin emisor configurado -> Debe fallar con EMISOR_CONFIG_MISSING
    res_conv = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={"opcion_id": op_id})
    assert res_conv.status_code == 400
    assert res_conv.json()["error_code"] == "EMISOR_CONFIG_MISSING"

    # Configurar emisor y reintentar -> Debe triunfar
    set_configuracion({"nombre": "Empresa Fiscal SL", "nif": "B10000008"})
    res_conv_ok = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={"opcion_id": op_id})
    assert res_conv_ok.status_code == 200
    assert "factura_id" in res_conv_ok.json()


def test_log03_init_db_no_sobreescribe_presupuestos_personalizados(client):
    """LOG-03: init_db no debe mutar títulos o subtítulos personalizados en presupuestos."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Test No Sobreescribir"})
    cliente_id = cli_res.json()["id"]

    with db_connection() as conn:
        conn.execute("""
            INSERT INTO presupuestos (numero_presupuesto, cliente_id, fecha, titulo, subtitulo, estado)
            VALUES ('PRE-NO-MUTAR', ?, '2026-06-01', 'Presupuesto para invitaciones', 'Precios boda especiales', 'Borrador')
        """, (cliente_id,))

    # Ejecutar init_db() simulating startup
    init_db()

    # Comprobar que los textos no fueron mutados
    with db_connection() as conn:
        row = conn.execute("SELECT titulo, subtitulo FROM presupuestos WHERE numero_presupuesto = 'PRE-NO-MUTAR'").fetchone()
        assert row["titulo"] == "Presupuesto para invitaciones"
        assert row["subtitulo"] == "Precios boda especiales"

