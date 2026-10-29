import pytest
from app.validators import (
    sanear_identificador,
    validar_nif_persona_fisica,
    validar_nie,
    validar_cif,
    validar_nif_cif_nie,
    sanear_iban,
    validar_iban,
    validar_codigo_postal
)


def test_sanear_identificador():
    assert sanear_identificador(" 12.345.678 - Z ") == "12345678Z"
    assert sanear_identificador("b-10000008") == "B10000008"
    assert sanear_identificador("") == ""
    assert sanear_identificador(None) == ""


def test_validar_nif_persona_fisica():
    # 12345678 % 23 = 14 -> Z
    assert validar_nif_persona_fisica("12345678Z") is True
    # Letra errónea
    assert validar_nif_persona_fisica("12345678A") is False
    # Formato inválido
    assert validar_nif_persona_fisica("1234567Z") is False
    assert validar_nif_persona_fisica("123456789") is False


def test_validar_nie():
    # X0000001 -> 00000001 % 23 = 1 -> R
    assert validar_nie("X0000001R") is True
    # Y0000001 -> 10000001 % 23 = 15 -> S
    assert validar_nie("Y0000001S") is True
    # Z0000001 -> 20000001 % 23 = 6 -> Y
    assert validar_nie("Z0000001Y") is True
    # Letra errónea
    assert validar_nie("X0000001A") is False
    # Prefijo inválido
    assert validar_nie("A0000001R") is False


def test_validar_cif():
    # CIF Sociedad Limitada (tipo B, requiere dígito)
    assert validar_cif("B10000008") is True
    # CIF erróneo
    assert validar_cif("B10000001") is False

    # CIF Organismo público (tipo Q, requiere letra de control JABCDEFGHI)
    assert validar_cif("Q0000000J") is True
    assert validar_cif("Q00000001") is False  # Tipo Q no permite dígito numérico


def test_validar_nif_cif_nie_unificado():
    # Válidos
    valido, tipo, _ = validar_nif_cif_nie("12345678Z")
    assert valido is True and tipo == "NIF"

    valido, tipo, _ = validar_nif_cif_nie("X0000001R")
    assert valido is True and tipo == "NIE"

    valido, tipo, _ = validar_nif_cif_nie("B10000008")
    assert valido is True and tipo == "CIF"

    # Extranjero / Intracomunitario UE (Francia)
    valido, tipo, _ = validar_nif_cif_nie("FR12345678901")
    assert valido is True and tipo == "EXTRANJERO"

    # Inválidos
    valido, tipo, _ = validar_nif_cif_nie("12345678A")
    assert valido is False and tipo == "INVALIDO"

    valido, tipo, _ = validar_nif_cif_nie("INVALIDO123")
    assert valido is False and tipo == "INVALIDO"

    # Vacío
    valido, tipo, _ = validar_nif_cif_nie("", permitir_vacio=True)
    assert valido is True and tipo == "VACIO"

    valido, tipo, _ = validar_nif_cif_nie("", permitir_vacio=False)
    assert valido is False and tipo == "VACIO"


def test_validar_iban():
    # IBAN español válido conocido
    iban_valido = "ES9121000418450200051332"
    valido, err, _ = validar_iban(iban_valido)
    assert valido is True
    assert err == ""

    # Con espacios
    valido, err, _ = validar_iban("ES91 2100 0418 4502 0005 1332")
    assert valido is True

    # Checksum alterado
    valido, err, _ = validar_iban("ES9121000418450200051330")
    assert valido is False
    assert "dígitos de control" in err

    # Longitud incorrecta en España (debe tener 24)
    valido, err, _ = validar_iban("ES9121000418")
    assert valido is False

    # Vacío con permitir_vacio
    valido, err, _ = validar_iban("", permitir_vacio=True)
    assert valido is True


def test_validar_codigo_postal():
    # Válidos (01 al 52)
    assert validar_codigo_postal("28001") is True  # Madrid
    assert validar_codigo_postal("08001") is True  # Barcelona
    assert validar_codigo_postal("52001") is True  # Melilla
    assert validar_codigo_postal("01001") is True  # Álava

    # Inválidos
    assert validar_codigo_postal("00123") is False
    assert validar_codigo_postal("53001") is False
    assert validar_codigo_postal("2800") is False
    assert validar_codigo_postal("280001") is False
    assert validar_codigo_postal("ABCDE") is False


def test_validation_exception_handler_union_limpieza():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    # Enviar producto con descripción vacía
    res = client.post("/api/productos", json={"nombre": "Tarjetón", "descripcion": ""})
    assert res.status_code == 422
    data = res.json()
    # Debe contener error sobre la descripción del producto
    assert "Descripción del producto" in data["detail"]
    # NO debe contener el mensaje técnico espurio en inglés del Union "Input should be a valid list"
    assert "Input should be a valid list" not in data["detail"]
    assert all("valid list" not in err["message"] for err in data["errors"])
