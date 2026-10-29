"""
Módulo de excepciones personalizadas y manejadores de errores para FastAPI.
Proporciona tipificación clara de errores para backend y frontend con códigos estándar.
"""
from typing import Optional, Any
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger("sif.errors")


# Nombres amigables en español para campos comunes de la aplicación
FIELD_LABELS: dict[str, str] = {
    "razon_social": "Nombre o Razón Social",
    "nif_cif": "NIF / CIF / NIE",
    "nif": "NIF / CIF del emisor",
    "nombre": "Nombre o Razón Social del emisor",
    "telefono": "Teléfono",
    "email": "Correo electrónico",
    "direccion": "Dirección",
    "codigo_postal": "Código Postal",
    "ciudad": "Ciudad",
    "provincia": "Provincia",
    "forma_pago_defecto": "Forma de pago por defecto",
    "cliente_id": "Cliente",
    "fecha_emision": "Fecha de emisión",
    "fecha_vencimiento": "Fecha de vencimiento",
    "lineas": "Líneas de la factura",
    "descripcion": "Descripción del producto",
    "cantidad": "Cantidad",
    "precio_unitario": "Precio unitario",
    "precio_unitario_base": "Precio unitario base",
    "porcentaje_iva": "Porcentaje de IVA",
    "porcentaje_irpf": "Porcentaje de IRPF",
    "porcentaje_descuento": "Porcentaje de descuento",
    "estado": "Estado de la factura",
    "codigo": "Código del producto",
    "iban": "IBAN bancario",
    "numero_presupuesto": "Identificador del presupuesto",
    "titulo": "Título del dossier",
    "subtitulo": "Subtítulo",
    "opciones": "Opciones del presupuesto",
    "nombre_opcion": "Nombre de la opción",
    "fecha": "Fecha",
    "fecha_validez": "Fecha de validez",
    "detalle_material": "Detalle del material",
}

HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class AppException(HTTPException):
    """Excepción base con código de error tipificado."""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "GENERIC_ERROR",
        errors: Optional[list[dict[str, Any]]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.errors = errors or []


class ValidationError(AppException):
    """Error de validación en datos recibidos (422)."""
    def __init__(self, detail: str, errors: Optional[list[dict[str, Any]]] = None):
        super().__init__(
            status_code=HTTP_422_STATUS,
            detail=detail,
            error_code="VALIDATION_ERROR",
            errors=errors
        )


class NotFoundError(AppException):
    """Recurso no encontrado (404)."""
    def __init__(self, detail: str = "Recurso no encontrado", field: Optional[str] = None):
        errors = [{"field": field, "message": detail}] if field else []
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
            errors=errors
        )


class ConflictError(AppException):
    """Conflicto con recursos existentes (ej. NIF o código duplicado) (409)."""
    def __init__(self, detail: str, field: Optional[str] = None):
        errors = [{"field": field, "message": detail}] if field else []
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
            errors=errors
        )


class BusinessRuleError(AppException):
    """Violación de reglas de negocio (ej. emisor sin configurar, fechas ilógicas) (400)."""
    def __init__(self, detail: str, error_code: str = "BUSINESS_RULE_VIOLATION", field: Optional[str] = None):
        errors = [{"field": field, "message": detail}] if field else []
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
            errors=errors
        )


def _traducir_error_pydantic(err: dict[str, Any]) -> tuple[str, str, str]:
    """
    Traduce un error de Pydantic a un nombre de campo amigable y un mensaje claro en español.
    Retorna: (campo_original, campo_legible, mensaje_amigable)
    """
    loc = err.get("loc", [])
    campo_original = str(loc[-1]) if loc else "general"
    campo_legible = FIELD_LABELS.get(campo_original, campo_original)
    if "Producto" in str(loc) or "producto" in str(loc):
        if campo_original == "nombre":
            campo_legible = "Nombre del producto"
        elif campo_original == "descripcion":
            campo_legible = "Descripción del producto"
    
    tipo_error = err.get("type", "")
    msg = err.get("msg", "")

    # Si el mensaje ya viene de un validador personalizado (ValueError), usarlo directamente
    if msg.startswith("Value error, "):
        raw_msg = msg.replace("Value error, ", "").strip()
        if raw_msg.lower().startswith("no puede") or raw_msg.lower().startswith("debe"):
            mensaje_limpio = f"El campo '{campo_legible}' {raw_msg[0].lower() + raw_msg[1:]}."
        else:
            mensaje_limpio = raw_msg
        return campo_original, campo_legible, mensaje_limpio

    # Traducción de tipos comunes de error de Pydantic
    if "missing" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' es obligatorio."
    elif "string_too_short" in tipo_error or "too_short" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' no puede estar vacío."
    elif "list_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser una lista válida de elementos."
    elif "model_type" in tipo_error or "dict_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser un objeto válido."
    elif "int_parsing" in tipo_error or "int_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser un número entero."
    elif "float_parsing" in tipo_error or "float_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser un número decimal válido."
    elif "date_parsing" in tipo_error or "date_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser una fecha válida."
    elif "bool_parsing" in tipo_error or "bool_type" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser verdadero o falso."
    elif "greater_than" in tipo_error or "gt" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' debe ser mayor que 0."
    elif "less_than" in tipo_error or "le" in tipo_error:
        mensaje_limpio = f"El campo '{campo_legible}' supera el límite permitido."
    elif "value_error" in tipo_error:
        mensaje_limpio = msg
    else:
        if "Input should be a valid list" in msg:
            mensaje_limpio = f"El campo '{campo_legible}' debe ser una lista válida de elementos."
        elif "Input should be a valid" in msg:
            mensaje_limpio = f"El campo '{campo_legible}' contiene un valor con formato no válido."
        else:
            mensaje_limpio = msg or f"El campo '{campo_legible}' contiene un valor inválido."

    return campo_original, campo_legible, mensaje_limpio


async def app_exception_handler(request: Request, exc: AppException):
    """Manejador para excepciones de tipo AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "errors": exc.errors
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador estándar para HTTPException."""
    error_code = getattr(exc, "error_code", "HTTP_ERROR")
    if exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 409:
        error_code = "CONFLICT"
    elif exc.status_code == 400:
        error_code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": error_code,
            "status_code": exc.status_code,
            "errors": []
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Manejador para errores de validación de Pydantic (HTTP 422).
    Genera un mensaje compuesto amigable y una lista estructurada de errores por campo.
    """
    raw_errors = exc.errors()
    # Filtrar errores espurios de variantes no coincidentes en Unions (ej: Union[ProductoCreate, list[ProductoCreate]])
    has_specific_field_error = any(
        e.get("type") not in ("list_type", "model_type", "dict_type", "union_tag_invalid")
        for e in raw_errors
    )

    filtered_errors = []
    for err in raw_errors:
        err_type = err.get("type", "")
        if has_specific_field_error and err_type in ("list_type", "model_type", "dict_type"):
            input_val = err.get("input")
            if (err_type == "list_type" and isinstance(input_val, dict)) or                (err_type in ("model_type", "dict_type") and isinstance(input_val, list)):
                continue
        filtered_errors.append(err)

    if not filtered_errors:
        filtered_errors = raw_errors

    errores_estructurados = []
    mensajes = []

    for err in filtered_errors:
        campo_original, campo_legible, mensaje_amigable = _traducir_error_pydantic(err)
        errores_estructurados.append({
            "field": campo_original,
            "field_label": campo_legible,
            "message": mensaje_amigable,
            "type": err.get("type", "validation_error")
        })
        mensajes.append(f"• {mensaje_amigable}")

    detalle_principal = "Errores de validación:\n" + "\n".join(mensajes) if mensajes else "Datos de entrada inválidos."

    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "detail": detalle_principal,
            "error_code": "VALIDATION_ERROR",
            "status_code": 422,
            "errors": errores_estructurados
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Manejador global para errores inesperados del servidor (500)."""
    logger.exception(f"Error no controlado en {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Ha ocurrido un error inesperado en el servidor.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "status_code": 500,
            "errors": []
        }
    )

