import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    from app.database import set_configuracion
    set_configuracion({
        'nombre': 'Empresa Presupuestos S.L.',
        'nif': 'B10000008'
    })


def test_crear_presupuesto_editorial_con_opciones():
    # 1. Crear un cliente particular sin DNI con teléfono
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Silvia y Óscar",
        "telefono": "611223344",
        "email": "silviayoscar@boda.es"
    })
    assert res_cli.status_code in [200, 201]
    cliente = res_cli.json()
    cliente_id = cliente["id"]

    # 2. Sugerir número
    res_sug = client.get(f"/api/presupuestos/siguiente-numero?cliente_nombre={cliente['razon_social']}")
    assert res_sug.status_code == 200
    sugerencia = res_sug.json()["sugerencia"]
    assert "silvia-y-oscar" in sugerencia

    # 3. Crear Presupuesto con dos opciones comparativas
    payload = {
        "numero_presupuesto": sugerencia,
        "cliente_id": cliente_id,
        "fecha": "2026-10-18",
        "fecha_validez": "2026-11-18",
        "titulo": "Presupuesto para invitaciones",
        "subtitulo": "Precios para el diseño de invitaciones de boda",
        "estado": "Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción A - Sobre artesanal",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Tarjetón invitación con ilustración",
                        "detalle_material": "A5 Papel 300 gr verjurado premium",
                        "cantidad": 100,
                        "precio_unitario": 1.85
                    },
                    {
                        "descripcion": "Sobre artesanal",
                        "detalle_material": "C5 Papel artesanal",
                        "cantidad": 100,
                        "precio_unitario": 1.50
                    }
                ]
            },
            {
                "nombre_opcion": "Opción B - Sobre estándar",
                "orden": 2,
                "lineas": [
                    {
                        "descripcion": "Tarjetón invitación con ilustración",
                        "detalle_material": "A5 Papel 300 gr verjurado premium",
                        "cantidad": 100,
                        "precio_unitario": 1.85
                    },
                    {
                        "descripcion": "Sobre estándar",
                        "detalle_material": "Papel premium C5",
                        "cantidad": 100,
                        "precio_unitario": 0.72
                    }
                ]
            }
        ]
    }

    res_crear = client.post("/api/presupuestos", json=payload)
    assert res_crear.status_code == 200
    presupuesto = res_crear.json()
    assert presupuesto["numero_presupuesto"] == sugerencia
    assert len(presupuesto["opciones"]) == 2
    assert presupuesto["opciones"][0]["total"] == 335.0 # (100*1.85 + 100*1.50)
    assert presupuesto["opciones"][1]["total"] == 257.0 # (100*1.85 + 100*0.72)

    # 4. Listar presupuestos
    res_list = client.get("/api/presupuestos?q=Silvia")
    assert res_list.status_code == 200
    lista = res_list.json()
    assert len(lista) >= 1
    item = next(p for p in lista if p["id"] == presupuesto["id"])
    assert item["cliente_nombre"] == "Silvia y Óscar"
    assert item["total_minimo"] == 257.0
    assert item["total_maximo"] == 335.0
    assert item["cantidad_opciones"] == 2

    # 5. Generar y descargar PDF
    res_pdf = client.get(f"/api/presupuestos/{presupuesto['id']}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content[:4] == b"%PDF"
    assert len(res_pdf.content) > 50000 # contiene imágenes en alta resolución

    # 6. Convertir a Factura (eligiendo Opción A)
    opcion_a_id = presupuesto["opciones"][0]["id"]
    res_conv = client.post(f"/api/presupuestos/{presupuesto['id']}/convertir-factura", json={
        "opcion_id": opcion_a_id,
        "porcentaje_iva": 21.0,
        "porcentaje_irpf": 0.0,
        "tipo_facturacion": "total"
    })
    assert res_conv.status_code == 200
    conv_data = res_conv.json()
    assert conv_data["factura_id"] > 0
    assert ("Factura Nº" in conv_data["numero_factura"] or "FAC-" in conv_data["numero_factura"])
    # Total factura: 335 + 21% IVA (70.35) = 405.35
    assert conv_data["total_factura"] == 405.35

    # 7. Verificar que el presupuesto ahora tiene estado 'Facturado'
    res_ver = client.get(f"/api/presupuestos/{presupuesto['id']}")
    assert res_ver.status_code == 200
    pres_actualizado = res_ver.json()
    assert pres_actualizado["estado"] == "Facturado"
    assert pres_actualizado["factura_id"] == conv_data["factura_id"]

    # 8. Intentar reconvertir debe dar error de regla de negocio
    res_doble = client.post(f"/api/presupuestos/{presupuesto['id']}/convertir-factura", json={
        "opcion_id": opcion_a_id
    })
    assert res_doble.status_code in [400, 422]


def test_configuracion_presupuesto_editorial():
    res_get = client.get("/api/configuracion/presupuesto")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "presupuesto_instagram" in data
    assert "presupuesto_bienvenida_texto" in data

    # Actualizar instagram
    res_put = client.put("/api/configuracion/presupuesto", json={
        "presupuesto_instagram": "@empresa_demo_estudio",
        "presupuesto_email": "contacto@empresa-demo.com"
    })
    assert res_put.status_code == 200
    datos_actualizados = res_put.json()["datos"]
    assert datos_actualizados["presupuesto_instagram"] == "@empresa_demo_estudio"
    assert datos_actualizados["presupuesto_email"] == "contacto@empresa-demo.com"


def test_factura_pdf_editorial_estructura():
    import io
    import pypdf

    # 0. Configurar emisor
    client.put("/api/configuracion", json={
        "nombre": "Empresa Comercial Demo",
        "nif": "12345678Z",
        "direccion": "Calle Mayor 1",
        "codigo_postal": "28001",
        "ciudad": "Madrid",
        "factura_incluir_portada": "true"
    })

    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Demo SL",
        "telefono": "655443322",
        "email": "contacto@clientedemo.es"
    })
    cli_id = res_cli.json()["id"]

    # 2. Crear factura directamente
    res_fac = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-18",
        "lineas": [
            {
                "descripcion": "Diseño tarjetón botánico personalizado",
                "cantidad": 120,
                "precio_unitario": 2.10,
                "porcentaje_iva": 21.0
            },
            {
                "descripcion": "Sobre artesanal con forro vegetal",
                "cantidad": 120,
                "precio_unitario": 1.65,
                "porcentaje_iva": 21.0
            }
        ]
    })
    assert res_fac.status_code in [200, 201]
    fac_id = res_fac.json()["id"]

    # 3. Descargar PDF de la factura
    res_pdf = client.get(f"/api/facturas/{fac_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"

    # 4. Verificar estructura limpia de factura (Portada + Factura oficial, sin bienvenida ni proceso)
    reader = pypdf.PdfReader(io.BytesIO(res_pdf.content))
    assert len(reader.pages) == 2

    # Página 1 (Portada) debe contener el año y la palabra Factura
    text_p1 = reader.pages[0].extract_text()
    assert "2026" in text_p1
    assert "Factura" in text_p1

    # Página 2 (Hoja de Productos / Factura oficial)
    text_p2 = reader.pages[1].extract_text()
    assert ("Factura Nº" in text_p2 or "FAC-2026-" in text_p2)
    assert "TOTAL FACTURA" in text_p2
    assert "Cliente Demo SL" in text_p2


def test_presupuesto_n_opciones_Productos_independientes():
    # Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Carlos y Elena",
        "telefono": "677889900"
    })
    cli_id = res_cli.json()["id"]

    # Presupuesto con 3 opciones totalmente heterogéneas
    payload = {
        "numero_presupuesto": "2026-10-18-carlos-y-elena",
        "cliente_id": cli_id,
        "fecha": "2026-10-18",
        "titulo": "Presupuesto Invitaciones y Complementos",
        "subtitulo": "Opciones A (Completa), B (Básica) y C (Especial)",
        "estado": "Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción A - Invitación completa con lacre",
                "orden": 1,
                "lineas": [
                    {"descripcion": "Tarjetón A5", "detalle_material": "Papel verjurado 300g", "cantidad": 100, "precio_unitario": 2.0},
                    {"descripcion": "Sobre artesanal", "detalle_material": "C5 hecho a mano", "cantidad": 100, "precio_unitario": 1.5},
                    {"descripcion": "Sello de lacre", "detalle_material": "Personalizado", "cantidad": 1, "precio_unitario": 45.0}
                ]
            },
            {
                "nombre_opcion": "Opción B - Solo tarjetón digital y papel estándar",
                "orden": 2,
                "lineas": [
                    {"descripcion": "Tarjetón digital para WhatsApp", "detalle_material": "PDF interactivo", "cantidad": 1, "precio_unitario": 80.0}
                ]
            },
            {
                "nombre_opcion": "Opción C - Pack Deluxe con meseros y minutas",
                "orden": 3,
                "lineas": [
                    {"descripcion": "Tarjetón A5", "detalle_material": "Papel algodón", "cantidad": 150, "precio_unitario": 2.5},
                    {"descripcion": "Sobre forrado", "detalle_material": "Estampado botánico", "cantidad": 150, "precio_unitario": 1.8},
                    {"descripcion": "Minutas banquete", "detalle_material": "Papel 250g", "cantidad": 150, "precio_unitario": 1.2},
                    {"descripcion": "Meseros numerados", "detalle_material": "A6 papel verjurado", "cantidad": 15, "precio_unitario": 4.0}
                ]
            }
        ]
    }

    res = client.post("/api/presupuestos", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["opciones"]) == 3
    # Totales independientes
    assert data["opciones"][0]["total"] == 395.0 # 200 + 150 + 45
    assert data["opciones"][1]["total"] == 80.0  # 80
    assert data["opciones"][2]["total"] == 885.0 # 375 + 270 + 180 + 60

    # Convertir eligiendo la Opción C
    op_c_id = data["opciones"][2]["id"]
    res_conv = client.post(f"/api/presupuestos/{data['id']}/convertir-factura", json={
        "opcion_id": op_c_id,
        "porcentaje_iva": 21.0,
        "tipo_facturacion": "total"
    })
    assert res_conv.status_code == 200
    fac_id = res_conv.json()["factura_id"]

    # Verificar que la factura tiene las 4 líneas de la opción C
    res_fac = client.get(f"/api/facturas/{fac_id}")
    assert res_fac.status_code == 200
    fac_data = res_fac.json()
    assert len(fac_data["lineas"]) == 4
    assert fac_data["base_imponible_total"] == 885.0


def test_desbordamiento_muchos_Productos_paginacion():
    """Verifica que con más de 20 Productos no hay desbordamiento y se pagina correctamente."""
    import io
    import pypdf

    # 0. Asegurar emisor configurado
    client.put("/api/configuracion", json={
        "nombre": "Empresa Ingeniería S.L.",
        "nif": "12345678Z",
        "direccion": "Calle Mayor 1",
        "codigo_postal": "28001",
        "ciudad": "Madrid",
        "factura_incluir_portada": "true"
    })

    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Gran Volumen",
        "telefono": "611223344"
    })
    cli_id = res_cli.json()["id"]

    # 2. Factura con 24 Productos
    lineas_muchas = [
        {
            "descripcion": f"Servicio o Producto técnico de ingeniería #{i}",
            "cantidad": float(i),
            "precio_unitario": 15.50,
            "porcentaje_iva": 21.0
        } for i in range(1, 25)
    ]
    res_fac = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-18",
        "lineas": lineas_muchas
    })
    assert res_fac.status_code in [200, 201]
    fac_id = res_fac.json()["id"]

    res_pdf = client.get(f"/api/facturas/{fac_id}/pdf")
    assert res_pdf.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(res_pdf.content))
    # Al tener 24 Productos, debe paginar limpiamente (Portada + múltiples páginas de tabla)
    assert len(reader.pages) >= 3
    text_last = reader.pages[-1].extract_text()
    assert len(text_last) > 0


def test_presupuesto_opcion_aprobada_solo_esa_opcion_en_pdf():
    """Verifica que cuando una opción es aprobada, el PDF solo incluye esa opción y NO las rechazadas."""
    import io
    import pypdf

    res_cli = client.post("/api/clientes", json={
        "razon_social": "Empresa Seleccionadora",
        "telefono": "699001122"
    })
    cli_id = res_cli.json()["id"]

    # Crear presupuesto con Opción Alpha y Opción Beta
    payload = {
        "numero_presupuesto": f"2026-10-18-test-filtro-opcion-{cli_id}",
        "cliente_id": cli_id,
        "fecha": "2026-10-18",
        "titulo": "Propuesta con Variantes",
        "opciones": [
            {
                "nombre_opcion": "Opción Alpha Seleccionada",
                "lineas": [
                    {"descripcion": "Servicio Alpha Especial", "cantidad": 1, "precio_unitario": 500.0}
                ]
            },
            {
                "nombre_opcion": "Opción Beta Rechazada",
                "lineas": [
                    {"descripcion": "Servicio Beta Descartado", "cantidad": 1, "precio_unitario": 900.0}
                ]
            }
        ]
    }
    res_pres = client.post("/api/presupuestos", json=payload)
    pres_id = res_pres.json()["id"]
    op_alpha_id = res_pres.json()["opciones"][0]["id"]

    # 1. Antes de seleccionar, el PDF contiene ambas opciones
    res_pdf_todos = client.get(f"/api/presupuestos/{pres_id}/pdf")
    reader_todos = pypdf.PdfReader(io.BytesIO(res_pdf_todos.content))
    texto_todos = " ".join([p.extract_text() for p in reader_todos.pages])
    assert "Opción Alpha Seleccionada" in texto_todos or "OPCIÓN ALPHA SELECCIONADA" in texto_todos
    assert "Opción Beta Rechazada" in texto_todos or "OPCIÓN BETA RECHAZADA" in texto_todos

    # 2. Convertir / Aprobar la Opción Alpha
    res_conv = client.post(f"/api/presupuestos/{pres_id}/convertir-factura", json={
        "opcion_id": op_alpha_id,
        "porcentaje_iva": 21.0,
        "tipo_facturacion": "total"
    })
    assert res_conv.status_code == 200

    # 3. Tras aprobar, el PDF del presupuesto debe incluir ÚNICAMENTE la opción aprobada
    res_pdf_aprobado = client.get(f"/api/presupuestos/{pres_id}/pdf")
    reader_aprobado = pypdf.PdfReader(io.BytesIO(res_pdf_aprobado.content))
    texto_aprobado = " ".join([p.extract_text() for p in reader_aprobado.pages])
    assert "Opción Alpha Seleccionada" in texto_aprobado or "OPCIÓN ALPHA SELECCIONADA" in texto_aprobado
    assert "Opción Beta Rechazada" not in texto_aprobado
    assert "Servicio Beta Descartado" not in texto_aprobado


def test_textos_configuracion_personalizados_empresa():
    """Verifica que los textos personalizados de una empresa cualquiera aparecen en el PDF sin textos por defecto ajenos."""
    import io
    import pypdf

    # Configurar empresa de desarrollo de software con NIF válido
    res_cfg = client.put("/api/configuracion", json={
        "nombre": "Software Innovación S.L.",
        "nif": "12345678Z",
        "direccion": "Parque Tecnológico 4",
        "codigo_postal": "28050",
        "ciudad": "Madrid",
        "presupuesto_bienvenida_titulo": "Bienvenida Corporativa",
        "presupuesto_bienvenida_subtitulo": "Soluciones Cloud y Arquitectura",
        "presupuesto_bienvenida_texto": "Somos especialistas en desarrollo cloud para empresas globales.",
        "factura_condiciones": "Pago neto a 30 días según directiva europea de morosidad comercial.",
        "presupuesto_proceso_titulo": "Metodología Agile Scrum",
        "presupuesto_proceso_subtitulo": "Fases y entregables del proyecto",
        "proceso_fase1_titulo": "Definición y Alcance",
        "proceso_fase1_puntos": "• Requisitos iniciales\n• Planificación técnica\n• Aprobación de arquitectura",
        "proceso_fase4_puntos": "• Despliegue en producción\n• Facturación mensual\n• Soporte continuado",
        "presupuesto_proceso_cierre": "Compromiso de calidad técnica continua y soporte dedicado."
    })
    assert res_cfg.status_code == 200

    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Tech Global",
        "telefono": "600123456"
    })
    cli_id = res_cli.json()["id"]

    res_fac = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-18",
        "lineas": [
            {"descripcion": "Desarrollo Backend Python FastAPI", "cantidad": 40, "precio_unitario": 65.0, "porcentaje_iva": 21.0}
        ]
    })
    assert res_fac.status_code in [200, 201]
    fac_id = res_fac.json()["id"]

    res_pdf = client.get(f"/api/facturas/{fac_id}/pdf")
    reader = pypdf.PdfReader(io.BytesIO(res_pdf.content))
    texto_total = " ".join([p.extract_text() for p in reader.pages])

    assert "Software Innovación S.L." in texto_total
    assert "directiva europea de morosidad" in texto_total
    # Asegurar que en factura no hay bienvenida ni proceso
    assert "Bienvenida" not in texto_total
    assert "boda" not in texto_total.lower()
    assert "novios" not in texto_total.lower()
    assert "invitaciones" not in texto_total.lower()

    # Comprobar que el presupuesto generado es directo y limpio (sin portada, sin bienvenida y sin proceso)
    res_pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRES-CORP-01",
        "cliente_id": cli_id,
        "titulo": "Propuesta Cloud",
        "opciones": [{
            "nombre_opcion": "Opción Cloud",
            "lineas": [{"descripcion": "Arquitectura Cloud", "cantidad": 1, "precio_unitario": 1200.0}]
        }]
    })
    pres_id = res_pres.json()["id"]
    res_pres_pdf = client.get(f"/api/presupuestos/{pres_id}/pdf")
    reader_pres = pypdf.PdfReader(io.BytesIO(res_pres_pdf.content))
    texto_pres = " ".join([p.extract_text() for p in reader_pres.pages])
    assert "Arquitectura Cloud" in texto_pres
    assert "Cliente Tech Global" in texto_pres
    assert "PRES-CORP-01" in texto_pres
    assert "Bienvenida" not in texto_pres
    assert "Metodología Agile Scrum" not in texto_pres
    assert "Proceso de trabajo" not in texto_pres


def test_conversion_presupuesto_a_factura_genera_pdf_y_redireccion(client, emisor_configurado):
    """Verifica que convertir un presupuesto a factura genera el PDF real, no dummy, y redirige sin 404."""
    import io
    import pypdf

    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={
        "razon_social": "Empresa Cliente Real S.A.",
        "nif_cif": "A12345674",
        "telefono": "912345678",
        "email": "contacto@clientereal.com"
    })
    cli_id = cli_res.json()["id"]

    # 2. Crear presupuesto con una opción específica
    pres_payload = {
        "numero_presupuesto": "2026-10-18-cliente-real",
        "cliente_id": cli_id,
        "fecha": "2026-10-18",
        "titulo": "Servicios de Auditoría",
        "subtitulo": "Alcance y Fases",
        "opciones": [
            {
                "nombre_opcion": "Opción Integral",
                "lineas": [
                    {"descripcion": "Auditoría Financiera y Contable", "cantidad": 1, "precio_unitario": 1500.0}
                ]
            }
        ]
    }
    pres_res = client.post("/api/presupuestos", json=pres_payload)
    pres_id = pres_res.json()["id"]
    op_id = pres_res.json()["opciones"][0]["id"]

    # 3. Convertir a factura
    conv_res = client.post(f"/api/presupuestos/{pres_id}/convertir-factura", json={
        "opcion_id": op_id,
        "tipo_facturacion": "total"
    })
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    fac_id = conv_data["factura_id"]
    assert conv_data["redirect_url"] == f"/api/facturas/{fac_id}/pdf"

    # 4. Verificar redirección de la ruta amigable /facturas/{id}
    red_res = client.get(f"/facturas/{fac_id}", follow_redirects=False)
    assert red_res.status_code == 303
    assert red_res.headers["location"] == f"/api/facturas/{fac_id}/pdf"

    # 5. Descargar PDF y verificar que contiene los datos reales creados, no datos dummy
    pdf_res = client.get(f"/api/facturas/{fac_id}/pdf")
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    texto_pdf = " ".join([p.extract_text() for p in reader.pages])

    assert "Empresa Cliente Real S.A." in texto_pdf
    assert "Auditoría Financiera y Contable" in texto_pdf
    assert "1.500,00" in texto_pdf
    # No debe contener datos dummy ni de bodas
    assert "Cliente Tech Global" not in texto_pdf
    assert "Desarrollo Backend Python FastAPI" not in texto_pdf
    assert "boda" not in texto_pdf.lower()


def test_crear_presupuesto_titulo_vacio_usa_defecto(client):
    """Verifica que si el frontend envía título vacío o espacios, se usa el valor por defecto sin 422."""
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Título Vacío",
        "telefono": "654987321"
    })
    cli_id = res_cli.json()["id"]

    payload = {
        "numero_presupuesto": "2026-10-19-titulo-defecto",
        "cliente_id": cli_id,
        "fecha": "2026-10-19",
        "fecha_validez": "",
        "titulo": "   ",
        "subtitulo": "",
        "estado": "Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción Estándar",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Consultoría Técnica",
                        "detalle_material": "",
                        "cantidad": 2,
                        "precio_unitario": 150.0,
                        "orden": 1
                    }
                ]
            }
        ]
    }

    res = client.post("/api/presupuestos", json=payload)
    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    assert data["titulo"] == "Presupuesto de Servicios"
    assert data["subtitulo"] == "Propuesta de servicios y condiciones comerciales"
    assert data["fecha_validez"] is None


def test_crear_presupuesto_validacion_errores_etiquetas_espanol(client):
    """Verifica que ante errores reales de validación (422), las etiquetas y mensajes en español son claros."""
    payload_invalido = {
        "numero_presupuesto": "",
        "cliente_id": -1,
        "opciones": []
    }
    res = client.post("/api/presupuestos", json=payload_invalido)
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert len(data["errors"]) > 0
    # Comprobar que contiene mensajes amigables
    campos_err = [e["field"] for e in data["errors"]]
    assert "numero_presupuesto" in campos_err or "opciones" in campos_err





def test_actualizar_presupuesto_cambio_producto_y_descripcion(client):
    """Verifica que al actualizar una línea tras cambiar de producto del catálogo, la descripción y detalle se guardan correctamente."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Cambio Producto"})
    cli_id = res_cli.json()["id"]

    # Crear presupuesto con producto A (tiene nombre y descripción)
    payload = {
        "numero_presupuesto": "2026-10-19-cambio-prod",
        "cliente_id": cli_id,
        "fecha": "2026-10-19",
        "opciones": [
            {
                "nombre_opcion": "Opción 1",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Tarjetón invitación",
                        "detalle_material": "A5 Papel 300 gr verjurado",
                        "cantidad": 100,
                        "precio_unitario": 2.5,
                        "orden": 1
                    }
                ]
            }
        ]
    }
    res = client.post("/api/presupuestos", json=payload)
    assert res.status_code == 200
    pres_id = res.json()["id"]
    linea = res.json()["opciones"][0]["lineas"][0]
    assert linea["descripcion"] == "Tarjetón invitación"
    assert linea["detalle_material"] == "A5 Papel 300 gr verjurado"

    # Actualizar sustituyendo por producto B (que no tiene detalle_material)
    payload_update = {
        "numero_presupuesto": "2026-10-19-cambio-prod",
        "cliente_id": cli_id,
        "fecha": "2026-10-19",
        "opciones": [
            {
                "nombre_opcion": "Opción 1",
                "orden": 1,
                "lineas": [
                    {
                        "descripcion": "Sobre estándar sin forro",
                        "detalle_material": "",
                        "cantidad": 100,
                        "precio_unitario": 1.0,
                        "orden": 1
                    }
                ]
            }
        ]
    }
    res_up = client.put(f"/api/presupuestos/{pres_id}", json=payload_update)
    assert res_up.status_code == 200
    linea_up = res_up.json()["opciones"][0]["lineas"][0]
    assert linea_up["descripcion"] == "Sobre estándar sin forro"
    assert not linea_up["detalle_material"]


def test_cambiar_estado_presupuesto_aceptado_con_opcion_y_rechazado():
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Test Estado Presupuesto"})
    cli_id = res_cli.json()["id"]

    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-ESTADO-TEST-1",
        "cliente_id": cli_id,
        "fecha": "2026-10-21",
        "titulo": "Propuesta de Identidad Corporativa",
        "opciones": [
            {
                "nombre_opcion": "Opción 1: Básico",
                "lineas": [{"descripcion": "Logotipo", "cantidad": 1, "precio_unitario": 300}]
            },
            {
                "nombre_opcion": "Opción 2: Completo",
                "lineas": [{"descripcion": "Branding 360", "cantidad": 1, "precio_unitario": 800}]
            }
        ]
    })
    assert res_p.status_code == 200
    p_data = res_p.json()
    p_id = p_data["id"]
    opcion_2_id = p_data["opciones"][1]["id"]

    # 1. Marcar como Aceptado con Opción 2
    res_ac = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Aceptado",
        "opcion_aprobada_id": opcion_2_id,
        "motivo": "Cliente aprobó la Opción 2 por teléfono"
    })
    assert res_ac.status_code == 200
    assert res_ac.json()["estado"] == "Aceptado"
    assert res_ac.json()["opcion_aprobada_id"] == opcion_2_id

    # Comprobar detalle
    res_det = client.get(f"/api/presupuestos/{p_id}")
    assert res_det.status_code == 200
    assert res_det.json()["estado"] == "Aceptado"
    assert res_det.json()["opcion_aprobada_id"] == opcion_2_id
    assert res_det.json()["opcion_aprobada_nombre"] == "Opción 2: Completo"
    assert res_det.json()["opcion_aprobada_total"] == 800.0

    # Comprobar historial de versiones generado
    res_ver = client.get(f"/api/presupuestos/{p_id}/versiones")
    assert res_ver.status_code == 200
    versiones = res_ver.json()
    assert any("aprobó la Opción 2" in v["motivo"] for v in versiones)

    # 2. Marcar como Rechazado
    res_rech = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Rechazado",
        "motivo": "Cliente decide pausar el proyecto"
    })
    assert res_rech.status_code == 200
    assert res_rech.json()["estado"] == "Rechazado"

    # Comprobar en listado
    res_list = client.get(f"/api/presupuestos?q=PRE-ESTADO-TEST-1")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["estado"] == "Rechazado"
    assert res_list.json()[0]["opcion_aprobada_id"] == opcion_2_id
    assert res_list.json()[0]["opcion_aprobada_nombre"] == "Opción 2: Completo"
    assert res_list.json()[0]["opcion_aprobada_total"] == 800.0

    # 3. Validar error al enviar opción inválida
    res_inv = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Aceptado",
        "opcion_aprobada_id": 99999
    })
    assert res_inv.status_code == 404


def test_reabrir_presupuesto_facturado_a_borrador_y_cambiar_opcion(client):
    """
    Verifica que si un presupuesto se acepta y factura con la Opción 1,
    se puede regresar al estado Borrador (lo que cancela/mueve a papelera la factura anterior
    y limpia opcion_aprobada_id y factura_id), permitiendo luego aprobar y facturar
    la Opción 2 sin bloquearse.
    """
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Reabrir S.L."})
    cliente_id = res_cli.json()["id"]

    # Crear presupuesto con 2 opciones
    res_crear = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-REABRIR-001",
        "cliente_id": cliente_id,
        "fecha": "2026-10-21",
        "titulo": "Propuesta para Reabrir y Facturar",
        "estado": "Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción A (Básica)",
                "total": 300.0,
                "lineas": [
                    {"descripcion": "Servicio Básico", "cantidad": 1, "precio_unitario": 300.0, "total": 300.0}
                ]
            },
            {
                "nombre_opcion": "Opción B (Premium)",
                "total": 750.0,
                "lineas": [
                    {"descripcion": "Servicio Premium", "cantidad": 1, "precio_unitario": 750.0, "total": 750.0}
                ]
            }
        ]
    })
    assert res_crear.status_code in [200, 201]
    p_data = res_crear.json()
    p_id = p_data["id"]
    opcion_a_id = p_data["opciones"][0]["id"]
    opcion_b_id = p_data["opciones"][1]["id"]

    # 1. Facturar con Opción A
    res_fac1 = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={
        "opcion_id": opcion_a_id
    })
    assert res_fac1.status_code == 200
    fac1_id = res_fac1.json()["factura_id"]
    assert fac1_id is not None

    # Comprobar que está Facturado
    res_det1 = client.get(f"/api/presupuestos/{p_id}")
    assert res_det1.json()["estado"] == "Facturado"
    assert res_det1.json()["factura_id"] == fac1_id
    assert res_det1.json()["opcion_aprobada_id"] == opcion_a_id

    # 2. Reabrir a Borrador
    res_reabrir = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Borrador",
        "motivo": "Cliente prefiere la Opción Premium"
    })
    assert res_reabrir.status_code == 200
    assert res_reabrir.json()["estado"] == "Borrador"
    assert res_reabrir.json()["opcion_aprobada_id"] is None

    # Comprobar presupuesto reabierto
    res_det2 = client.get(f"/api/presupuestos/{p_id}")
    assert res_det2.json()["estado"] == "Borrador"
    assert res_det2.json()["factura_id"] is None
    assert res_det2.json()["opcion_aprobada_id"] is None

    # Comprobar que la factura anterior se envió a la papelera (is_deleted = 1)
    res_fac1_get = client.get(f"/api/facturas/{fac1_id}")
    assert res_fac1_get.status_code == 404  # Not found in active list because is_deleted=1

    # 3. Facturar con Opción B (Premium)
    res_fac2 = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={
        "opcion_id": opcion_b_id
    })
    assert res_fac2.status_code == 200
    fac2_id = res_fac2.json()["factura_id"]
    assert fac2_id != fac1_id

    # Comprobar que ahora está Facturado con Opción B y nuevo factura_id
    res_det3 = client.get(f"/api/presupuestos/{p_id}")
    assert res_det3.json()["estado"] == "Facturado"
    assert res_det3.json()["factura_id"] == fac2_id
    assert res_det3.json()["opcion_aprobada_id"] == opcion_b_id
    assert res_det3.json()["opcion_aprobada_nombre"] == "Opción B (Premium)"


def test_preview_pdf_sin_guardar(client):
    """Verifica que se puede previsualizar un PDF en vivo a partir de los datos en memoria del formulario."""
    preview_payload = {
        "numero_presupuesto": "PREVIEW-2026-LIVE",
        "cliente_nombre": "Cliente En Directo",
        "titulo": "Presupuesto en Tiempo Real",
        "subtitulo": "Sin guardar en base de datos",
        "opciones": [
            {
                "nombre_opcion": "Opción Vista Previa",
                "lineas": [
                    {
                        "descripcion": "Invitación personalizada en directo",
                        "detalle_material": "Papel de prueba",
                        "cantidad": 50,
                        "precio_unitario": 3.20
                    }
                ]
            }
        ]
    }
    res = client.post("/api/presupuestos/preview-pdf", json=preview_payload)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 10000
    assert res.content.startswith(b"%PDF")



def test_bloqueo_edicion_presupuesto_aceptado_o_facturado(client):
    """Verifica que un presupuesto Aceptado o Facturado no puede modificarse con PUT hasta volver a Borrador."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Bloqueo Edicion"})
    cli_id = res_cli.json()["id"]

    # 1. Crear presupuesto con 2 opciones
    payload = {
        "numero_presupuesto": "2026-10-24-bloqueo",
        "cliente_id": cli_id,
        "titulo": "Presupuesto Bloqueo Test",
        "opciones": [
            {
                "nombre_opcion": "Opción 1",
                "orden": 1,
                "lineas": [
                    {"descripcion": "Item 1", "cantidad": 10, "precio_unitario": 5.0, "orden": 1}
                ]
            },
            {
                "nombre_opcion": "Opción 2",
                "orden": 2,
                "lineas": [
                    {"descripcion": "Item 2", "cantidad": 20, "precio_unitario": 4.0, "orden": 1}
                ]
            }
        ]
    }
    res = client.post("/api/presupuestos", json=payload)
    assert res.status_code == 200
    p = res.json()
    p_id = p["id"]
    op1_id = p["opciones"][0]["id"]

    # 2. Aceptar Opción 1
    res_ac = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Aceptado",
        "opcion_aprobada_id": op1_id
    })
    assert res_ac.status_code == 200
    assert res_ac.json()["estado"] == "Aceptado"

    # Modificar el presupuesto con PUT mientras está Aceptado (sin facturar) -> permitido
    res_put_aceptado = client.put(f"/api/presupuestos/{p_id}", json={
        "titulo": "Presupuesto Aceptado Modificado",
        "opciones": [
            {
                "nombre_opcion": "Opción 1 Modificada",
                "orden": 1,
                "lineas": [
                    {"descripcion": "Item 1 Nuevo", "cantidad": 15, "precio_unitario": 6.0, "orden": 1}
                ]
            },
            {
                "nombre_opcion": "Opción 2",
                "orden": 2,
                "lineas": [
                    {"descripcion": "Item 2", "cantidad": 20, "precio_unitario": 4.0, "orden": 1}
                ]
            }
        ]
    })
    assert res_put_aceptado.status_code == 200
    assert res_put_aceptado.json()["titulo"] == "Presupuesto Aceptado Modificado"
    assert len(res_put_aceptado.json()["opciones"]) == 2
    assert res_put_aceptado.json()["opciones"][0]["nombre_opcion"] == "Opción 1 Modificada"
    op1_nuevo_id = res_put_aceptado.json()["opciones"][0]["id"]

    # Comprobar que el PDF se genera con éxito conteniendo las opciones
    res_pdf = client.get(f"/api/presupuestos/{p_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # 3. Facturar el presupuesto -> pasa a Facturado
    res_fac = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={
        "opcion_id": op1_nuevo_id
    })
    assert res_fac.status_code == 200
    fac_id = res_fac.json()["factura_id"]

    # Intentar modificar el presupuesto con PUT mientras está Facturado -> 400
    res_put_facturado = client.put(f"/api/presupuestos/{p_id}", json={
        "titulo": "Intento de Modificación Facturado"
    })
    assert res_put_facturado.status_code == 400
    assert "No se puede modificar directamente un presupuesto en estado 'Facturado'" in res_put_facturado.json()["detail"]

    # 4. Reabrir a Borrador mediante PATCH
    res_reabrir = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Borrador",
        "motivo": "Reabierto para prueba de edición"
    })
    assert res_reabrir.status_code == 200
    assert res_reabrir.json()["estado"] == "Borrador"
    assert res_reabrir.json()["opcion_aprobada_id"] is None

    # Comprobar que el presupuesto tiene factura_id = None y la factura está en papelera
    res_check = client.get(f"/api/presupuestos/{p_id}")
    assert res_check.json()["factura_id"] is None
    assert res_check.json()["opcion_aprobada_id"] is None
    res_fac_check = client.get(f"/api/facturas/{fac_id}")
    assert res_fac_check.status_code == 404  # papelera

    # 5. Ahora en Borrador, el PUT debe permitirse sin error
    res_put_ok = client.put(f"/api/presupuestos/{p_id}", json={
        "titulo": "Título Modificado en Borrador",
        "opciones": [
            {
                "nombre_opcion": "Opción Renovada",
                "orden": 1,
                "lineas": [
                    {"descripcion": "Item Renovado", "cantidad": 50, "precio_unitario": 10.0, "orden": 1}
                ]
            }
        ]
    })
    assert res_put_ok.status_code == 200
    data_mod = res_put_ok.json()
    assert data_mod["titulo"] == "Título Modificado en Borrador"
    assert len(data_mod["opciones"]) == 1
    assert data_mod["opciones"][0]["nombre_opcion"] == "Opción Renovada"


def test_guardar_impuestos_al_aceptar_presupuesto_y_convertir_sin_iva(client, emisor_configurado):
    """Verifica que al aceptar un presupuesto se persisten porcentaje_iva, porcentaje_irpf y sin_iva,
    y que al convertir a factura sin_iva se genera la factura exenta correctamente."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Aceptar Impuestos"})
    cli_id = res_cli.json()["id"]

    # 1. Crear presupuesto
    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "2026-10-24-test-impuestos",
        "cliente_id": cli_id,
        "fecha": "2026-10-24",
        "titulo": "Presupuesto con Impuestos Guardados",
        "opciones": [
            {
                "nombre_opcion": "Opción Principal",
                "orden": 1,
                "lineas": [
                    {"descripcion": "Diseño Editorial", "cantidad": 1, "precio_unitario": 500.0, "orden": 1}
                ]
            }
        ]
    })
    assert res_p.status_code == 200
    p_id = res_p.json()["id"]
    op_id = res_p.json()["opciones"][0]["id"]

    # 2. Aceptar el presupuesto especificando IRPF 15%, IVA 0%, sin_iva = True
    res_aceptar = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Aceptado",
        "opcion_aprobada_id": op_id,
        "porcentaje_iva": 0.0,
        "porcentaje_irpf": 15.0,
        "sin_iva": True
    })
    assert res_aceptar.status_code == 200

    # 3. Comprobar que los campos de impuestos quedaron guardados en la BD
    res_det = client.get(f"/api/presupuestos/{p_id}")
    assert res_det.status_code == 200
    p_data = res_det.json()
    assert p_data["estado"] == "Aceptado"
    assert p_data["porcentaje_iva"] == 0.0
    assert p_data["porcentaje_irpf"] == 15.0
    assert p_data["sin_iva"] is True

    # Comprobar también en el listado /api/presupuestos
    res_list = client.get(f"/api/presupuestos?q=2026-10-24-test-impuestos")
    assert res_list.status_code == 200
    item_list = res_list.json()[0]
    assert item_list["porcentaje_iva"] == 0.0
    assert item_list["porcentaje_irpf"] == 15.0
    assert item_list["sin_iva"] is True

    # 4. Convertir el presupuesto a factura usando la configuración sin IVA
    res_conv = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={
        "opcion_id": op_id,
        "porcentaje_iva": 0.0,
        "porcentaje_irpf": 15.0,
        "sin_iva": True
    })
    assert res_conv.status_code == 200
    conv_data = res_conv.json()
    fac_id = conv_data["factura_id"]

    # 5. Comprobar factura generada
    res_fac = client.get(f"/api/facturas/{fac_id}")
    assert res_fac.status_code == 200
    fac = res_fac.json()
    assert fac["sin_iva"] == 1 or fac["sin_iva"] is True
    assert fac["base_imponible_total"] == 500.0
    assert fac["iva_total"] == 0.0
    assert fac["irpf_total"] == 75.0  # 15% de 500
    assert fac["total_factura"] == 425.0  # 500 - 75


def test_reabrir_presupuesto_absorbe_cambios_de_factura_editada(client, emisor_configurado):
    """
    Verifica que si un presupuesto se factura, luego se edita la factura directamente
    y desde presupuestos se reabre a Borrador, el presupuesto absorbe las líneas,
    precios y configuraciones de impuestos de la factura, y la factura se mueve a la papelera.
    """
    res_cli = client.post("/api/clientes", json={"razon_social": "Novios Test Absorber"})
    cli_id = res_cli.json()["id"]

    # 1. Crear presupuesto con una opción y 1 línea
    res_p = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-2026-TEST-ABSORBER",
        "cliente_id": cli_id,
        "fecha": "2026-10-24",
        "titulo": "Invitaciones Originales",
        "opciones": [
            {
                "nombre_opcion": "Opción Principal",
                "orden": 1,
                "total": 250.0,
                "lineas": [
                    {"descripcion": "Invitaciones Clásicas", "cantidad": 100, "precio_unitario": 2.50, "total": 250.0, "orden": 1}
                ]
            }
        ]
    })
    assert res_p.status_code in [200, 201]
    p_data = res_p.json()
    p_id = p_data["id"]
    op_id = p_data["opciones"][0]["id"]

    # 2. Convertir a factura
    res_conv = client.post(f"/api/presupuestos/{p_id}/convertir-factura", json={
        "opcion_id": op_id,
        "tipo_facturacion": "total",
        "porcentaje_iva": 21.0
    })
    assert res_conv.status_code == 200
    fac_id = res_conv.json()["factura_id"]

    # 3. Editar la factura directamente: aumentar a 120 uds y añadir sobres forrados con sin_iva=True
    res_edit_fac = client.put(f"/api/facturas/{fac_id}", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-24",
        "sin_iva": True,
        "lineas": [
            {
                "descripcion": "Invitaciones Clásicas",
                "cantidad": 120,
                "precio_unitario": 2.50,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 0.0,
                "porcentaje_irpf": 0.0
            },
            {
                "descripcion": "Sobres Forrados Artesanales",
                "cantidad": 120,
                "precio_unitario": 1.00,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 0.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_edit_fac.status_code == 200
    fac_actualizada = client.get(f"/api/facturas/{fac_id}").json()
    assert fac_actualizada["base_imponible_total"] == 420.0  # (120 * 2.50 = 300) + (120 * 1.0 = 120)

    # 4. Reabrir el presupuesto a Borrador desde presupuestos
    res_reabrir = client.patch(f"/api/presupuestos/{p_id}/estado", json={
        "estado": "Borrador"
    })
    assert res_reabrir.status_code == 200
    reabrir_data = res_reabrir.json()
    assert reabrir_data["estado"] == "Borrador"
    assert reabrir_data["opcion_aprobada_id"] is None
    assert reabrir_data["factura_absorbida"] is True

    # 5. Comprobar que el presupuesto absorbió las 2 líneas y el nuevo total de la factura
    res_p_check = client.get(f"/api/presupuestos/{p_id}")
    assert res_p_check.status_code == 200
    p_check = res_p_check.json()
    assert p_check["estado"] == "Borrador"
    assert p_check["factura_id"] is None
    assert p_check["sin_iva"] is True

    op_actualizada = p_check["opciones"][0]
    assert op_actualizada["total"] == 420.0
    assert len(op_actualizada["lineas"]) == 2
    assert op_actualizada["lineas"][0]["descripcion"] == "Invitaciones Clásicas"
    assert op_actualizada["lineas"][0]["cantidad"] == 120
    assert op_actualizada["lineas"][0]["precio_unitario"] == 2.50
    assert op_actualizada["lineas"][0]["total"] == 300.0

    assert op_actualizada["lineas"][1]["descripcion"] == "Sobres Forrados Artesanales"
    assert op_actualizada["lineas"][1]["cantidad"] == 120
    assert op_actualizada["lineas"][1]["precio_unitario"] == 1.00
    assert op_actualizada["lineas"][1]["total"] == 120.0

    # 6. Comprobar que la factura antigua fue enviada a la papelera (soft-delete)
    res_fac_del = client.get(f"/api/facturas/{fac_id}")
    assert res_fac_del.status_code == 404


def test_conversion_presupuesto_con_anticipo_negativo_deduce_iva_proporcional():
    """Verifica que al convertir un presupuesto con partida negativa se mantenga el IVA e IRPF proporcional [LOG-08]."""
    # 1. Configurar emisor válido
    client.put("/api/configuracion", json={
        "nombre": "Estudio Creativo S.L.",
        "nif": "B10000008"
    })

    # 2. Cliente
    cli = client.post("/api/clientes", json={
        "razon_social": "Cliente con Anticipo S.L.",
        "nif_cif": "B10000008"
    }).json()

    # 3. Presupuesto con línea positiva y anticipo negativo
    pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": "PRE-ANTICIPO-PROP",
        "cliente_id": cli["id"],
        "fecha": "2026-06-01",
        "titulo": "Presupuesto con Entrega Inicial",
        "opciones": [
            {
                "nombre_opcion": "Completa",
                "lineas": [
                    {"descripcion": "Honorarios Proyecto", "cantidad": 1, "precio_unitario": 500.0},
                    {"descripcion": "Anticipo Reserva", "cantidad": 1, "precio_unitario": -100.0}
                ]
            }
        ]
    }).json()

    op_id = pres["opciones"][0]["id"]

    # 4. Convertir a factura con 21% IVA
    res_conv = client.post(f"/api/presupuestos/{pres['id']}/convertir-factura", json={
        "opcion_id": op_id,
        "porcentaje_iva": 21.0
    })
    assert res_conv.status_code == 200
    fac_id = res_conv.json()["factura_id"]

    fac = client.get(f"/api/facturas/{fac_id}").json()
    # Base = 500 - 100 = 400.0
    assert fac["base_imponible_total"] == 400.0
    # IVA = 500*0.21 - 100*0.21 = 105 - 21 = 84.0
    assert fac["iva_total"] == 84.0
    # Total = 484.0
    assert fac["total_factura"] == 484.0

