import io
import pytest
import pypdf
from starlette.testclient import TestClient
from app.database import db_connection, get_configuracion
from app.services.pdf_service import generar_numero_factura, formatear_numero_factura


def test_formatear_numero_factura_casos():
    assert formatear_numero_factura("Factura Nº", 1) == "Factura Nº 1"
    assert formatear_numero_factura("Factura Nº ", 25) == "Factura Nº 25"
    assert formatear_numero_factura("FAC-", 100) == "FAC-100"
    assert formatear_numero_factura("F2026/", 5) == "F2026/5"
    assert formatear_numero_factura("SERIE_A", 7) == "SERIE_A-7"


def test_generar_numero_factura_secuencial_por_defecto(clean_database_tables):
    with db_connection() as conn:
        cli = conn.execute("INSERT INTO clientes (razon_social) VALUES ('Cliente Base')")
        cli_id = cli.lastrowid

        num1, corr1 = generar_numero_factura(conn)
        assert num1 == "Factura Nº 1"
        assert corr1 == 1

        # Simulamos que se inserta la factura 1
        conn.execute(
            """INSERT INTO facturas (numero_factura, serie, correlativo, fecha_emision, cliente_id, total_factura)
               VALUES (?, ?, ?, '2026-10-27', ?, 100.0)""",
            (num1, "Factura Nº", corr1, cli_id)
        )

        num2, corr2 = generar_numero_factura(conn)
        assert num2 == "Factura Nº 2"
        assert corr2 == 2


def test_numero_inicio_factura_configurable(client: TestClient, emisor_configurado):
    # 1. Configurar inicio en 100 y serie 'Factura Nº'
    res_cfg = client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "serie_defecto": "Factura Nº",
        "numero_inicio_factura": 100
    })
    assert res_cfg.status_code == 200
    cfg_data = res_cfg.json()["datos"]
    assert cfg_data["serie_defecto"] == "Factura Nº"
    assert cfg_data["numero_inicio_factura"] == 100

    # 2. Crear cliente
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Numeracion S.L.", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # 3. Emitir primera factura -> Debe ser 'Factura Nº 100'
    fac1_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "lineas": [{"descripcion": "Honorarios Profesionales", "cantidad": 1, "precio_unitario": 400.0, "porcentaje_iva": 21.0}]
    })
    assert fac1_res.status_code == 201
    fac1_data = fac1_res.json()
    assert fac1_data["numero_factura"] == "Factura Nº 100"

    # 4. Emitir segunda factura -> Debe ser 'Factura Nº 101'
    fac2_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "lineas": [{"descripcion": "Consultoría IT", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 21.0}]
    })
    assert fac2_res.status_code == 201
    fac2_data = fac2_res.json()
    assert fac2_data["numero_factura"] == "Factura Nº 101"

    # 5. Comprobar que en el PDF el encabezado renderiza limpiamente sin duplicados 'Nº Factura Nº'
    pdf_res = client.get(f"/api/facturas/{fac1_data['id']}/pdf")
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    texto_pdf = " ".join([page.extract_text() for page in reader.pages])

    assert "Factura Nº 100" in texto_pdf
    assert "Nº Factura Nº" not in texto_pdf
    assert "Concepto: Factura Factura" not in texto_pdf


def test_conversion_presupuesto_a_factura_utiliza_nueva_numeracion(client: TestClient, emisor_configurado):
    # 1. Configurar inicio en 50
    client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "serie_defecto": "Factura Nº",
        "numero_inicio_factura": 50
    })

    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Presupuesto Num", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    pres_res = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-NUM-01",
        "cliente_id": cli_id,
        "opciones": [{
            "nombre_opcion": "Opción Única",
            "lineas": [{"descripcion": "Instalación Eléctrica", "cantidad": 1, "precio_unitario": 600.0}]
        }]
    })
    pres_id = pres_res.json()["id"]
    op_id = pres_res.json()["opciones"][0]["id"]

    # Convertir a factura
    conv_res = client.post(f"/api/presupuestos/{pres_id}/convertir-factura", json={
        "opcion_id": op_id
    })
    assert conv_res.status_code == 200
    data_fac = conv_res.json()
    assert data_fac["numero_factura"] == "Factura Nº 50"


def test_numeracion_independiente_con_y_sin_iva(client: TestClient, emisor_configurado):
    """Verifica que las facturas con IVA y sin IVA llevan numeraciones y series independientes."""
    # 1. Configuración por defecto: Con IVA 'Factura Nº', Sin IVA 'Factura Sin IVA Nº'
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Doble Régimen", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # 2. Emitir Factura CON IVA 1 -> Factura Nº 1
    fac1_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Venta estándar con IVA", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0}]
    }).json()
    assert fac1_con["numero_factura"] == "Factura Nº 1"

    # 3. Emitir Factura SIN IVA 1 -> Factura Sin IVA Nº 1
    fac1_sin = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": True,
        "lineas": [{"descripcion": "Servicio formativo exento", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 0.0}]
    }).json()
    assert fac1_sin["numero_factura"] == "Factura Sin IVA Nº 1"

    # 4. Emitir Factura CON IVA 2 -> Factura Nº 2
    fac2_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Venta estándar 2", "cantidad": 1, "precio_unitario": 150.0, "porcentaje_iva": 21.0}]
    }).json()
    assert fac2_con["numero_factura"] == "Factura Nº 2"

    # 5. Emitir Factura SIN IVA 2 -> Factura Sin IVA Nº 2
    fac2_sin = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": True,
        "lineas": [{"descripcion": "Servicio médico exento", "cantidad": 1, "precio_unitario": 300.0, "porcentaje_iva": 0.0}]
    }).json()
    assert fac2_sin["numero_factura"] == "Factura Sin IVA Nº 2"


def test_configuracion_series_y_numeros_inicio_diferenciados(client: TestClient, emisor_configurado):
    """Verifica que se pueden personalizar series y números iniciales independientes para Con IVA y Sin IVA."""
    res_cfg = client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "serie_defecto": "F-IVA-",
        "numero_inicio_factura": 1000,
        "serie_sin_iva": "F-EXENTA-",
        "numero_inicio_factura_sin_iva": 500
    })
    assert res_cfg.status_code == 200

    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Series Custom", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # Factura con IVA
    f_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Producto General", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 21.0}]
    }).json()
    assert f_con["numero_factura"] == "F-IVA-1000"

    # Factura sin IVA
    f_sin = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": True,
        "lineas": [{"descripcion": "Curso Especializado", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 0.0}]
    }).json()
    assert f_sin["numero_factura"] == "F-EXENTA-500"

