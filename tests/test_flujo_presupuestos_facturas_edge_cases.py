import pytest
from app.services.pdf_service import get_pdf_output_path

def test_reabrir_presupuesto_elimina_pdf_fisico_factura(client, emisor_configurado):
    """Verifica que al reabrir un presupuesto facturado a Borrador, el PDF de la factura vinculada se elimina de disco."""
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Test EdgeCase 1", "nif_cif": "B10000008"})
    assert res_cli.status_code == 201
    cli_id = res_cli.json()["id"]

    # 2. Crear presupuesto
    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-EDGE-001",
        "cliente_id": cli_id,
        "fecha": "2026-10-18",
        "titulo": "Presupuesto Prueba PDF Purge",
        "opciones": [{
            "nombre_opcion": "Opción A",
            "total": 500.0,
            "lineas": [{"descripcion": "Desarrollo", "cantidad": 1, "precio_unitario": 500.0, "total": 500.0}]
        }]
    })
    assert res_p.status_code in [200, 201]
    p_id = res_p.json()["id"]
    op_id = res_p.json()["opciones"][0]["id"]

    # 3. Convertir a Factura
    res_fac = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={"opcion_id": op_id})
    assert res_fac.status_code == 200
    fac_num = res_fac.json()["numero_factura"]
    fac_id = res_fac.json()["factura_id"]

    # Comprobar que el PDF existe físicamente en disco
    pdf_path = get_pdf_output_path(fac_num, "2026-10-18", sin_iva=False)
    # Puede haberse emitido hoy (la fecha actual) o con la del presupuesto:
    # Verifiquemos con la respuesta de la factura
    fac_info = client.get(f"/api/facturas/{fac_id}").json()
    pdf_path = get_pdf_output_path(fac_num, fac_info["fecha_emision"], sin_iva=bool(fac_info["sin_iva"]))
    assert pdf_path.exists()

    # 4. Reabrir presupuesto a Borrador
    res_reabrir = client.patch(f"/api/presupuestos/{p_id}/estado", json={"estado": "Borrador"})
    assert res_reabrir.status_code == 200

    # 5. Comprobar que el PDF de la factura anterior ha sido purgado de disco
    assert not pdf_path.exists()


def test_destruir_factura_revierte_presupuesto_a_aceptado(client, emisor_configurado):
    """Verifica que si una factura se destruye permanentemente, el presupuesto asociado pasa a Aceptado y permite volver a editarse."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Test EdgeCase 2", "nif_cif": "B10000008"})
    cli_id = res_cli.json()["id"]

    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-EDGE-002",
        "cliente_id": cli_id,
        "fecha": "2026-10-19",
        "titulo": "Presupuesto Destrucción Factura",
        "opciones": [{
            "nombre_opcion": "Opción 1",
            "total": 200.0,
            "lineas": [{"descripcion": "Hosting", "cantidad": 1, "precio_unitario": 200.0, "total": 200.0}]
        }]
    })
    p_id = res_p.json()["id"]
    op_id = res_p.json()["opciones"][0]["id"]

    res_fac = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={"opcion_id": op_id})
    fac_id = res_fac.json()["factura_id"]

    # Destruir factura
    res_destr = client.delete(f"/api/facturas/{fac_id}/destruir")
    assert res_destr.status_code == 200

    # Comprobar que el presupuesto quedó en estado 'Aceptado' y factura_id en None
    p_after = client.get(f"/api/presupuestos/{p_id}").json()
    assert p_after["factura_id"] is None
    assert p_after["estado"] == "Aceptado"


def test_vaciar_papelera_revierte_presupuestos_vinculados_a_aceptado(client, emisor_configurado):
    """Verifica que vaciar la papelera con facturas vinculadas devuelve los presupuestos a Aceptado sin dejarlos huérfanos."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Test EdgeCase 3", "nif_cif": "B10000008"})
    cli_id = res_cli.json()["id"]

    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-EDGE-003",
        "cliente_id": cli_id,
        "fecha": "2026-10-20",
        "titulo": "Presupuesto Vaciar Papelera",
        "opciones": [{
            "nombre_opcion": "Opción Unica",
            "total": 350.0,
            "lineas": [{"descripcion": "Diseño", "cantidad": 1, "precio_unitario": 350.0, "total": 350.0}]
        }]
    })
    p_id = res_p.json()["id"]
    op_id = res_p.json()["opciones"][0]["id"]

    res_fac = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={"opcion_id": op_id})
    fac_id = res_fac.json()["factura_id"]

    # Enviar factura a papelera
    client.delete(f"/api/facturas/{fac_id}")

    # Vaciar papelera
    res_vaciar = client.post("/api/papelera/vaciar")
    assert res_vaciar.status_code == 200

    # Comprobar estado del presupuesto
    p_after = client.get(f"/api/presupuestos/{p_id}").json()
    assert p_after["factura_id"] is None
    assert p_after["estado"] == "Aceptado"

