"""
Módulo de validadores y saneamiento para el ámbito fiscal y administrativo (España / SEPA).
Incluye validación formal de:
- NIF (personas físicas)
- NIE (extranjeros residentes)
- CIF (personas jurídicas / empresas)
- IBAN (cuentas bancarias SEPA, algoritmo Modulo 97 / ISO 7064)
- Código Postal (España)
"""

import re
from typing import Tuple, Optional

# Letras de control para NIF/NIE según resto % 23
LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"

# Tipos de entidades CIF y su tipo de carácter de control
# 'D': Solo dígito numérico
# 'L': Solo letra
# 'A': Ambos aceptados (dígito o letra)
TIPOS_CIF = {
    'A': 'D',  # Sociedades Anónimas
    'B': 'D',  # Sociedades de Responsabilidad Limitada
    'C': 'A',  # Sociedades Colectivas
    'D': 'A',  # Sociedades Comanditarias
    'E': 'D',  # Comunidades de Bienes
    'F': 'A',  # Sociedades Cooperativas
    'G': 'A',  # Asociaciones
    'H': 'D',  # Comunidades de propietarios
    'J': 'A',  # Sociedades Civiles
    'N': 'L',  # Entidades extranjeras
    'P': 'L',  # Corporaciones locales
    'Q': 'L',  # Organismos públicos
    'R': 'L',  # Congregaciones e instituciones religiosas
    'S': 'L',  # Órganos de la Administración del Estado
    'U': 'A',  # Uniones Temporales de Empresas
    'V': 'A',  # Otros tipos
    'W': 'L',  # Establecimientos permanentes de no residentes
}

LETRAS_CONTROL_CIF = "JABCDEFGHI"

# Códigos de país miembros de la UE para NIF intracomunitario (VIES)
PAISES_UE_VAT = {
    'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'FI',
    'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL',
    'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'GB'
}


def sanear_identificador(identificador: str) -> str:
    """Elimina espacios en blanco, guiones y convierte a mayúsculas."""
    if not identificador:
        return ""
    return re.sub(r"[\s\-_.]+", "", identificador).upper().strip()


def validar_nif_persona_fisica(nif: str) -> bool:
    """Valida un NIF estándar de persona física española (8 números + 1 letra)."""
    if not re.match(r"^\d{8}[A-Z]$", nif):
        return False
    numeros = int(nif[:8])
    letra = nif[8]
    return LETRAS_NIF[numeros % 23] == letra


def validar_nie(nie: str) -> bool:
    """
    Valida un NIE (Número de Identidad de Extranjero).
    Formato: X, Y o Z seguido de 7 dígitos y 1 letra de control.
    """
    if not re.match(r"^[XYZ]\d{7}[A-Z]$", nie):
        return False
    mapeo = {'X': '0', 'Y': '1', 'Z': '2'}
    numero_equivalente = mapeo[nie[0]] + nie[1:8]
    letra = nie[8]
    return LETRAS_NIF[int(numero_equivalente) % 23] == letra


def validar_cif(cif: str) -> bool:
    """
    Valida un CIF (Código de Identificación Fiscal para personas jurídicas).
    Formato: 1 letra de tipo de entidad + 7 dígitos centrales + 1 carácter de control.
    """
    if not re.match(r"^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$", cif):
        return False

    tipo = cif[0]
    digitos = cif[1:8]
    control = cif[8]

    # Suma de posiciones pares (índices 1, 3, 5 empezando en 0)
    suma_pares = sum(int(digitos[i]) for i in (1, 3, 5))

    # Suma de posiciones impares (índices 0, 2, 4, 6 empezando en 0)
    suma_impares = 0
    for i in (0, 2, 4, 6):
        doble = int(digitos[i]) * 2
        suma_impares += (doble // 10) + (doble % 10)

    suma_total = suma_pares + suma_impares
    unidades = suma_total % 10
    digito_esperado = (10 - unidades) % 10
    letra_esperada = LETRAS_CONTROL_CIF[digito_esperado]

    tipo_control = TIPOS_CIF.get(tipo, 'A')

    if tipo_control == 'D':
        return control == str(digito_esperado)
    elif tipo_control == 'L':
        return control == letra_esperada
    else:  # 'A' -> Permite dígito o letra
        return control == str(digito_esperado) or control == letra_esperada


def validar_nif_cif_nie(identificador: str, permitir_vacio: bool = False) -> Tuple[bool, str, str]:
    """
    Valida cualquier identificador fiscal español (NIF, NIE, CIF) o intracomunitario.
    
    Retorna una tupla: (es_valido, tipo_detectado, identificador_saneado)
    Donde tipo_detectado puede ser: 'NIF', 'NIE', 'CIF', 'EXTRANJERO', 'VACIO', 'INVALIDO'.
    """
    saneado = sanear_identificador(identificador)
    if not saneado:
        if permitir_vacio:
            return True, "VACIO", ""
        return False, "VACIO", ""

    # Comprobación NIF persona física
    if re.match(r"^\d{8}[A-Z]$", saneado):
        if validar_nif_persona_fisica(saneado):
            return True, "NIF", saneado
        return False, "INVALIDO", saneado

    # Comprobación NIE
    if re.match(r"^[XYZ]\d{7}[A-Z]$", saneado):
        if validar_nie(saneado):
            return True, "NIE", saneado
        return False, "INVALIDO", saneado

    # Comprobación CIF
    if re.match(r"^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$", saneado):
        if validar_cif(saneado):
            return True, "CIF", saneado
        return False, "INVALIDO", saneado

    # Si es formato intracomunitario de la UE (ej. FR123456789, DE123456789)
    prefijo = saneado[:2]
    if prefijo in PAISES_UE_VAT and len(saneado) >= 8 and len(saneado) <= 15:
        if re.match(r"^[A-Z]{2}[A-Z0-9]{6,13}$", saneado):
            return True, "EXTRANJERO", saneado

    return False, "INVALIDO", saneado


def sanear_iban(iban: str) -> str:
    """Elimina espacios y guiones y convierte a mayúsculas."""
    if not iban:
        return ""
    return re.sub(r"[\s\-_.]+", "", iban).upper().strip()


def validar_iban(iban: str, permitir_vacio: bool = True) -> Tuple[bool, str, str]:
    """
    Valida una cuenta bancaria con formato IBAN según estándar ISO 7064 (Módulo 97).
    
    Retorna: (es_valido, mensaje_error, iban_saneado)
    """
    saneado = sanear_iban(iban)
    if not saneado:
        if permitir_vacio:
            return True, "", ""
        return False, "El IBAN no puede estar vacío.", ""

    # Longitud básica (entre 15 y 34 caracteres alfanuméricos)
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$", saneado):
        return False, "El formato o longitud del IBAN no es válido.", saneado

    # Si es español (ES), la longitud obligatoria es exactamente 24 caracteres (ES + 22 dígitos)
    if saneado.startswith("ES"):
        if len(saneado) != 24 or not re.match(r"^ES\d{22}$", saneado):
            return False, "El IBAN español debe comenzar por ES seguido de 22 dígitos (24 caracteres en total).", saneado

    # Algoritmo Modulo 97 (ISO 7064)
    reordenado = saneado[4:] + saneado[:4]
    
    numerico = ""
    for char in reordenado:
        if char.isdigit():
            numerico += char
        else:
            numerico += str(ord(char) - ord('A') + 10)

    if int(numerico) % 97 == 1:
        return True, "", saneado
    return False, "Los dígitos de control del IBAN son incorrectos.", saneado


def validar_codigo_postal(cp: Optional[str], permitir_vacio: bool = True) -> bool:
    """Valida que un código postal español conste de 5 dígitos (01000 a 52999)."""
    if not cp:
        return permitir_vacio
    cp_limpio = cp.strip()
    if not re.match(r"^\d{5}$", cp_limpio):
        return False
    provincia = int(cp_limpio[:2])
    return 1 <= provincia <= 52

