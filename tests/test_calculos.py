import pytest
from decimal import Decimal
from app.services.pdf_service import calcular_totales_linea, calcular_totales_factura, round2


def test_round2_financial_precision():
    # Comprobar ROUND_HALF_UP (0.005 -> 0.01)
    assert round2(0.005) == Decimal('0.01')
    assert round2(0.004) == Decimal('0.00')
    assert round2(10.555) == Decimal('10.56')
    assert round2(10.554) == Decimal('10.55')
    assert float(round2(0.005)) == 0.01


def test_calcular_totales_linea_estandar():
    linea = {
        'cantidad': 2.0,
        'precio_unitario': 100.0,
        'porcentaje_descuento': 10.0,  # 100 - 10 = 90 -> * 2 = 180.0
        'porcentaje_iva': 21.0,        # 180 * 0.21 = 37.80
        'porcentaje_irpf': 15.0        # 180 * 0.15 = 27.00
    }
    totales = calcular_totales_linea(linea)
    assert totales['subtotal_base'] == 180.00
    assert totales['iva_amount'] == 37.80
    assert totales['irpf_amount'] == 27.00
    # Total = Base + IVA - IRPF = 180 + 37.80 - 27.00 = 190.80
    assert totales['total_linea'] == 190.80


def test_calcular_totales_factura_multiples_lineas():
    lineas = [
        {
            'cantidad': 1.0,
            'precio_unitario': 100.0,
            'porcentaje_descuento': 0.0,
            'porcentaje_iva': 21.0,
            'porcentaje_irpf': 0.0
        },
        {
            'cantidad': 2.0,
            'precio_unitario': 50.0,
            'porcentaje_descuento': 0.0,
            'porcentaje_iva': 10.0,
            'porcentaje_irpf': 0.0
        }
    ]
    totales = calcular_totales_factura(lineas)
    assert totales['base_imponible_total'] == 200.00
    # IVA: (100 * 0.21 = 21.0) + (100 * 0.10 = 10.0) = 31.00
    assert totales['iva_total'] == 31.00
    assert totales['irpf_total'] == 0.00
    assert totales['total_factura'] == 231.00
    
    # Desglose de tipos de IVA
    desglose = totales['desglose_iva']
    assert 21.0 in desglose
    assert desglose[21.0]['base'] == 100.0
    assert desglose[21.0]['cuota'] == 21.0

    assert 10.0 in desglose
    assert desglose[10.0]['base'] == 100.0
    assert desglose[10.0]['cuota'] == 10.0




def test_calcular_totales_linea_precio_negativo():
    """Verifica que a una línea con precio negativo se le calcula proporcionalmente el IVA y el IRPF."""
    linea = {
        'cantidad': 1.0,
        'precio_unitario': -50.0,
        'porcentaje_descuento': 0.0,
        'porcentaje_iva': 21.0,
        'porcentaje_irpf': 15.0
    }
    totales = calcular_totales_linea(linea)
    assert totales['subtotal_base'] == -50.00
    assert totales['iva_amount'] == -10.50
    assert totales['irpf_amount'] == -7.50
    assert totales['total_linea'] == -53.00


def test_calcular_totales_factura_con_linea_negativa():
    """Verifica que una línea negativa resta de la base imponible y reduce adecuadamente la cuota de IVA e IRPF."""
    lineas = [
        {
            'cantidad': 1.0,
            'precio_unitario': 200.0,
            'porcentaje_descuento': 0.0,
            'porcentaje_iva': 21.0,
            'porcentaje_irpf': 15.0
        },
        {
            'cantidad': 1.0,
            'precio_unitario': -50.0,
            'porcentaje_descuento': 0.0,
            'porcentaje_iva': 21.0,
            'porcentaje_irpf': 15.0
        }
    ]
    totales = calcular_totales_factura(lineas)
    assert totales['base_imponible_total'] == 150.00
    assert totales['iva_total'] == 31.50
    assert totales['irpf_total'] == 22.50
    # Total = 150 (base) + 31.50 (iva) - 22.50 (irpf) = 159.00 €
    assert totales['total_factura'] == 159.00
    # El desglose de IVA refleja la base y cuota netas
    assert 21.0 in totales['desglose_iva']
    assert totales['desglose_iva'][21.0]['base'] == 150.00
    assert totales['desglose_iva'][21.0]['cuota'] == 31.50
