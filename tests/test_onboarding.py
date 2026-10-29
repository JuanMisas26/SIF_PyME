import pytest
from pathlib import Path
from app.services.pdf_service import get_pdf_output_path
import app.paths as paths_module


def test_rutas_sugeridas_endpoint(client):
    """Verifica que el endpoint de rutas sugeridas devuelva la estructura adecuada."""
    res = client.get("/api/configuracion/rutas-sugeridas")
    assert res.status_code == 200
    data = res.json()
    assert "local_default" in data
    assert "desktop" in data
    assert "current" in data
    assert "platform" in data


def test_completar_onboarding_exitoso(client, tmp_path):
    """Verifica el flujo completo de Onboarding con guardado de ruta y datos fiscales."""
    custom_pdf_dir = tmp_path / "FacturasPersonalizadas"

    payload = {
        "nombre": "Estudio Creativo Norte S.L.",
        "nif": "B12345674",
        "direccion": "Paseo de la Castellana 100",
        "codigo_postal": "28046",
        "ciudad": "Madrid",
        "email": "facturas@estudionorte.com",
        "iban": "ES91 2100 0418 4502 0005 1332",
        "pdf_storage_dir": str(custom_pdf_dir),
        "crear_acceso_escritorio": False
    }

    res = client.post("/api/configuracion/onboarding", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["alias_escritorio"] == "Omitido"
    assert Path(data["pdf_storage_dir"]).resolve() == custom_pdf_dir.resolve()

    # Comprobar que /api/configuracion refleja los datos y marca onboarding completado
    cfg_res = client.get("/api/configuracion")
    assert cfg_res.status_code == 200
    cfg_data = cfg_res.json()
    assert cfg_data["es_valida"] is True
    assert cfg_data["datos"]["nombre"] == "Estudio Creativo Norte S.L."
    assert cfg_data["datos"]["nif"] == "B12345674"
    assert cfg_data["datos"]["onboarding_completado"] == "true"
    assert Path(cfg_data["datos"]["pdf_storage_dir"]).resolve() == custom_pdf_dir.resolve()

    # Verificar que get_pdf_output_path() ahora usa el directorio personalizado
    pdf_path = get_pdf_output_path("FAC-2026-10-20-001", "2026-10-20")
    assert custom_pdf_dir.resolve() in pdf_path.parents or custom_pdf_dir.resolve() == pdf_path.parent.parent


def test_crear_acceso_directo_endpoint(client):
    """Verifica la respuesta del endpoint de creación de acceso directo."""
    res = client.post("/api/configuracion/crear-acceso-directo")
    assert res.status_code == 200
    data = res.json()
    assert "ok" in data
    assert "mensaje" in data


def test_guardar_configuracion_con_directorio_personalizado(client, tmp_path):
    """Verifica que modificar pdf_storage_dir desde la pantalla de configuración estándar funcione."""
    nuevo_dir = tmp_path / "OtroDirectorio"

    payload = {
        "nombre": "Mi Empresa Test",
        "nif": "B12345674",
        "direccion": "Calle Mayor 1",
        "codigo_postal": "28001",
        "ciudad": "Madrid",
        "pdf_storage_dir": str(nuevo_dir)
    }

    res = client.put("/api/configuracion", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert Path(data["datos"]["pdf_storage_dir"]).resolve() == nuevo_dir.resolve()

