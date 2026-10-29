import pytest
from pathlib import Path


def test_money_rain_static_file_exists():
    """Verifica que el fichero JavaScript del motor de lluvia de billetes existe y es válido."""
    js_path = Path("app/static/js/money_rain.js")
    assert js_path.is_file(), "El archivo app/static/js/money_rain.js debe existir"
    content = js_path.read_text(encoding="utf-8")
    assert "window.triggerMoneyRain = triggerMoneyRain" in content
    assert "playChaChing" in content
    assert "sif-money-rain-overlay" in content
    assert "500 €" in content
    assert "100 €" in content


def test_base_html_includes_money_rain():
    """Verifica que base.html enlaza el script de money_rain.js."""
    base_html = Path("app/templates/base.html").read_text(encoding="utf-8")
    assert '<script src="/static/js/money_rain.js"></script>' in base_html


def test_presupuestos_html_triggers_money_rain():
    """Verifica que presupuestos.html contiene la lógica del 5% y el easter egg al aceptar."""
    presupuestos_html = Path("app/templates/presupuestos.html").read_text(encoding="utf-8")
    assert "Math.random() < 0.05" in presupuestos_html
    assert "window.triggerMoneyRain" in presupuestos_html
    assert "ejecutarAceptarPresupuesto(false, event)" in presupuestos_html
    assert "ejecutarAceptarPresupuesto(true, event)" in presupuestos_html
    assert "ejecutarConversionFactura(event)" in presupuestos_html
    assert "event.shiftKey" in presupuestos_html
    assert "🍀 ¡Día de Suerte!" in presupuestos_html


def test_app_js_invoice_emission_triggers_money_rain():
    """Verifica que submitFactura en app.js incluye la probabilidad del 5% y la lluvia de billetes."""
    app_js = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "const esSuerte = !isEdit && ((Math.random() < 0.05)" in app_js
    assert "window.triggerMoneyRain" in app_js
    assert "redirectDelay = esSuerte ? 3600 : 1000" in app_js
    assert "🍀 ¡Día de Suerte!" in app_js

