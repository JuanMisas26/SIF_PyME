import io
import pytest
import pypdf
from datetime import date
from starlette.testclient import TestClient
from app.database import db_connection, get_configuracion
from app.services.pdf_service import generar_numero_factura, formatear_numero_factura


def test_formatear_numero_factura_casos():
    f = date(2026, 10, 27)
    assert formatear_numero_factura("FAC", 1, f) == "FAC-2026-10-27-001"
    assert formatear_numero_factura("FAC-", 25, f) == "FAC-2026-10-27-025"
    assert formatear_numero_factura("F/", 100, f) == "F-2026-10-27-100"
    assert formatear_numero_factura("FACTURA", 5, f) == "FACTURA-2026-10-27-005"
    assert formatear_numero_factura("INV", 1000, f) == "INV-2026-10-27-1000"


def test_generar_numero_factura_secuencial_por_defecto(clean_database_tables):
    with db_connection() as conn:
        cli = conn.execute("INSERT INTO clientes (razon_social) VALUES ('Cliente Base')")
        cli_id = cli.lastrowid

        fecha_test = "2026-10-27"
        num1, corr1 = generar_numero_factura(conn, fecha=fecha_test)
        assert num1 == "FAC-2026-10-27-001"
        assert corr1 == 1

        # Simulamos que se inserta la factura 1
        conn.execute(
            """INSERT INTO facturas (numero_factura, serie, correlativo, fecha_emision, cliente_id, total_factura)
               VALUES (?, 'FAC', ?, ?, ?, 100.0)""",
            (num1, corr1, fecha_test, cli_id)
        )

        num2, corr2 = generar_numero_factura(conn, fecha=fecha_test)
        assert num2 == "FAC-2026-10-27-002"
        assert corr2 == 2


def test_numero_inicio_factura_configurable(client: TestClient, emisor_configurado):
    # 1. Configurar inicio en 100 y prefijo 'FAC'
    res_cfg = client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "prefijo_factura": "FAC",
        "numero_inicio_factura": 100
    })
    assert res_cfg.status_code == 200
    cfg_data = res_cfg.json()["datos"]
    assert cfg_data["prefijo_factura"] == "FAC"
    assert cfg_data["numero_inicio_factura"] == 100

    # 2. Crear cliente
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Numeracion S.L.", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # 3. Emitir primera factura -> Debe ser 'FAC-2026-10-27-100'
    fac1_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "lineas": [{"descripcion": "Honorarios Profesionales", "cantidad": 1, "precio_unitario": 400.0, "porcentaje_iva": 21.0}]
    })
    assert fac1_res.status_code == 201
    fac1_data = fac1_res.json()
    assert fac1_data["numero_factura"] == "FAC-2026-10-27-100"

    # 4. Emitir segunda factura -> Debe ser 'FAC-2026-10-27-101'
    fac2_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "lineas": [{"descripcion": "Consultoría IT", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 21.0}]
    })
    assert fac2_res.status_code == 201
    fac2_data = fac2_res.json()
    assert fac2_data["numero_factura"] == "FAC-2026-10-27-101"

    # 5. Comprobar que en el PDF el encabezado renderiza limpiamente
    pdf_res = client.get(f"/api/facturas/{fac1_data['id']}/pdf")
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    texto_pdf = " ".join([page.extract_text() for page in reader.pages])

    assert "FAC-2026-10-27-100" in texto_pdf


def test_conversion_presupuesto_a_factura_utiliza_nueva_numeracion(client: TestClient, emisor_configurado):
    # 1. Configurar inicio en 50
    client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "prefijo_factura": "FAC",
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
    assert data_fac["numero_factura"].startswith("FAC-")
    assert data_fac["numero_factura"].endswith("-050")


def test_numeracion_unificada_con_y_sin_iva(client: TestClient, emisor_configurado):
    """Verifica que las facturas con IVA y sin IVA comparten la misma numeración unificada."""
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Doble Régimen", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # 1. Emitir Factura CON IVA 1 -> FAC-2026-10-27-001
    fac1_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Venta estándar con IVA", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0}]
    }).json()
    assert fac1_con["numero_factura"] == "FAC-2026-10-27-001"

    # 2. Emitir Factura SIN IVA 1 -> Sigue la correlación unificada: FAC-2026-10-27-002
    fac1_sin = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": True,
        "lineas": [{"descripcion": "Servicio formativo exento", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 0.0}]
    }).json()
    assert fac1_sin["numero_factura"] == "FAC-2026-10-27-002"

    # 3. Emitir Factura CON IVA 2 -> FAC-2026-10-27-003
    fac2_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Venta estándar 2", "cantidad": 1, "precio_unitario": 150.0, "porcentaje_iva": 21.0}]
    }).json()
    assert fac2_con["numero_factura"] == "FAC-2026-10-27-003"


def test_prefijo_configurable_personalizado(client: TestClient, emisor_configurado):
    """Verifica que se puede personalizar el prefijo configurable desde configuración."""
    res_cfg = client.post("/api/configuracion", json={
        "nombre": emisor_configurado["nombre"],
        "nif": emisor_configurado["nif"],
        "prefijo_factura": "INV",
        "numero_inicio_factura": 1
    })
    assert res_cfg.status_code == 200

    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Prefijo Custom", "nif_cif": "B10000008"})
    cli_id = cli_res.json()["id"]

    # Factura con IVA
    f_con = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": False,
        "lineas": [{"descripcion": "Producto General", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 21.0}]
    }).json()
    assert f_con["numero_factura"] == "INV-2026-10-27-001"

    # Factura sin IVA
    f_sin = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-27",
        "sin_iva": True,
        "lineas": [{"descripcion": "Curso Especializado", "cantidad": 1, "precio_unitario": 50.0, "porcentaje_iva": 0.0}]
    }).json()
    assert f_sin["numero_factura"] == "INV-2026-10-27-002"
