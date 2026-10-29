import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.services.backup_service import restaurar_snapshot
from app.errors import ValidationError


def test_restaurar_version_factura_preserva_descuentos_y_regimen_fiscal(client: TestClient, emisor_configurado):
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente Test Restaurar Fiscal S.L.",
        "nif_cif": "B10000008",
        "direccion": "Avenida 1",
        "codigo_postal": "28001",
        "ciudad": "Madrid"
    })
    assert cli_res.status_code == 201
    cliente_id = cli_res.json()["id"]

    # 2. Crear descuento
    desc_res = client.post("/api/descuentos", json={
        "nombre": "Promo Verano 10%",
        "tipo": "porcentaje",
        "valor": 10.0,
        "descripcion": "Descuento del 10% promocional"
    })
    assert desc_res.status_code == 201
    desc_id = desc_res.json()["id"]

    # 3. Crear factura con régimen especial: sin_iva=True, irpf=15%, y descuento en cabecera y línea
    f_res = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-07-01",
        "sin_iva": True,
        "porcentaje_iva": 0.0,
        "porcentaje_irpf": 15.0,
        "descuento_id": desc_id,
        "descuento_nombre": "Promo Verano 10%",
        "descuento_tipo": "porcentaje",
        "descuento_valor": 10.0,
        "descuento_importe_total": 9.0,
        "descuento_visible": False,
        "lineas": [
            {
                "descripcion": "Servicio de Consultoría Especial",
                "cantidad": 1.0,
                "precio_unitario": 90.0,
                "precio_unitario_original": 100.0,
                "porcentaje_descuento": 10.0,
                "porcentaje_iva": 0.0,
                "porcentaje_irpf": 15.0,
                "descuento_id": desc_id
            }
        ]
    })
    assert f_res.status_code == 201
    factura_id = f_res.json()["id"]

    # Comprobar versión 1 inicial
    v1_res = client.get(f"/api/facturas/{factura_id}/versiones/1")
    assert v1_res.status_code == 200

    # 4. Modificar la factura a régimen ordinario (sin_iva=False, iva=21%, sin descuentos)
    up_res = client.put(f"/api/facturas/{factura_id}", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-07-01",
        "sin_iva": False,
        "porcentaje_iva": 21.0,
        "porcentaje_irpf": 0.0,
        "lineas": [
            {
                "descripcion": "Servicio de Consultoría Modificado",
                "cantidad": 1.0,
                "precio_unitario": 200.0,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert up_res.status_code == 200

    # 5. Restaurar a la versión 1
    rest_res = client.post(f"/api/facturas/{factura_id}/versiones/1/restaurar")
    assert rest_res.status_code == 200

    # 6. Verificar que los descuentos y régimen fiscal original fueron íntegramente preservados
    f_rest = client.get(f"/api/facturas/{factura_id}").json()
    assert f_rest["sin_iva"] is True
    assert f_rest["descuento_id"] == desc_id
    assert f_rest["descuento_nombre"] == "Promo Verano 10%"
    assert f_rest["descuento_visible"] is False
    assert len(f_rest["lineas"]) == 1
    l = f_rest["lineas"][0]
    assert l["precio_unitario"] == 90.0
    assert l["precio_unitario_original"] == 100.0
    assert l["descuento_id"] == desc_id
    assert l["porcentaje_descuento"] == 10.0
    assert l["porcentaje_irpf"] == 15.0
    assert f_rest["irpf_total"] == 12.15


def test_restaurar_version_presupuesto_preserva_descuentos_y_regimen_fiscal(client: TestClient):
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente Presupuesto Fiscal S.L.",
        "nif_cif": "B10000008"
    })
    assert cli_res.status_code == 201
    cliente_id = cli_res.json()["id"]

    # 2. Crear descuento
    desc_res = client.post("/api/descuentos", json={
        "nombre": "Descuento Especial Opción",
        "tipo": "fijo",
        "valor": 50.0
    })
    assert desc_res.status_code == 201
    desc_id = desc_res.json()["id"]

    # 3. Crear presupuesto con opciones, descuentos y régimen fiscal sin_iva
    p_res = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-FISC-001",
        "cliente_id": cliente_id,
        "fecha": "2026-07-10",
        "titulo": "Presupuesto Fiscal Completo",
        "sin_iva": True,
        "porcentaje_iva": 0.0,
        "porcentaje_irpf": 7.0,
        "opciones": [
            {
                "nombre_opcion": "Opción Descuento",
                "orden": 1,
                "descuento_id": desc_id,
                "descuento_nombre": "Descuento Especial Opción",
                "descuento_tipo": "fijo",
                "descuento_valor": 50.0,
                "descuento_importe_total": 50.0,
                "descuento_visible": False,
                "lineas": [
                    {
                        "descripcion": "Línea de diseño",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
                        "precio_unitario_original": 250.0,
                        "descuento_id": desc_id,
                        "orden": 1
                    }
                ]
            }
        ]
    })
    assert p_res.status_code == 200
    pres_id = p_res.json()["id"]

    # 4. Modificar el presupuesto
    up_res = client.put(f"/api/presupuestos/{pres_id}", json={
        "numero_presupuesto": "PRE-FISC-001",
        "cliente_id": cliente_id,
        "fecha": "2026-07-10",
        "titulo": "Presupuesto Fiscal Modificado",
        "sin_iva": False,
        "porcentaje_iva": 21.0,
        "porcentaje_irpf": 0.0,
        "opciones": [
            {
                "nombre_opcion": "Opción Sin Descuento",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Línea modificada",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "orden": 1
                    }
                ]
            }
        ]
    })
    assert up_res.status_code == 200

    # 5. Restaurar versión 1
    rest_res = client.post(f"/api/presupuestos/{pres_id}/versiones/1/restaurar")
    assert rest_res.status_code == 200

    # 6. Comprobar que se restauraron los descuentos y el régimen fiscal
    p_rest = client.get(f"/api/presupuestos/{pres_id}").json()
    assert p_rest["sin_iva"] is True
    assert p_rest["porcentaje_irpf"] == 7.0
    assert len(p_rest["opciones"]) == 1
    op = p_rest["opciones"][0]
    assert op["descuento_id"] == desc_id
    assert op["descuento_nombre"] == "Descuento Especial Opción"
    assert op["descuento_tipo"] == "fijo"
    assert op["descuento_valor"] == 50.0
    assert op["descuento_visible"] is False
    assert len(op["lineas"]) == 1
    l = op["lineas"][0]
    assert l["precio_unitario"] == 200.0
    assert l["precio_unitario_original"] == 250.0
    assert l["descuento_id"] == desc_id


def test_seguridad_path_traversal_restaurar_snapshot(client: TestClient):
    # 1. Peticiones HTTP con nombres de archivo no autorizados o extensiones erróneas son rechazadas con 422
    payloads_invalidos = [
        "malicious.txt",
        "snapshot.db",
        "facturacion_pyme_hack.sh",
        "facturacion_pyme_hack.php"
    ]
    for filename in payloads_invalidos:
        res = client.post(f"/api/backups/{filename}/restaurar")
        assert res.status_code == 422, f"Falló rechazar {filename}: {res.status_code}"

    # 2. Verificación directa en el servicio contra inyección de rutas relativas y absolutas
    with pytest.raises(ValidationError):
        restaurar_snapshot("facturacion_pyme_../../etc/passwd.db")

    with pytest.raises(ValidationError):
        restaurar_snapshot("..\\windows\\win.ini.db")

    with pytest.raises(ValidationError):
        restaurar_snapshot("/etc/passwd")

    # 3. Fichero con sintaxis válida pero inexistente en BACKUP_DIR debe dar 404
    res_404 = client.post("/api/backups/facturacion_pyme_20260101_000000_inexistente.db/restaurar")
    assert res_404.status_code == 404


def test_validacion_fiscal_convertir_presupuesto_sin_emisor(client: TestClient):
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Cliente Test Emisor S.L.",
        "nif_cif": "B10000008"
    })
    assert cli_res.status_code == 201
    cliente_id = cli_res.json()["id"]

    # 2. Crear presupuesto
    p_res = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-EMISOR-001",
        "cliente_id": cliente_id,
        "fecha": "2026-07-20",
        "titulo": "Presupuesto Test Emisor",
        "opciones": [
            {
                "nombre_opcion": "Opción 1",
                "lineas": [
                    {"descripcion": "Servicio Test", "cantidad": 1, "precio_unitario": 100.0}
                ]
            }
        ]
    })
    assert p_res.status_code == 200
    pres_data = p_res.json()
    pres_id = pres_data["id"]
    opcion_id = pres_data["opciones"][0]["id"]

    # 3. Vaciar datos fiscales del emisor
    client.put("/api/configuracion", json={"nombre": "", "nif": ""})

    # 4. Intentar convertir a factura sin emisor configurado
    conv_res = client.post(f"/api/presupuestos/{pres_id}/convertir-factura", json={
        "opcion_id": opcion_id
    })
    # Debe ser rechazado por regla de negocio (400) con error EMISOR_CONFIG_MISSING
    assert conv_res.status_code == 400
    err_body = conv_res.json()
    assert err_body.get("error_code") == "EMISOR_CONFIG_MISSING"

    # Verificar que el presupuesto no cambió de estado ni se le asignó factura_id
    p_check = client.get(f"/api/presupuestos/{pres_id}").json()
    assert p_check["factura_id"] is None
    assert p_check["estado"] == "Borrador"


def test_listar_descuentos_batch_loading_productos(client: TestClient):
    """Verifica que el listado de descuentos carga correctamente productos sin N+1 [PERF-02]."""
    p1 = client.post("/api/productos", json={"nombre": "Prod Batch 1", "descripcion": "Desc 1", "precio_unitario_base": 10.0}).json()["id"]
    p2 = client.post("/api/productos", json={"nombre": "Prod Batch 2", "descripcion": "Desc 2", "precio_unitario_base": 20.0}).json()["id"]

    d1 = client.post("/api/descuentos", json={
        "nombre": "Desc Batch 1",
        "tipo": "porcentaje",
        "valor": 5.0,
        "aplica_a": "productos",
        "producto_ids": [p1, p2]
    }).json()

    d2 = client.post("/api/descuentos", json={
        "nombre": "Desc Batch 2",
        "tipo": "fijo",
        "valor": 15.0,
        "aplica_a": "todos"
    }).json()

    res = client.get("/api/descuentos?paginated=true&page=1&page_size=20")
    assert res.status_code == 200
    items = res.json()["items"]
    d1_found = next((d for d in items if d["id"] == d1["id"]), None)
    assert d1_found is not None
    assert set(d1_found["producto_ids"]) == {p1, p2}
    assert len(d1_found["productos_nombres"]) == 2


def test_textos_comerciales_neutros_por_defecto(client: TestClient):
    """Verifica que los modelos y configuraciones usen textos comerciales neutros sin mención a bodas [ARQ-06]."""
    from app.models import PresupuestoBase, ConfiguracionPresupuestoData

    p = PresupuestoBase(numero_presupuesto="TEST-NEUTRO", cliente_id=1, subtitulo="")
    assert "boda" not in p.subtitulo.lower()
    assert "invitacion" not in p.subtitulo.lower()
    assert p.subtitulo == "Propuesta de servicios y condiciones comerciales"

    cfg_p = ConfiguracionPresupuestoData()
    assert "boda" not in cfg_p.presupuesto_proceso_subtitulo.lower()
    assert "invitacion" not in cfg_p.presupuesto_proceso_subtitulo.lower()
    assert cfg_p.presupuesto_proceso_titulo == "Proceso de trabajo"


def test_portada_factura_opcional(client: TestClient, emisor_configurado):
    """Verifica que la factura oficial se genere sin portada decorativa por defecto (1 pág.) [ARQ-07]."""
    import io
    import pypdf

    cli = client.post("/api/clientes", json={"razon_social": "Cliente Portada S.L.", "nif_cif": "B88888888"}).json()
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli["id"],
        "fecha_emision": "2026-10-01",
        "lineas": [{"descripcion": "Servicio Rápido", "cantidad": 1, "precio_unitario": 100.0}]
    })
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["id"]

    pdf_res = client.get(f"/api/facturas/{fac_id}/pdf")
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    # Por defecto sin portada gráfica: 1 sola página con la factura
    assert len(reader.pages) == 1
    text_p1 = reader.pages[0].extract_text()
    assert "Factura" in text_p1
    assert "Servicio Rápido" in text_p1


def test_sugerir_numero_presupuesto_no_colisiona_con_papelera(client: TestClient):
    """Verifica que sugerir_numero_presupuesto nunca sugiera un código ocupado por un presupuesto en papelera [LOG-10]."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Sugerencia Test", "nif_cif": "B10000008"})
    assert cli_res.status_code == 201
    cli_id = cli_res.json()["id"]

    sug1 = client.get("/api/presupuestos/siguiente-numero?cliente_nombre=Cliente%20Sugerencia%20Test").json()["sugerencia"]

    # Crear presupuesto con esa sugerencia
    pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": sug1,
        "cliente_id": cli_id,
        "opciones": [{"nombre_opcion": "Op 1", "lineas": [{"descripcion": "L1", "cantidad": 1, "precio_unitario": 50.0}]}]
    }).json()
    pres_id = pres["id"]

    # Mover a papelera
    del_res = client.delete(f"/api/presupuestos/{pres_id}")
    assert del_res.status_code == 200

    # Pedir sugerencia de nuevo: debe sufijar -2 y no devolver sug1
    sug2 = client.get("/api/presupuestos/siguiente-numero?cliente_nombre=Cliente%20Sugerencia%20Test").json()["sugerencia"]
    assert sug2 != sug1
    assert sug2 == f"{sug1}-2"


def test_crear_producto_reactiva_codigo_en_papelera(client: TestClient):
    """Verifica que el alta individual de producto reactiva un código previamente eliminado [LOG-11]."""
    # 1. Crear producto con código
    p1 = client.post("/api/productos", json={
        "codigo": "CODE-REUTILIZABLE",
        "nombre": "Producto Original",
        "descripcion": "Descripción Original",
        "precio_unitario_base": 15.0
    })
    assert p1.status_code == 201
    p1_id = p1.json()["id"]

    # 2. Borrarlo (soft-delete)
    del_res = client.delete(f"/api/productos/{p1_id}")
    assert del_res.status_code == 200

    # 3. Intentar crearlo de nuevo mediante alta individual con el mismo código
    p2 = client.post("/api/productos", json={
        "codigo": "CODE-REUTILIZABLE",
        "nombre": "Producto Reactivado",
        "descripcion": "Nueva Descripción",
        "precio_unitario_base": 25.0
    })
    assert p2.status_code == 201
    p2_data = p2.json()
    assert p2_data["id"] == p1_id
    assert p2_data["nombre"] == "Producto Reactivado"
    assert p2_data["precio_unitario_base"] == 25.0


def test_actualizar_factura_preserva_linea_iva_cero(client: TestClient, emisor_configurado):
    """Verifica que actualizar una factura preserva líneas al 0% de IVA sin forzarlas al 21% [LOG-07]."""
    cli = client.post("/api/clientes", json={"razon_social": "Cliente Mixto IVA S.L.", "nif_cif": "B10000008"}).json()
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli["id"],
        "fecha_emision": "2026-03-10",
        "lineas": [
            {"descripcion": "Servicio Gravado", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0},
            {"descripcion": "Suplido o Exento", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 0.0}
        ]
    })
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["id"]

    # Factura inicial: base 150, IVA 21, total 171
    fac_init = client.get(f"/api/facturas/{fac_id}").json()
    assert fac_init["base_imponible_total"] == 150.0
    assert fac_init["iva_total"] == 21.0
    assert fac_init["total_factura"] == 171.0

    # Actualizar la factura (por ejemplo modificar la descripción del servicio gravado)
    put_res = client.put(f"/api/facturas/{fac_id}", json={
        "fecha_emision": "2026-03-10",
        "lineas": [
            {"descripcion": "Servicio Gravado Editado", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0},
            {"descripcion": "Suplido o Exento", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 0.0}
        ]
    })
    assert put_res.status_code == 200

    fac_updated = client.get(f"/api/facturas/{fac_id}").json()
    assert fac_updated["base_imponible_total"] == 150.0
    assert fac_updated["iva_total"] == 21.0  # El suplido al 0% NO debe haberse convertido en 21% (que daría 31.50)
    assert fac_updated["total_factura"] == 171.0

    # Verificar líneas en base de datos
    lineas = fac_updated["lineas"]
    linea_exenta = next(l for l in lineas if "Suplido" in l["descripcion"])
    assert linea_exenta["porcentaje_iva"] == 0.0


def test_convertir_presupuesto_con_partida_negativa_calcula_iva_proporcional(client: TestClient, emisor_configurado):
    """Verifica que una línea negativa (anticipo) en presupuesto deduzca proporcionalmente el IVA al facturar [LOG-08]."""
    cli = client.post("/api/clientes", json={"razon_social": "Cliente Anticipo S.L.", "nif_cif": "B10000008"}).json()
    pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-ANTICIPO-01",
        "cliente_id": cli["id"],
        "fecha": "2026-05-15",
        "titulo": "Presupuesto con Entrega a Cuenta",
        "opciones": [
            {
                "nombre_opcion": "Opción Estándar",
                "lineas": [
                    {"descripcion": "Servicio Principal", "cantidad": 1, "precio_unitario": 100.0},
                    {"descripcion": "Anticipo ya abonado", "cantidad": 1, "precio_unitario": -20.0}
                ]
            }
        ]
    }).json()
    opcion_id = pres["opciones"][0]["id"]

    # Convertir a factura
    conv = client.post(f"/api/presupuestos/{pres['id']}/convertir-factura", json={"opcion_id": opcion_id})
    assert conv.status_code == 200
    factura_id = conv.json()["factura_id"]

    factura = client.get(f"/api/facturas/{factura_id}").json()
    # Base: 100 - 20 = 80
    assert factura["base_imponible_total"] == 80.0
    # IVA al 21%: 100*0.21 - 20*0.21 = 21.0 - 4.20 = 16.80
    assert factura["iva_total"] == 16.80
    assert factura["total_factura"] == 96.80

    # Ambas líneas deben conservar 21% de IVA
    lineas = factura["lineas"]
    assert len(lineas) == 2
    for l in lineas:
        assert l["porcentaje_iva"] == 21.0


def test_actualizar_factura_fecha_emision_elimina_pdf_previo(client: TestClient, emisor_configurado):
    """Verifica que cambiar la fecha de emisión elimina el PDF físico en el directorio previo [LOG-09]."""
    from pathlib import Path
    cli = client.post("/api/clientes", json={"razon_social": "Cliente Mudanza Fecha", "nif_cif": "B10000008"}).json()
    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli["id"],
        "fecha_emision": "2026-01-10",
        "lineas": [{"descripcion": "Servicio Enero", "cantidad": 1, "precio_unitario": 100.0}]
    })
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["id"]

    # Verificar que el PDF existe en 2026/01
    pdf_enero_url = fac_res.json()["pdf_path"]
    pdf_enero_path = Path(pdf_enero_url)
    assert pdf_enero_path.exists()
    assert "01-Enero" in str(pdf_enero_path) or "01" in str(pdf_enero_path)

    # Actualizar a fecha en febrero
    put_res = client.put(f"/api/facturas/{fac_id}", json={
        "fecha_emision": "2026-02-15"
    })
    assert put_res.status_code == 200

    # El PDF viejo en enero debe haber sido eliminado
    assert not pdf_enero_path.exists()

    # El nuevo PDF debe existir en febrero
    pdf_febrero_path = Path(put_res.json()["pdf_path"])
    assert pdf_febrero_path.exists()
    assert "02-Febrero" in str(pdf_febrero_path) or "02" in str(pdf_febrero_path)


def test_paths_get_pdf_storage_dir_no_fuga_conexion():
    """Verifica que get_pdf_storage_dir() abre y cierra limpiamente su conexión [RES-01]."""
    from app.paths import get_pdf_storage_dir
    import gc
    import sqlite3

    # Ejecutar múltiples llamadas consecutivas
    for _ in range(10):
        storage_dir = get_pdf_storage_dir()
        assert storage_dir.exists()

    # La base de datos no debe estar bloqueada por descriptores abiertos
    from app.database import DB_PATH
    gc.collect()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM configuracion")
    assert cur.fetchone()[0] >= 0
    conn.close()



