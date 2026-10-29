import pytest
from datetime import date


def test_api_clientes_validacion(client):
    # Cliente con CIF válido
    res = client.post("/api/clientes", json={
        "razon_social": "Cliente Pruebas Uno S.L.",
        "nif_cif": "B10000008",
        "direccion": "Avenida Diagonal, 10",
        "codigo_postal": "08001",
        "ciudad": "Barcelona",
        "provincia": "Barcelona",
        "email": "cliente1@pruebas.es"
    })
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["id"] > 0
    assert data["nif_cif"] == "B10000008"

    # Cliente con NIF inválido (debe rechazar con 422)
    res_invalido = client.post("/api/clientes", json={
        "razon_social": "Cliente Invalido",
        "nif_cif": "12345678A"  # Letra errónea
    })
    assert res_invalido.status_code == 422

    # Cliente con CP inválido (debe rechazar con 422)
    res_cp_invalido = client.post("/api/clientes", json={
        "razon_social": "Cliente CP Mal",
        "nif_cif": "12345678Z",
        "codigo_postal": "99999"
    })
    assert res_cp_invalido.status_code == 422


def test_api_facturas_requiere_emisor(client):
    # Crear cliente primero con NIF único
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Receptor Prueba Dos S.L.",
        "nif_cif": "87654321X"
    })
    assert res_cli.status_code == 201, res_cli.text
    cliente_id = res_cli.json()["id"]

    # Vaciar configuración intencionalmente para probar rechazo
    client.put("/api/configuracion", json={"nombre": "", "nif": ""})

    # Intentar emitir factura sin datos del emisor
    res_factura = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": str(date.today()),
        "lineas": [
            {
                "descripcion": "Servicio de consultoría técnica",
                "cantidad": 1.0,
                "precio_unitario": 500.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_factura.status_code == 400
    assert "debe configurar los datos fiscales de la empresa" in res_factura.json()["detail"]


def test_api_facturas_flujo_completo(client, emisor_configurado):
    # 1. Crear cliente con NIF único
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Empresa Cliente Final",
        "nif_cif": "11111111H",
        "direccion": "Calle Mayor 5",
        "codigo_postal": "28001",
        "ciudad": "Madrid"
    })
    assert res_cli.status_code == 201, res_cli.text
    cliente_id = res_cli.json()["id"]

    # 2. Intentar crear factura sin líneas (debe fallar con 422)
    res_sin_lineas = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": str(date.today()),
        "lineas": []
    })
    assert res_sin_lineas.status_code == 422

    # 3. Intentar fecha_vencimiento anterior a fecha_emision (debe fallar con 422)
    res_fechas_mal = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-06-10",
        "fecha_vencimiento": "2026-06-01",
        "lineas": [{"descripcion": "Item", "cantidad": 1.0, "precio_unitario": 10.0}]
    })
    assert res_fechas_mal.status_code == 422

    # 4. Crear factura válida
    payload_factura = {
        "cliente_id": cliente_id,
        "fecha_emision": "2026-06-01",
        "fecha_vencimiento": "2026-06-30",
        "observaciones": "Pago a 30 días",
        "estado": "Emitida",
        "lineas": [
            {
                "descripcion": "Desarrollo de Software a Medida",
                "cantidad": 10.0,
                "precio_unitario": 80.0,
                "porcentaje_descuento": 5.0,  # 800 - 40 = 760.00
                "porcentaje_iva": 21.0,       # 760 * 0.21 = 159.60
                "porcentaje_irpf": 15.0       # 760 * 0.15 = 114.00
            }
        ]
    }
    res_crear = client.post("/api/facturas", json=payload_factura)
    assert res_crear.status_code == 201, res_crear.text
    crear_data = res_crear.json()

    assert crear_data["id"] > 0
    assert crear_data["numero_factura"].startswith(("Factura Nº", "FAC-"))
    assert crear_data["total_factura"] == 805.60

    # 5. Listar facturas y verificar campos y cálculos persistidos
    res_listar = client.get("/api/facturas")
    assert res_listar.status_code == 200
    facturas = res_listar.json()
    assert len(facturas) >= 1

    factura_guardada = next(f for f in facturas if f["id"] == crear_data["id"])
    assert factura_guardada["correlativo"] >= 1
    assert factura_guardada["base_imponible_total"] == 760.00
    assert factura_guardada["iva_total"] == 159.60
    assert factura_guardada["irpf_total"] == 114.00
    assert factura_guardada["total_factura"] == 805.60
    assert factura_guardada["emisor_snapshot"] is not None

    # 6. Descargar / consultar PDF generado
    factura_id = crear_data["id"]
    res_pdf = client.get(f"/api/facturas/{factura_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000  # Archivo PDF binario generado


def test_api_cliente_particular_sin_dni(client):
    # Crear cliente 1 sin DNI (solo con teléfono y email)
    res1 = client.post("/api/clientes", json={
        "razon_social": "Juan Pérez Particular",
        "telefono": "654987321",
        "email": "juan.perez@email.com",
        "ciudad": "Valencia"
    })
    assert res1.status_code == 201, res1.text
    data1 = res1.json()
    assert data1["id"] > 0
    assert data1["nif_cif"] is None
    assert data1["telefono"] == "654987321"

    # Crear cliente 2 también sin DNI (verificar que no colisionan por restricción UNIQUE)
    res2 = client.post("/api/clientes", json={
        "razon_social": "María López Gómez",
        "telefono": "611222333"
    })
    assert res2.status_code == 201, res2.text
    data2 = res2.json()
    assert data2["id"] > 0
    assert data2["nif_cif"] is None

    # Búsqueda por teléfono
    res_busqueda_tel = client.get("/api/clientes?q=654987321")
    assert res_busqueda_tel.status_code == 200
    resultados = res_busqueda_tel.json()
    assert len(resultados) == 1
    assert resultados[0]["razon_social"] == "Juan Pérez Particular"

    # Búsqueda por email
    res_busqueda_email = client.get("/api/clientes?q=juan.perez")
    assert res_busqueda_email.status_code == 200
    assert len(res_busqueda_email.json()) == 1


def test_api_factura_cliente_particular(client, emisor_configurado):
    # Cliente particular sin DNI
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Carlos Santana Particular",
        "telefono": "699888777",
        "email": "carlos@santana.org"
    })
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    # Emitir factura para particular
    res_fac = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-07-01",
        "lineas": [
            {
                "descripcion": "Reparación de equipo informático",
                "cantidad": 1.0,
                "precio_unitario": 120.0,
                "porcentaje_iva": 21.0
            }
        ]
    })
    assert res_fac.status_code == 201
    fac_data = res_fac.json()
    assert fac_data["id"] > 0
    assert fac_data["total_factura"] == 145.20

    # Descargar PDF y verificar generación correcta
    res_pdf = client.get(f"/api/facturas/{fac_data['id']}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000


def test_api_errores_tipificados(client):
    # 1. Error de validación estructurado (422)
    res_val = client.post("/api/clientes", json={
        "razon_social": "",  # Campo obligatorio vacío
        "nif_cif": "12345678A"  # NIF inválido
    })
    assert res_val.status_code == 422
    data_val = res_val.json()
    assert data_val["error_code"] == "VALIDATION_ERROR"
    assert "errors" in data_val and len(data_val["errors"]) > 0
    campos_con_error = [e["field"] for e in data_val["errors"]]
    assert "razon_social" in campos_con_error or "nif_cif" in campos_con_error

    # 2. Conflicto por duplicidad estructurado (409)
    client.post("/api/clientes", json={
        "razon_social": "Cliente Original",
        "nif_cif": "12345678Z"
    })
    res_dup = client.post("/api/clientes", json={
        "razon_social": "Cliente Clon",
        "nif_cif": "12345678Z"
    })
    assert res_dup.status_code == 409
    data_dup = res_dup.json()
    assert data_dup["error_code"] == "CONFLICT"
    assert "Ya existe un cliente registrado" in data_dup["detail"]

    # 3. No encontrado estructurado (404)
    res_nf = client.get("/api/clientes/999999")
    assert res_nf.status_code == 404
    data_nf = res_nf.json()
    assert data_nf["error_code"] == "NOT_FOUND"


def test_eliminar_factura_borrado_logico(client, emisor_configurado):
    """Verifica que eliminar una factura realiza un borrado lógico (is_deleted=1) y la oculta de listados."""
    # 1. Crear cliente y factura
    cli_res = client.post("/api/clientes", json={"razon_social": "Cliente Test Factura Borrado"})
    cli_id = cli_res.json()["id"]

    fac_res = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-19",
        "lineas": [{"descripcion": "Servicio de Consultoría", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 21.0}]
    })
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["id"]

    # Verificar que aparece en el listado
    listar1 = client.get("/api/facturas").json()
    assert any(f["id"] == fac_id for f in listar1)

    # 2. Eliminar factura (borrado lógico)
    del_res = client.delete(f"/api/facturas/{fac_id}")
    assert del_res.status_code == 200

    # 3. Verificar que ya no aparece en el listado de facturas activas
    listar2 = client.get("/api/facturas").json()
    assert not any(f["id"] == fac_id for f in listar2)

    # 4. Intentar descargar el PDF o consultarla devuelve 404
    res_pdf = client.get(f"/api/facturas/{fac_id}/pdf")
    assert res_pdf.status_code == 404


def test_eliminar_cliente_en_cascada_con_presupuestos_y_facturas(client, emisor_configurado):
    """Verifica aviso previo de asociados y borrado lógico en cascada de presupuestos y facturas al eliminar un cliente."""
    # 1. Crear cliente
    cli_res = client.post("/api/clientes", json={"razon_social": "Empresa Integral Borrado S.L."})
    cli_id = cli_res.json()["id"]

    # 2. Crear factura vinculada
    client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-19",
        "lineas": [{"descripcion": "Mantenimiento Servidores", "cantidad": 1, "precio_unitario": 500.0, "porcentaje_iva": 21.0}]
    })

    # 3. Crear presupuesto vinculado
    client.post("/api/presupuestos", json={
        "numero_presupuesto": "2026-10-19-empresa-integral",
        "cliente_id": cli_id,
        "fecha": "2026-10-19",
        "titulo": "Renovación Infraestructura",
        "opciones": [{
            "nombre_opcion": "Opción Cloud",
            "lineas": [{"descripcion": "Migración Cloud", "cantidad": 1, "precio_unitario": 1200.0}]
        }]
    })

    # 4. Consultar endpoint de asociados para aviso previo
    asociados_res = client.get(f"/api/clientes/{cli_id}/asociados")
    assert asociados_res.status_code == 200
    asoc_data = asociados_res.json()
    assert asoc_data["total_facturas"] == 1
    assert asoc_data["total_presupuestos"] == 1

    # 5. Eliminar cliente en cascada
    del_cli_res = client.delete(f"/api/clientes/{cli_id}")
    assert del_cli_res.status_code == 200
    del_data = del_cli_res.json()
    assert del_data["facturas_eliminadas"] == 1
    assert del_data["presupuestos_eliminados"] == 1

    # 6. Comprobar que cliente, facturas y presupuestos no aparecen en listados activos
    clientes_activos = client.get("/api/clientes").json()
    assert not any(c["id"] == cli_id for c in clientes_activos)

    facturas_activas = client.get("/api/facturas").json()
    assert not any(f["cliente_id"] == cli_id for f in facturas_activas)

    presupuestos_activos = client.get("/api/presupuestos").json()
    assert not any(p["cliente_id"] == cli_id for p in presupuestos_activos)

    # 7. Restaurar cliente y comprobar que recupera sus documentos
    rest_res = client.post(f"/api/clientes/{cli_id}/restaurar")
    assert rest_res.status_code == 200

    assert any(c["id"] == cli_id for c in client.get("/api/clientes").json())
    assert any(f["cliente_id"] == cli_id for f in client.get("/api/facturas").json())
    assert any(p["cliente_id"] == cli_id for p in client.get("/api/presupuestos").json())


def test_api_contadores(client):
    res = client.get("/api/contadores")
    assert res.status_code == 200
    data = res.json()
    assert "facturas" in data
    assert "presupuestos" in data
    assert "clientes" in data
    assert "productos" in data
    assert isinstance(data["facturas"], int)
    assert isinstance(data["presupuestos"], int)
    assert isinstance(data["clientes"], int)
    assert isinstance(data["productos"], int)


def test_actualizar_factura_completa(client, emisor_configurado):
    # Crear cliente inicial
    res_c1 = client.post("/api/clientes", json={
        "razon_social": "Cliente Original S.L.",
        "nif_cif": "B12345674"
    })
    c1_id = res_c1.json()["id"]

    # Crear factura inicial
    res_factura = client.post("/api/facturas", json={
        "cliente_id": c1_id,
        "fecha_emision": "2026-10-20",
        "estado": "Borrador",
        "observaciones": "Primera versión",
        "lineas": [
            {
                "descripcion": "Diseño de identidad visual",
                "cantidad": 1.0,
                "precio_unitario": 200.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_factura.status_code == 201
    factura_id = res_factura.json()["id"]
    assert res_factura.json()["total_factura"] == 242.0

    # Crear cliente alternativo para cambio
    res_c2 = client.post("/api/clientes", json={
        "razon_social": "Cliente Modificado S.L.",
        "nif_cif": "12345678Z"
    })
    assert res_c2.status_code == 201
    c2_id = res_c2.json()["id"]

    # Actualizar la factura completa
    res_put = client.put(f"/api/facturas/{factura_id}", json={
        "cliente_id": c2_id,
        "fecha_emision": "2026-10-21",
        "fecha_vencimiento": "2026-11-21",
        "estado": "Emitida",
        "observaciones": "Versión corregida y ampliada",
        "lineas": [
            {
                "descripcion": "Diseño de identidad visual ampliado",
                "cantidad": 2.0,
                "precio_unitario": 300.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            },
            {
                "descripcion": "Manual de marca",
                "cantidad": 1.0,
                "precio_unitario": 100.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_put.status_code == 200, res_put.text
    put_data = res_put.json()
    # Base: 600 + 100 = 700. IVA 21%: 147. Total: 847
    assert put_data["total_factura"] == 847.0

    # Comprobar que GET /api/facturas/{id} devuelve los datos actualizados
    res_get = client.get(f"/api/facturas/{factura_id}")
    assert res_get.status_code == 200
    factura_get = res_get.json()
    assert factura_get["cliente_id"] == c2_id
    assert factura_get["cliente_razon_social"] == "Cliente Modificado S.L."
    assert factura_get["estado"] == "Emitida"
    assert factura_get["fecha_emision"] == "2026-10-21"
    assert factura_get["fecha_vencimiento"] == "2026-11-21"
    assert factura_get["observaciones"] == "Versión corregida y ampliada"
    assert len(factura_get["lineas"]) == 2
    assert factura_get["total_factura"] == 847.0

    # Comprobar que la vista HTML de edición responde 200
    res_html = client.get(f"/facturas/{factura_id}/editar")
    assert res_html.status_code == 200
    assert "Editar Factura" in res_html.text





def test_lineas_factura_detalle_material_separado(client, emisor_configurado):
    # Emisor
    client.put('/api/configuracion', json={
        'nombre': 'Estudio Creativo S.L.',
        'nif': 'B12345678',
        'direccion': 'Calle Mayor 1',
        'ciudad': 'Madrid'
    })

    # Cliente
    res_c = client.post('/api/clientes', json={
        'razon_social': 'Cliente Detalle Separado S.L.',
        'nif_cif': 'X0000001R'
    })
    cli_id = res_c.json()['id']

    # Crear factura con descripcion y detalle_material separados
    res_post = client.post('/api/facturas', json={
        'cliente_id': cli_id,
        'fecha_emision': '2026-10-21',
        'lineas': [
            {
                'descripcion': 'Tarjetón Invitación',
                'detalle_material': 'A5 Papel 300 gr / acabado mate',
                'cantidad': 100.0,
                'precio_unitario': 2.50,
                'porcentaje_iva': 21.0,
                'porcentaje_irpf': 0.0
            }
        ]
    })
    assert res_post.status_code == 201, res_post.text
    fact_id = res_post.json()['id']

    # Verificar que el GET no incluye paréntesis en la descripción
    res_get = client.get(f'/api/facturas/{fact_id}')
    assert res_get.status_code == 200
    data = res_get.json()
    linea = data['lineas'][0]
    assert linea['descripcion'] == 'Tarjetón Invitación'
    assert '(' not in linea['descripcion']
    assert linea['detalle_material'] == 'A5 Papel 300 gr / acabado mate'

    # Editar la factura cambiando el detalle sin alterar la descripción
    res_put = client.put(f'/api/facturas/{fact_id}', json={
        'lineas': [
            {
                'descripcion': 'Tarjetón Invitación',
                'detalle_material': 'A5 Papel 350 gr verjurado',
                'cantidad': 120.0,
                'precio_unitario': 2.60,
                'porcentaje_iva': 21.0,
                'porcentaje_irpf': 0.0
            }
        ]
    })
    assert res_put.status_code == 200, res_put.text
    res_get2 = client.get(f'/api/facturas/{fact_id}')
    assert res_get2.status_code == 200
    linea_put = res_get2.json()['lineas'][0]
    assert linea_put['descripcion'] == 'Tarjetón Invitación'
    assert '(' not in linea_put['descripcion']
    assert linea_put['detalle_material'] == 'A5 Papel 350 gr verjurado'



def test_crear_factura_linea_precio_negativo(client, emisor_configurado):
    """Verifica que se puede emitir una factura con una línea negativa (anticipo/descuento) y que no calcula IVA ni IRPF sobre ella."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Factura Negativo"})
    cli_id = res_cli.json()["id"]

    factura_data = {
        "serie": "FAC-2026",
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-24",
        "lineas": [
            {
                "descripcion": "Servicio de diseño y papelería",
                "cantidad": 1.0,
                "precio_unitario": 300.0,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 15.0
            },
            {
                "descripcion": "Anticipo ya transferido",
                "cantidad": 1.0,
                "precio_unitario": -100.0,
                "porcentaje_descuento": 0.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 15.0
            }
        ]
    }

    res = client.post("/api/facturas", json=factura_data)
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["total_factura"] == 212.00

    # Comprobar los totales completos y las líneas mediante GET
    res_get = client.get(f"/api/facturas/{created['id']}")
    assert res_get.status_code == 200
    data = res_get.json()

    assert data["base_imponible_total"] == 200.00
    # 21% neto sobre 200.0 (300 - 100) = 42.00
    assert data["iva_total"] == 42.00
    # 15% neto sobre 200.0 (300 - 100) = 30.00
    assert data["irpf_total"] == 30.00
    # Total = 200 (base) + 42 (iva) - 30 (irpf) = 212.00 €
    assert data["total_factura"] == 212.00

    # Comprobar que en la BD la línea negativa preserva su 21% IVA y 15% IRPF
    lineas = data["lineas"]
    neg_line = [l for l in lineas if l["precio_unitario"] < 0][0]
    assert neg_line["porcentaje_iva"] == 21.0
    assert neg_line["porcentaje_irpf"] == 15.0


def test_factura_sin_iva_y_filtrado_y_pdf(client, emisor_configurado):
    """Verifica emisión de facturas sin IVA, separación en filtrado (SIN_IVA vs CON_IVA) y texto en PDF."""
    import pypdf
    import io

    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Régimen Exento"})
    cli_id = res_cli.json()["id"]

    # 1. Crear factura con IVA normal (21%)
    res_con_iva = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-24",
        "sin_iva": False,
        "lineas": [
            {"descripcion": "Servicio con IVA", "cantidad": 1, "precio_unitario": 100.0, "porcentaje_iva": 21.0}
        ]
    })
    assert res_con_iva.status_code == 201
    fac_con_iva_id = res_con_iva.json()["id"]

    # 2. Crear factura sin IVA (sin_iva: True)
    res_sin_iva = client.post("/api/facturas", json={
        "cliente_id": cli_id,
        "fecha_emision": "2026-10-24",
        "sin_iva": True,
        "lineas": [
            {"descripcion": "Formación exenta", "cantidad": 1, "precio_unitario": 200.0, "porcentaje_iva": 21.0}
        ]
    })
    assert res_sin_iva.status_code == 201
    fac_sin_iva_data = res_sin_iva.json()
    fac_sin_iva_id = fac_sin_iva_data["id"]

    assert fac_sin_iva_data["sin_iva"] == 1 or fac_sin_iva_data["sin_iva"] is True
    assert fac_sin_iva_data["iva_total"] == 0.0
    assert fac_sin_iva_data["total_factura"] == 200.0

    # 3. Probar filtrado por estado=SIN_IVA
    res_filtro_sin = client.get("/api/facturas?estado=SIN_IVA")
    assert res_filtro_sin.status_code == 200
    ids_sin = [f["id"] for f in res_filtro_sin.json()]
    assert fac_sin_iva_id in ids_sin
    assert fac_con_iva_id not in ids_sin

    # 4. Probar filtrado por estado=CON_IVA
    res_filtro_con = client.get("/api/facturas?estado=CON_IVA")
    assert res_filtro_con.status_code == 200
    ids_con = [f["id"] for f in res_filtro_con.json()]
    assert fac_con_iva_id in ids_con
    assert fac_sin_iva_id not in ids_con

    # 5. Comprobar que en el PDF de la factura sin IVA se indica 'IVA (0% Exento):'
    pdf_res = client.get(f"/api/facturas/{fac_sin_iva_id}/pdf")
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    texto_pdf = " ".join([p.extract_text() for p in reader.pages])
    assert "0% Exento" in texto_pdf


def test_get_pdf_output_path_formato_mes_y_trimestre():
    """Verifica que las carpetas de guardado de PDFs se estructuran por año, trimestre (1T, 2T, 3T, 4T) y mes (01_Enero, etc.)."""
    from app.services.pdf_service import get_pdf_output_path

    meses_esperados = [
        ("2026-01-15", "1T", "01_Enero"),
        ("2026-02-10", "1T", "02_Febrero"),
        ("2026-03-22", "1T", "03_Marzo"),
        ("2026-04-05", "2T", "04_Abril"),
        ("2026-05-18", "2T", "05_Mayo"),
        ("2026-06-30", "2T", "06_Junio"),
        ("2026-07-07", "3T", "07_Julio"),
        ("2026-08-14", "3T", "08_Agosto"),
        ("2026-09-01", "3T", "09_Septiembre"),
        ("2026-10-26", "4T", "10_Octubre"),
        ("2026-11-11", "4T", "11_Noviembre"),
        ("2026-12-25", "4T", "12_Diciembre"),
    ]

    for fecha_str, trimestre_esperado, mes_esperado in meses_esperados:
        path = get_pdf_output_path("FAC-TEST-MES", fecha_str)
        assert "2026" in path.parts
        assert trimestre_esperado in path.parts
        assert mes_esperado in path.parts
        assert "Con_IVA" in path.parts
        assert path.name == "FAC-TEST-MES.pdf"

        path_sin = get_pdf_output_path("FAC-TEST-MES", fecha_str, sin_iva=True)
        assert "2026" in path_sin.parts
        assert trimestre_esperado in path_sin.parts
        assert mes_esperado in path_sin.parts
        assert "Sin_IVA" in path_sin.parts
        assert path_sin.name == "FAC-TEST-MES.pdf"


def test_get_pdf_output_path_migracion_automatica_ruta_antigua(tmp_path, monkeypatch):
    """Verifica que si existía un PDF en la ruta antigua '2026/10' o '2026/10_Octubre', se migra a '2026/4T/10_Octubre'."""
    from app.services.pdf_service import get_pdf_output_path
    import app.paths as paths_mod

    monkeypatch.setattr(paths_mod, "get_pdf_storage_dir", lambda: tmp_path)

    # 1. Caso ruta antigua: tmp_path / "2026" / "10" / "FAC-OLD1.pdf"
    old_dir_raw = tmp_path / "2026" / "10"
    old_dir_raw.mkdir(parents=True, exist_ok=True)
    old_file_raw = old_dir_raw / "FAC-OLD1.pdf"
    old_file_raw.write_text("%PDF-1.4 content 1", encoding="utf-8")

    new_path1 = get_pdf_output_path("FAC-OLD1", "2026-10-15")
    assert "4T" in new_path1.parts
    assert "10_Octubre" in new_path1.parts
    assert new_path1.exists()
    assert new_path1.read_text(encoding="utf-8") == "%PDF-1.4 content 1"
    assert not old_file_raw.exists()

    # 2. Caso ruta intermedia sin trimestre: tmp_path / "2026" / "10_Octubre" / "FAC-OLD2.pdf"
    old_dir_no_trim = tmp_path / "2026" / "10_Octubre"
    old_dir_no_trim.mkdir(parents=True, exist_ok=True)
    old_file_no_trim = old_dir_no_trim / "FAC-OLD2.pdf"
    old_file_no_trim.write_text("%PDF-1.4 content 2", encoding="utf-8")

    new_path2 = get_pdf_output_path("FAC-OLD2", "2026-10-20")
    assert "4T" in new_path2.parts
    assert "10_Octubre" in new_path2.parts
    assert new_path2.exists()
    assert new_path2.read_text(encoding="utf-8") == "%PDF-1.4 content 2"
    assert not old_file_no_trim.exists()


def test_api_facturas_filtro_sin_iva(client, emisor_configurado):
    """Verifica el filtrado exclusivo e independiente de facturas con IVA y sin IVA."""
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Filtro Sin IVA S.L.",
        "nif_cif": "B88888888"
    })
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    # 2. Crear factura con IVA (21%)
    res_con_iva = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-10-26",
        "sin_iva": False,
        "lineas": [
            {
                "descripcion": "Servicio con IVA",
                "cantidad": 1.0,
                "precio_unitario": 100.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_con_iva.status_code == 201
    fac_con_iva_id = res_con_iva.json()["id"]

    # 3. Crear factura sin IVA (exenta)
    res_sin_iva = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-10-26",
        "sin_iva": True,
        "lineas": [
            {
                "descripcion": "Servicio médico o formación sin IVA",
                "cantidad": 1.0,
                "precio_unitario": 200.0,
                "porcentaje_iva": 0.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_sin_iva.status_code == 201
    fac_sin_iva_id = res_sin_iva.json()["id"]

    # 4. Filtrar por sin_iva=true
    res_filtro_sin = client.get("/api/facturas?sin_iva=true")
    assert res_filtro_sin.status_code == 200
    ids_sin = [f["id"] for f in res_filtro_sin.json()]
    assert fac_sin_iva_id in ids_sin
    assert fac_con_iva_id not in ids_sin

    # 5. Filtrar por sin_iva=false
    res_filtro_con = client.get("/api/facturas?sin_iva=false")
    assert res_filtro_con.status_code == 200
    ids_con = [f["id"] for f in res_filtro_con.json()]
    assert fac_con_iva_id in ids_con
    assert fac_sin_iva_id not in ids_con

    # 6. Combinar con estado
    res_combinado = client.get("/api/facturas?estado=Emitida&sin_iva=true")
    assert res_combinado.status_code == 200
    ids_comb = [f["id"] for f in res_combinado.json()]
    assert fac_sin_iva_id in ids_comb
    assert fac_con_iva_id not in ids_comb

    # 7. Compatibilidad retroactiva con estado=SIN_IVA
    res_retro = client.get("/api/facturas?estado=SIN_IVA")
    assert res_retro.status_code == 200
    ids_retro = [f["id"] for f in res_retro.json()]
    assert fac_sin_iva_id in ids_retro
    assert fac_con_iva_id not in ids_retro


