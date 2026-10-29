import pytest
from starlette.testclient import TestClient
from app.services.pdf_service import get_pdf_output_path


def test_factura_pdf_lifecycle_soft_delete_restaurar_y_destruir(client: TestClient, emisor_configurado):
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Ciclo PDF S.L.", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    # 2. Crear factura
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-20",
        "lineas": [{"descripcion": "Desarrollo Software", "cantidad": 1, "precio_unitario": 500.0, "porcentaje_iva": 21.0}]
    })
    assert fac_res.status_code == 201
    fac_data = fac_res.json()
    fac_id = fac_data["id"]
    numero = fac_data["numero_factura"]

    # Comprobar que el archivo PDF físico existe en disco
    pdf_path = get_pdf_output_path(numero, "2026-10-20")
    assert pdf_path.exists(), f"El archivo PDF {pdf_path} debería existir tras crear la factura"

    # 3. Borrar factura (Soft delete / Enviar a papelera)
    del_res = client.delete(f"/api/facturas/{fac_id}")
    assert del_res.status_code == 200

    # Comprobar que el archivo PDF físico YA NO está en el directorio de facturación activa
    assert not pdf_path.exists(), f"El archivo PDF {pdf_path} NO debería existir en el explorador de archivos tras el borrado"

    # 4. Restaurar factura desde papelera
    res_rest = client.post(f"/api/facturas/{fac_id}/restaurar")
    assert res_rest.status_code == 200

    # Comprobar que el archivo PDF físico se ha vuelto a regenerar en disco
    assert pdf_path.exists(), f"El archivo PDF {pdf_path} debería regenerarse al restaurar la factura"

    # 5. Destruir definitivamente la factura
    res_dest = client.delete(f"/api/facturas/{fac_id}/destruir")
    assert res_dest.status_code == 200
    assert not pdf_path.exists(), f"El archivo PDF {pdf_path} no debe existir tras destrucción permanente"


def test_vaciar_papelera_elimina_pdfs_fisicos(client: TestClient, emisor_configurado):
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Vaciar Papelera", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-21",
        "lineas": [{"descripcion": "Auditoría de Sistemas", "cantidad": 1, "precio_unitario": 350.0, "porcentaje_iva": 21.0}]
    })
    fac_data = fac_res.json()
    numero = fac_data["numero_factura"]
    pdf_path = get_pdf_output_path(numero, "2026-10-21")

    # Simulamos que por alguna razón previa o legado el PDF estuviera en disco
    # Al crear la factura existe
    assert pdf_path.exists()

    # Si se vacía la papelera, todos los PDFs en papelera se purgan
    # Enviamos a papelera
    client.delete(f"/api/facturas/{fac_data['id']}")
    # Aseguramos que si recreamos el archivo manualmente para simular un remanente físico, vaciar papelera lo purga:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_text("dummy pdf content")
    assert pdf_path.exists()

    # Vaciar papelera
    res_vaciar = client.post("/api/papelera/vaciar")
    assert res_vaciar.status_code == 200
    assert not pdf_path.exists(), "El archivo PDF debe eliminarse al vaciar la papelera"


def test_eliminar_y_restaurar_cliente_cascada_sincroniza_pdfs(client: TestClient, emisor_configurado):
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Cascada PDF", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-22",
        "lineas": [{"descripcion": "Consultoría IT", "cantidad": 2, "precio_unitario": 100.0, "porcentaje_iva": 21.0}]
    })
    fac_data = fac_res.json()
    pdf_path = get_pdf_output_path(fac_data["numero_factura"], "2026-10-22")
    assert pdf_path.exists()

    # Borrado de cliente en cascada
    res_del_cli = client.delete(f"/api/clientes/{cli_id}")
    assert res_del_cli.status_code == 200
    assert not pdf_path.exists(), "El PDF de la factura debe eliminarse al borrar el cliente en cascada"

    # Restauración del cliente en cascada
    res_rest_cli = client.post(f"/api/clientes/{cli_id}/restaurar")
    assert res_rest_cli.status_code == 200
    assert pdf_path.exists(), "El PDF de la factura debe restaurarse automáticamente al recuperar el cliente"

    # Limpieza final
    client.delete(f"/api/facturas/{fac_data['id']}/destruir")
    assert not pdf_path.exists()
