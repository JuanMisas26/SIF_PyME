import pytest
from starlette.testclient import TestClient
from app.services.pdf_service import get_pdf_output_path


def test_crear_facturas_con_y_sin_iva_en_carpetas_separadas(client: TestClient, emisor_configurado):
    """Verifica que las facturas se organizan físicamente en subcarpetas Con_IVA y Sin_IVA."""
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Test IVA", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    # 2. Factura CON IVA
    fac_con_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-10",
        "sin_iva": False,
        "lineas": [{"descripcion": "Servicio estándar", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 21.0}]
    })
    assert fac_con_res.status_code == 201
    con_data = fac_con_res.json()
    con_num = con_data["numero_factura"]

    path_con = get_pdf_output_path(con_num, "2026-10-10", sin_iva=False)
    assert path_con.exists()
    assert "Con_IVA" in path_con.parts
    assert "Sin_IVA" not in path_con.parts

    # 3. Factura SIN IVA
    fac_sin_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-10",
        "sin_iva": True,
        "lineas": [{"descripcion": "Formación exenta", "cantidad": 1, "precio_unitario": 150.0, "porcentaje_iva": 0.0}]
    })
    assert fac_sin_res.status_code == 201
    sin_data = fac_sin_res.json()
    sin_num = sin_data["numero_factura"]

    path_sin = get_pdf_output_path(sin_num, "2026-10-10", sin_iva=True)
    assert path_sin.exists()
    assert "Sin_IVA" in path_sin.parts
    assert "Con_IVA" not in path_sin.parts

    # Asegurar que ambos archivos existen simultáneamente en sus respectivas carpetas sin interferir
    assert path_con.exists()
    assert path_sin.exists()
    assert path_con != path_sin


def test_actualizar_factura_migra_entre_con_y_sin_iva(client: TestClient, emisor_configurado):
    """Verifica que cambiar el régimen de IVA de una factura mueve su PDF y actualiza la serie/numeración."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Migracion IVA", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    # 1. Crear inicialmente CON IVA
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-12",
        "sin_iva": False,
        "lineas": [{"descripcion": "Consultoría", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0}]
    })
    fac_id = fac_res.json()["id"]
    numero_con = fac_res.json()["numero_factura"]

    path_con = get_pdf_output_path(numero_con, "2026-10-12", sin_iva=False)
    assert path_con.exists()
    assert "Con_IVA" in path_con.parts

    # 2. Modificar factura pasando a régimen SIN IVA
    upd_res = client.put(f"/api/facturas/{fac_id}", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-12",
        "sin_iva": True,
        "lineas": [{"descripcion": "Consultoría exenta", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 0.0}]
    })
    assert upd_res.status_code == 200
    numero_sin = upd_res.json()["numero_factura"]

    # La numeración debe cambiar de la serie con IVA a la serie sin IVA
    assert numero_sin != numero_con
    assert "Sin IVA" in numero_sin

    path_sin = get_pdf_output_path(numero_sin, "2026-10-12", sin_iva=True)
    assert path_sin.exists()
    assert "Sin_IVA" in path_sin.parts
    # El archivo anterior en Con_IVA ya no debe existir
    assert not path_con.exists()


def test_actualizar_factura_migra_entre_sin_y_con_iva(client: TestClient, emisor_configurado):
    """Verifica la migración inversa de Sin IVA a Con IVA, actualizando numeración y carpetas."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Migracion Inversa", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    # 1. Crear inicialmente SIN IVA
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-14",
        "sin_iva": True,
        "lineas": [{"descripcion": "Servicio médico exento", "cantidad": 1, "precio_unitario": 120.0, "porcentaje_iva": 0.0}]
    })
    fac_id = fac_res.json()["id"]
    numero_sin = fac_res.json()["numero_factura"]
    assert "Sin IVA" in numero_sin

    path_sin = get_pdf_output_path(numero_sin, "2026-10-14", sin_iva=True)
    assert path_sin.exists()
    assert "Sin_IVA" in path_sin.parts

    # 2. Modificar factura pasando a régimen CON IVA
    upd_res = client.put(f"/api/facturas/{fac_id}", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-14",
        "sin_iva": False,
        "lineas": [{"descripcion": "Servicio estándar", "cantidad": 1, "precio_unitario": 120.0, "porcentaje_iva": 21.0}]
    })
    assert upd_res.status_code == 200
    numero_con = upd_res.json()["numero_factura"]

    # La numeración debe volver a la serie general con IVA
    assert numero_con != numero_sin
    assert "Sin IVA" not in numero_con

    path_con = get_pdf_output_path(numero_con, "2026-10-14", sin_iva=False)
    assert path_con.exists()
    assert "Con_IVA" in path_con.parts
    # El archivo anterior en Sin_IVA ya no debe existir
    assert not path_sin.exists()


def test_ciclo_borrado_restaurado_factura_sin_iva(client: TestClient, emisor_configurado):
    """Verifica que el ciclo de papelera y destrucción funciona correctamente en la carpeta Sin_IVA."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Ciclo Sin IVA", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-15",
        "sin_iva": True,
        "lineas": [{"descripcion": "Tutoría online", "cantidad": 1, "precio_unitario": 80.0, "porcentaje_iva": 0.0}]
    })
    fac_id = fac_res.json()["id"]
    numero = fac_res.json()["numero_factura"]

    path_sin = get_pdf_output_path(numero, "2026-10-15", sin_iva=True)
    assert path_sin.exists()
    assert "Sin_IVA" in path_sin.parts

    # 1. Enviar a papelera -> PDF borrado de disco
    client.delete(f"/api/facturas/{fac_id}")
    assert not path_sin.exists()

    # 2. Restaurar de papelera -> PDF regenerado en Sin_IVA
    client.post(f"/api/facturas/{fac_id}/restaurar")
    assert path_sin.exists()
    assert "Sin_IVA" in path_sin.parts

    # 3. Destruir permanentemente -> PDF borrado de disco
    client.delete(f"/api/facturas/{fac_id}/destruir")
    assert not path_sin.exists()
