import pytest
from datetime import date
from fastapi.testclient import TestClient


def test_versiones_factura_ciclo_completo(client, emisor_configurado):
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Test Versiones",
        "nif_cif": "12345678Z",
        "direccion": "Calle Versiones 1",
        "email": "versiones@test.com"
    })
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    # 2. Crear factura (debe generar versión v1 automáticamente)
    payload_f1 = {
        "cliente_id": cliente_id,
        "fecha_emision": "2026-06-01",
        "fecha_vencimiento": "2026-06-30",
        "observaciones": "Versión inicial",
        "estado": "Emitida",
        "lineas": [
            {
                "descripcion": "Diseño Web Corporativo",
                "cantidad": 1.0,
                "precio_unitario": 800.0,
                "porcentaje_iva": 21.0
            }
        ]
    }
    res_f = client.post("/api/facturas", json=payload_f1)
    assert res_f.status_code == 201
    factura_id = res_f.json()["id"]

    # 3. Comprobar que existe la versión v1
    res_ver = client.get(f"/api/facturas/{factura_id}/versiones")
    assert res_ver.status_code == 200
    versiones = res_ver.json()
    assert len(versiones) == 1
    assert versiones[0]["numero_version"] == 1
    assert "Emisión inicial" in versiones[0]["motivo"]
    assert versiones[0]["total_factura"] == 968.0  # 800 * 1.21

    # Detalle de la versión v1
    res_det_v1 = client.get(f"/api/facturas/{factura_id}/versiones/1")
    assert res_det_v1.status_code == 200
    det_v1 = res_det_v1.json()
    assert len(det_v1["snapshot"]["lineas"]) == 1
    assert det_v1["snapshot"]["lineas"][0]["descripcion"] == "Diseño Web Corporativo"

    # 4. Modificar la factura (debe generar versión v2)
    payload_f2 = {
        "cliente_id": cliente_id,
        "fecha_emision": "2026-06-01",
        "fecha_vencimiento": "2026-07-15",
        "observaciones": "Versión modificada con mantenimiento",
        "lineas": [
            {
                "descripcion": "Diseño Web Corporativo",
                "cantidad": 1.0,
                "precio_unitario": 800.0,
                "porcentaje_iva": 21.0
            },
            {
                "descripcion": "Mantenimiento Mensual",
                "cantidad": 2.0,
                "precio_unitario": 100.0,
                "porcentaje_iva": 21.0
            }
        ]
    }
    res_up = client.put(f"/api/facturas/{factura_id}", json=payload_f2)
    assert res_up.status_code == 200

    # Comprobar versiones (debe haber v2 y v1)
    res_ver2 = client.get(f"/api/facturas/{factura_id}/versiones")
    assert res_ver2.status_code == 200
    versiones2 = res_ver2.json()
    assert len(versiones2) == 2
    assert versiones2[0]["numero_version"] == 2  # Orden DESC
    assert versiones2[1]["numero_version"] == 1

    # 5. Cambiar estado a Pagada (debe generar versión v3)
    res_st = client.put(f"/api/facturas/{factura_id}/estado", json={"estado": "Pagada"})
    assert res_st.status_code == 200
    res_ver3 = client.get(f"/api/facturas/{factura_id}/versiones")
    versiones3 = res_ver3.json()
    assert len(versiones3) == 3
    assert versiones3[0]["numero_version"] == 3
    assert "Pagada" in versiones3[0]["motivo"]

    # 6. Revertir / Restaurar a la versión v1
    res_rest = client.post(f"/api/facturas/{factura_id}/versiones/1/restaurar")
    assert res_rest.status_code == 200
    assert res_rest.json()["nueva_version"] == 4

    # Verificar que la factura en base de datos vuelve a tener solo 1 línea (como en v1)
    res_f_actual = client.get(f"/api/facturas/{factura_id}")
    assert res_f_actual.status_code == 200
    f_actual = res_f_actual.json()
    assert len(f_actual["lineas"]) == 1
    assert f_actual["lineas"][0]["descripcion"] == "Diseño Web Corporativo"
    assert f_actual["total_factura"] == 968.0


def test_versiones_presupuesto_ciclo_completo(client):
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Presupuesto Versiones"})
    cli_id = res_cli.json()["id"]

    # 2. Crear presupuesto (debe generar versión v1)
    payload_p = {
        "numero_presupuesto": "PRE-VER-001",
        "cliente_id": cli_id,
        "fecha": "2026-06-10",
        "titulo": "Propuesta Branding v1",
        "opciones": [
            {
                "nombre_opcion": "Opción Estándar",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Identidad Visual",
                        "detalle_material": "Manual PDF",
                        "cantidad": 1,
                        "precio_unitario": 1200.0,
                        "orden": 1
                    }
                ]
            }
        ]
    }
    res_p = client.post("/api/presupuestos", json=payload_p)
    assert res_p.status_code == 200
    pres_id = res_p.json()["id"]

    # Comprobar v1
    res_v = client.get(f"/api/presupuestos/{pres_id}/versiones")
    assert res_v.status_code == 200
    versiones = res_v.json()
    assert len(versiones) == 1
    assert versiones[0]["numero_version"] == 1
    assert "Creación inicial" in versiones[0]["motivo"]

    # 3. Modificar presupuesto (debe generar versión v2)
    payload_p_up = {
        "numero_presupuesto": "PRE-VER-001",
        "cliente_id": cli_id,
        "fecha": "2026-06-10",
        "titulo": "Propuesta Branding Modificada",
        "opciones": [
            {
                "nombre_opcion": "Opción Premium",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Identidad Visual Completa + Papelería",
                        "detalle_material": "Impresión artesanal",
                        "cantidad": 1,
                        "precio_unitario": 2000.0,
                        "orden": 1
                    }
                ]
            }
        ]
    }
    res_up = client.put(f"/api/presupuestos/{pres_id}", json=payload_p_up)
    assert res_up.status_code == 200

    # Comprobar v2
    res_v2 = client.get(f"/api/presupuestos/{pres_id}/versiones")
    versiones2 = res_v2.json()
    assert len(versiones2) == 2
    assert versiones2[0]["numero_version"] == 2

    # 4. Restaurar v1
    res_rest = client.post(f"/api/presupuestos/{pres_id}/versiones/1/restaurar")
    assert res_rest.status_code == 200
    assert res_rest.json()["nueva_version"] == 3

    # Comprobar que el presupuesto volvió a Opción Estándar (1200.0)
    res_p_actual = client.get(f"/api/presupuestos/{pres_id}")
    assert res_p_actual.status_code == 200
    p_actual = res_p_actual.json()
    assert p_actual["titulo"] == "Propuesta Branding v1"
    assert p_actual["opciones"][0]["nombre_opcion"] == "Opción Estándar"
    assert p_actual["opciones"][0]["lineas"][0]["precio_unitario"] == 1200.0


def test_papelera_y_recuperacion_facturas_y_presupuestos(client, emisor_configurado):
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Papelera"})
    cli_id = res_cli.json()["id"]

    # 1. Crear factura
    res_f = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-06-15",
        "lineas": [{"descripcion": "Servicio de Consultoría", "cantidad": 1.0, "precio_unitario": 300.0}]
    })
    assert res_f.status_code == 201
    f_id = res_f.json()["id"]

    # 2. Crear presupuesto
    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-PAPELERA-1",
        "cliente_id": cli_id,
        "fecha": "2026-06-15",
        "titulo": "Presupuesto Descartado",
        "opciones": [{"nombre_opcion": "Op A", "lineas": [{"descripcion": "Item", "cantidad": 1, "precio_unitario": 50}]}]
    })
    assert res_p.status_code == 200
    p_id = res_p.json()["id"]

    # 3. Eliminar factura (soft delete)
    res_del_f = client.delete(f"/api/facturas/{f_id}")
    assert res_del_f.status_code == 200

    # 4. Eliminar presupuesto (soft delete)
    res_del_p = client.delete(f"/api/presupuestos/{p_id}")
    assert res_del_p.status_code == 200

    # 5. Comprobar que aparecen en la papelera
    res_pap = client.get("/api/papelera")
    assert res_pap.status_code == 200
    papelera = res_pap.json()
    assert papelera["total"] >= 2
    assert any(f["id"] == f_id for f in papelera["facturas"])
    assert any(p["id"] == p_id for p in papelera["presupuestos"])

    # Comprobar contadores globales
    res_cont = client.get("/api/contadores")
    assert res_cont.status_code == 200
    assert res_cont.json()["papelera"] >= 2

    # 6. Restaurar factura desde papelera
    res_rest_f = client.post(f"/api/facturas/{f_id}/restaurar")
    assert res_rest_f.status_code == 200

    # Verificar que la factura vuelve a estar en el listado activo
    res_f_activa = client.get(f"/api/facturas/{f_id}")
    assert res_f_activa.status_code == 200

    # 7. Destruir presupuesto definitivamente
    res_dest_p = client.delete(f"/api/presupuestos/{p_id}/destruir")
    assert res_dest_p.status_code == 200

    # Ya no existe en ningún sitio (ni activo ni papelera)
    res_pap_post = client.get("/api/papelera")
    assert not any(p["id"] == p_id for p in res_pap_post.json()["presupuestos"])

    # 8. Vaciar papelera
    res_vaciar = client.post("/api/papelera/vaciar")
    assert res_vaciar.status_code == 200
    res_pap_vacia = client.get("/api/papelera")
    assert res_pap_vacia.json()["total"] == 0


def test_backups_crear_listar_y_restaurar(client):
    # 1. Listar backups
    res_b = client.get("/api/backups")
    assert res_b.status_code == 200
    assert isinstance(res_b.json(), list)

    # 2. Crear backup manual
    res_crear = client.post("/api/backups/snapshot")
    assert res_crear.status_code == 200
    assert "Copia de seguridad creada" in res_crear.json()["message"]

    # 3. Comprobar que aparece en la lista
    res_b2 = client.get("/api/backups")
    assert res_b2.status_code == 200
    backups = res_b2.json()
    assert len(backups) > 0
    snapshot_filename = backups[-1]["filename"]

    # 4. Restaurar backup
    res_rest = client.post(f"/api/backups/{snapshot_filename}/restaurar")
    assert res_rest.status_code == 200
    assert "restaurada correctamente" in res_rest.json()["message"]


def test_restaurar_cliente_no_reactiva_documentos_previamente_en_papelera(client, emisor_configurado):
    """
    [LOG-05] Verifica que al restaurar un cliente, NO se restauran facturas o presupuestos
    que el usuario ya había descartado a la papelera antes de eliminar el cliente.
    """
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Selectivo Papelera"})
    assert res_cli.status_code == 201
    cli_id = res_cli.json()["id"]

    # 2. Crear Factura 1 (será descartada a papelera de antemano)
    res_f1 = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-06-10",
        "lineas": [{"descripcion": "Factura antigua descartada", "cantidad": 1, "precio_unitario": 100}]
    })
    assert res_f1.status_code == 201
    f1_id = res_f1.json()["id"]

    # 3. Crear Factura 2 (activa)
    res_f2 = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-06-12",
        "lineas": [{"descripcion": "Factura activa actual", "cantidad": 1, "precio_unitario": 200}]
    })
    assert res_f2.status_code == 201
    f2_id = res_f2.json()["id"]

    # 4. Enviar Factura 1 a la papelera individualmente
    res_del_f1 = client.delete(f"/api/facturas/{f1_id}")
    assert res_del_f1.status_code == 200

    # 5. Dar de baja al cliente (esto manda Factura 2 a la papelera por cascada)
    res_del_cli = client.delete(f"/api/clientes/{cli_id}")
    assert res_del_cli.status_code == 200

    # 6. Restaurar el cliente
    res_rest_cli = client.post(f"/api/clientes/{cli_id}/restaurar")
    assert res_rest_cli.status_code == 200

    # 7. Comprobaciones críticas:
    # Factura 2 debe haberse restaurado (activa)
    res_f2_check = client.get(f"/api/facturas/{f2_id}")
    assert res_f2_check.status_code == 200

    # Factura 1 debe permanecer en la papelera (404 al buscar como activa)
    res_f1_check = client.get(f"/api/facturas/{f1_id}")
    assert res_f1_check.status_code == 404

    res_papelera = client.get("/api/papelera")
    papelera_f_ids = [f["id"] for f in res_papelera.json()["facturas"]]
    assert f1_id in papelera_f_ids
    assert f2_id not in papelera_f_ids



def test_restaurar_version_factura_cambio_regimen_iva(client, emisor_configurado):
    """Verifica que restaurar una versión previa que tenía otro régimen de IVA
    actualiza el número de factura, la serie y reubica físicamente el archivo PDF."""
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Historial Regimen",
        "nif_cif": "B10000008",
        "direccion": "Calle Historica 1"
    })
    assert res_cli.status_code == 201
    cli_id = res_cli.json()["id"]

    # 2. Versión 1: Factura emitida CON IVA
    res_f = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-07-01",
        "sin_iva": False,
        "lineas": [{"descripcion": "Desarrollo Software", "cantidad": 1, "precio_unitario": 1000.0, "porcentaje_iva": 21.0}]
    })
    assert res_f.status_code == 201
    factura_id = res_f.json()["id"]
    numero_v1 = res_f.json()["numero_factura"]
    assert "Sin IVA" not in numero_v1

    from app.services.pdf_service import get_pdf_output_path
    path_v1 = get_pdf_output_path(numero_v1, "2026-07-01", sin_iva=False)
    assert path_v1.exists()
    assert "Con_IVA" in path_v1.parts

    # 3. Versión 2: Modificar factura a SIN IVA
    res_up = client.put(f"/api/facturas/{factura_id}", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-07-01",
        "sin_iva": True,
        "lineas": [{"descripcion": "Desarrollo Exento", "cantidad": 1, "precio_unitario": 1000.0, "porcentaje_iva": 0.0}]
    })
    assert res_up.status_code == 200
    numero_v2 = res_up.json()["numero_factura"]
    assert "Sin IVA" in numero_v2
    assert numero_v2 != numero_v1

    path_v2 = get_pdf_output_path(numero_v2, "2026-07-01", sin_iva=True)
    assert path_v2.exists()
    assert "Sin_IVA" in path_v2.parts
    assert not path_v1.exists()

    # 4. Restaurar a la Versión 1 (que era CON IVA)
    res_rest = client.post(f"/api/facturas/{factura_id}/versiones/1/restaurar")
    assert res_rest.status_code == 200
    numero_restaurado = res_rest.json()["numero_factura"]

    # Debe volver a la serie con IVA
    assert "Sin IVA" not in numero_restaurado
    assert numero_restaurado == numero_v1

    # Comprobar en BD
    f_bd = client.get(f"/api/facturas/{factura_id}").json()
    assert f_bd["sin_iva"] == 0
    assert f_bd["numero_factura"] == numero_v1
    assert f_bd["iva_total"] == 210.0

    # Comprobar archivos físicos en disco
    path_restaurado = get_pdf_output_path(numero_restaurado, "2026-07-01", sin_iva=False)
    assert path_restaurado.exists()
    assert "Con_IVA" in path_restaurado.parts
    assert not path_v2.exists()
