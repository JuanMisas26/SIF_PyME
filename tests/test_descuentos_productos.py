import pytest
from datetime import date
from pypdf import PdfReader
from io import BytesIO


def test_factura_descuento_global_visible(client, emisor_configurado):
    """Prueba una factura con descuento global del 10% en modo VISIBLE."""
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Cliente Descuento Global S.L."
    })
    assert res_cli.status_code == 201, res_cli.text
    cliente_id = res_cli.json()["id"]

    # 2. Crear descuento global
    res_desc = client.post("/api/descuentos", json={
        "nombre": "Promo Global 10%",
        "codigo": "GLOBAL10",
        "tipo": "porcentaje",
        "valor": 10.0,
        "aplica_a": "todos"
    })
    assert res_desc.status_code == 201
    desc_id = res_desc.json()["id"]

    # 3. Emitir factura con descuento visible
    res_fac = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-10-26",
        "descuento_id": desc_id,
        "descuento_nombre": "Promo Global 10%",
        "descuento_tipo": "porcentaje",
        "descuento_valor": 10.0,
        "descuento_importe_total": 10.0,
        "descuento_visible": True,
        "lineas": [
            {
                "descripcion": "Consultoría Técnica",
                "cantidad": 1.0,
                "precio_unitario": 100.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_fac.status_code == 201
    fac_data = res_fac.json()
    assert fac_data["descuento_id"] == desc_id
    assert fac_data["descuento_visible"] == 1 or fac_data["descuento_visible"] is True

    # 4. Comprobar PDF
    res_pdf = client.get(f"/api/facturas/{fac_data['id']}/pdf")
    assert res_pdf.status_code == 200
    reader = PdfReader(BytesIO(res_pdf.content))
    pdf_text = "".join(page.extract_text() or "" for page in reader.pages)

    # Debe contener el desglose de descuento
    assert "Descuento" in pdf_text or "descuento" in pdf_text.lower()
    assert "Subtotal bruto" in pdf_text or "Base imponible" in pdf_text


def test_factura_descuento_especifico_producto_oculto(client, emisor_configurado):
    """
    Prueba clave: Descuento para un producto en concreto en modo NO VISIBLE.
    El precio unitario de ese producto se autocalcula y en el PDF final
    NO aparece ninguna mención a descuentos ni palabras 'Descuento'.
    """
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Empresa Industrial Norte S.A."
    })
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    # 2. Crear 2 productos
    res_p1 = client.post("/api/productos", json={
        "nombre": "Servicio Mantenimiento Anual",
        "descripcion": "Mantenimiento preventivo",
        "precio_unitario_base": 100.0
    })
    p1_id = res_p1.json()["id"]

    res_p2 = client.post("/api/productos", json={
        "nombre": "Licencia Software",
        "descripcion": "Licencia anual de uso",
        "precio_unitario_base": 200.0
    })
    p2_id = res_p2.json()["id"]

    # 3. Crear descuento vinculado SOLO a Producto 1 (20% dto)
    res_desc = client.post("/api/descuentos", json={
        "nombre": "Promo Especial Prod A",
        "codigo": "PROMOA20",
        "tipo": "porcentaje",
        "valor": 20.0,
        "aplica_a": "productos",
        "producto_ids": [p1_id]
    })
    desc_id = res_desc.json()["id"]

    # 4. Emitir factura con descuento NO VISIBLE (oculto / autocalculado):
    # - Prod 1: precio_unitario reducido a 80.0 (100 - 20%), precio_unitario_original=100.0
    # - Prod 2: precio_unitario intacto a 200.0
    res_fac = client.post("/api/facturas", json={
        "cliente_id": cliente_id,
        "fecha_emision": "2026-10-26",
        "descuento_id": desc_id,
        "descuento_nombre": "Promo Especial Prod A",
        "descuento_tipo": "porcentaje",
        "descuento_valor": 20.0,
        "descuento_importe_total": 20.0,
        "descuento_visible": False,
        "lineas": [
            {
                "producto_id": p1_id,
                "descripcion": "Servicio Mantenimiento Anual",
                "cantidad": 1.0,
                "precio_unitario": 80.0,
                "precio_unitario_original": 100.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            },
            {
                "producto_id": p2_id,
                "descripcion": "Licencia Software",
                "cantidad": 1.0,
                "precio_unitario": 200.0,
                "porcentaje_iva": 21.0,
                "porcentaje_irpf": 0.0
            }
        ]
    })
    assert res_fac.status_code == 201
    fac_data = res_fac.json()
    assert fac_data["descuento_visible"] == 0 or fac_data["descuento_visible"] is False
    assert fac_data["base_imponible_total"] == 280.0

    # 5. Comprobar PDF final
    res_pdf = client.get(f"/api/facturas/{fac_data['id']}/pdf")
    assert res_pdf.status_code == 200
    reader = PdfReader(BytesIO(res_pdf.content))
    pdf_text = "".join(page.extract_text() or "" for page in reader.pages)

    # En modo oculto NO debe figurar la palabra 'Descuento'
    assert "Descuento" not in pdf_text
    assert "descuento" not in pdf_text.lower()

    # Los precios netos deben reflejarse
    assert "80,00" in pdf_text
    assert "200,00" in pdf_text
    assert "280,00" in pdf_text


def test_presupuesto_con_descuento_opcion_y_conversion(client, emisor_configurado):
    """Verifica la asignación de descuento por opción en presupuestos y su conversión a factura."""
    # 1. Crear cliente
    res_cli = client.post("/api/clientes", json={
        "razon_social": "Novios Prueba Descuento S.L."
    })
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    # 2. Crear descuento
    res_desc = client.post("/api/descuentos", json={
        "nombre": "Pack Boda Completo 10%",
        "tipo": "porcentaje",
        "valor": 10.0,
        "aplica_a": "todos"
    })
    desc_id = res_desc.json()["id"]

    # 3. Crear presupuesto con 2 opciones: Opción A con descuento, Opción B sin descuento
    res_pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": f"PRE-DTO-{date.today().isoformat()}-001",
        "cliente_id": cliente_id,
        "titulo": "Presupuesto con Promoción",
        "opciones": [
            {
                "nombre_opcion": "Opción Promo 10%",
                "descuento_id": desc_id,
                "descuento_nombre": "Pack Boda Completo 10%",
                "descuento_tipo": "porcentaje",
                "descuento_valor": 10.0,
                "descuento_visible": True,
                "descuento_importe_total": 50.0,
                "lineas": [
                    {
                        "descripcion": "Invitación Premium",
                        "cantidad": 100.0,
                        "precio_unitario": 5.0
                    }
                ]
            },
            {
                "nombre_opcion": "Opción Estándar",
                "lineas": [
                    {
                        "descripcion": "Invitación Estándar",
                        "cantidad": 100.0,
                        "precio_unitario": 4.0
                    }
                ]
            }
        ]
    })
    assert res_pres.status_code in (200, 201)
    pres_data = res_pres.json()
    assert len(pres_data["opciones"]) == 2
    op_promo = pres_data["opciones"][0]
    assert op_promo["descuento_id"] == desc_id

    # 4. Convertir opción promo a factura
    res_conv = client.post(f"/api/presupuestos/{pres_data['id']}/convertir-factura", json={
        "opcion_id": op_promo["id"],
        "tipo_facturacion": "total",
        "porcentaje_iva": 21.0,
        "porcentaje_irpf": 0.0,
        "sin_iva": False
    })
    assert res_conv.status_code == 200
    conv_data = res_conv.json()
    assert conv_data["factura_id"] > 0

    # 5. Verificar que la factura creada heredó el descuento
    res_fac = client.get(f"/api/facturas/{conv_data['factura_id']}")
    assert res_fac.status_code == 200
    fac_obj = res_fac.json()
    assert fac_obj["descuento_id"] == desc_id
    assert fac_obj["descuento_nombre"] == "Pack Boda Completo 10%"


def test_presupuesto_descuento_oculto_y_conversion(client, emisor_configurado):
    """Verifica que un presupuesto con descuento en modo OCULTO guarda el importe del descuento y los precios originales en líneas."""
    res_cli = client.post("/api/clientes", json={"razon_social": "Cliente Dto Oculto SL"})
    assert res_cli.status_code == 201
    cliente_id = res_cli.json()["id"]

    res_desc = client.post("/api/descuentos", json={
        "nombre": "Promo Oculta 20%",
        "tipo": "porcentaje",
        "valor": 20.0,
        "aplica_a": "todos"
    })
    assert res_desc.status_code == 201
    desc_id = res_desc.json()["id"]

    # Crear presupuesto con opción en modo oculto (descuento_visible = False)
    res_pres = client.post("/api/presupuestos", json={
        "numero_presupuesto": f"PRE-OCU-{date.today().isoformat()}-001",
        "cliente_id": cliente_id,
        "titulo": "Presupuesto Oculto",
        "opciones": [
            {
                "nombre_opcion": "Opción Descuento Oculto",
                "descuento_id": desc_id,
                "descuento_nombre": "Promo Oculta 20%",
                "descuento_tipo": "porcentaje",
                "descuento_valor": 20.0,
                "descuento_visible": False,
                "descuento_importe_total": 40.0,
                "lineas": [
                    {
                        "descripcion": "Producto con dto oculto",
                        "cantidad": 2.0,
                        "precio_unitario": 80.0,
                        "precio_unitario_original": 100.0
                    }
                ]
            }
        ]
    })
    assert res_pres.status_code in (200, 201)
    pres_data = res_pres.json()
    op = pres_data["opciones"][0]
    assert op["descuento_visible"] == 0 or op["descuento_visible"] is False
    assert op["descuento_importe_total"] == 40.0
    assert op["lineas"][0]["precio_unitario_original"] == 100.0
    assert op["lineas"][0]["precio_unitario"] == 80.0

    # Convertir a factura
    res_conv = client.post(f"/api/presupuestos/{pres_data['id']}/convertir-factura", json={
        "opcion_id": op["id"],
        "tipo_facturacion": "total",
        "porcentaje_iva": 21.0,
        "porcentaje_irpf": 0.0,
        "sin_iva": False
    })
    assert res_conv.status_code == 200
    fac_id = res_conv.json()["factura_id"]

    res_fac = client.get(f"/api/facturas/{fac_id}")
    assert res_fac.status_code == 200
    fac_obj = res_fac.json()
    assert fac_obj["descuento_id"] == desc_id
    assert fac_obj["descuento_visible"] == 0 or fac_obj["descuento_visible"] is False
    assert fac_obj["descuento_importe_total"] == 40.0
    assert fac_obj["lineas"][0]["precio_unitario_original"] == 100.0
    assert fac_obj["lineas"][0]["precio_unitario"] == 80.0

