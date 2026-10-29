from typing import Optional, Generic, TypeVar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from app.validators import (
    sanear_identificador,
    validar_nif_cif_nie,
    validar_iban,
    validar_codigo_postal,
)

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def round2(value: float) -> float:
    """Round to 2 decimal places using financial rounding (ROUND_HALF_UP)."""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


# --- Cliente Models ---
class ClienteBase(BaseModel):
    razon_social: str = Field(..., min_length=1, description="Razón social o nombre completo del cliente")
    nif_cif: Optional[str] = Field(default=None, description="NIF, CIF o NIE del cliente (opcional para clientes particulares)")
    telefono: Optional[str] = Field(default=None, description="Teléfono de contacto del cliente")
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    email: Optional[str] = None
    forma_pago_defecto: str = 'Transferencia bancaria'

    @field_validator('nif_cif')
    @classmethod
    def validar_identificador(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_limpio = v.strip()
        if not v_limpio:
            return None
        saneado = sanear_identificador(v_limpio)
        if not saneado:
            return None
        valido, tipo, _ = validar_nif_cif_nie(saneado, permitir_vacio=True)
        if not valido:
            raise ValueError(f"El identificador fiscal '{v}' no es un NIF, NIE o CIF válido.")
        return saneado

    @field_validator('codigo_postal')
    @classmethod
    def validar_cp(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip():
            cp = v.strip()
            if not validar_codigo_postal(cp):
                raise ValueError(f"El código postal '{v}' no es válido para España (debe tener 5 dígitos entre 01000 y 52999).")
            return cp
        return None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    razon_social: Optional[str] = None
    nif_cif: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    email: Optional[str] = None
    forma_pago_defecto: Optional[str] = None

    @field_validator('nif_cif')
    @classmethod
    def validar_identificador(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_limpio = v.strip()
            if not v_limpio:
                return None
            saneado = sanear_identificador(v_limpio)
            if not saneado:
                return None
            valido, tipo, _ = validar_nif_cif_nie(saneado, permitir_vacio=True)
            if not valido:
                raise ValueError(f"El identificador fiscal '{v}' no es un NIF, NIE o CIF válido.")
            return saneado
        return None

    @field_validator('codigo_postal')
    @classmethod
    def validar_cp(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip():
            cp = v.strip()
            if not validar_codigo_postal(cp):
                raise ValueError(f"El código postal '{v}' no es válido para España.")
            return cp
        return None


class ClienteResponse(ClienteBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Modelos de Escalados por Volumen (Tiered Pricing) ---
class ProductoEscaladoBase(BaseModel):
    cantidad_minima: float = Field(default=1.0, ge=1.0, description="Cantidad mínima para aplicar la tarifa")
    cantidad_maxima: Optional[float] = Field(default=None, ge=1.0, description="Cantidad máxima (None = sin límite)")
    precio_unitario: float = Field(default=0.0, ge=0.0, description="Precio unitario para este tramo")

    @field_validator("cantidad_maxima")
    @classmethod
    def validar_rango_cantidades(cls, v, info):
        min_cant = info.data.get("cantidad_minima", 1.0)
        if v is not None and v < min_cant:
            raise ValueError("La cantidad máxima no puede ser inferior a la cantidad mínima")
        return v


class ProductoEscaladoCreate(ProductoEscaladoBase):
    pass


class ProductoEscaladoResponse(ProductoEscaladoBase):
    id: int
    producto_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Modelos de Variantes y Atributos (Colores, Acabados, Tamaños) ---
class ProductoVarianteBase(BaseModel):
    tipo_atributo: str = Field(default="Color", min_length=1, description="Tipo de atributo (Color, Acabado, Tamaño, etc.)")
    valor: str = Field(..., min_length=1, description="Nombre o valor de la variante (ej. Kraft, Blanco, A5)")
    sku_variante: Optional[str] = Field(default=None, description="Código de referencia específico de la variante")
    precio_adicional: float = Field(default=0.0, description="Importe a sumar al precio base")
    precio_fijo: Optional[float] = Field(default=None, ge=0.0, description="Precio específico que reemplaza al precio base si está definido")
    color_hex: Optional[str] = Field(default=None, description="Código hexadecimal para previsualización visual (#FFFFFF)")


class ProductoVarianteCreate(ProductoVarianteBase):
    pass


class ProductoVarianteResponse(ProductoVarianteBase):
    id: int
    producto_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Producto Models ---
class ProductoBase(BaseModel):
    codigo: Optional[str] = None
    nombre: str = Field(..., min_length=1, description="Nombre del producto o servicio")
    descripcion: str = Field(..., min_length=1, description="Descripción del producto o servicio")
    precio_unitario_base: float = Field(default=0.0, ge=0.0, description="Precio unitario base")
    porcentaje_iva: float = Field(default=21.0, ge=0.0, le=100.0)
    aplica_irpf: bool = False
    porcentaje_irpf: float = Field(default=15.0, ge=0.0, le=100.0)
    escalados: list[ProductoEscaladoCreate] = Field(default_factory=list, description="Tramos de precios por volumen")
    variantes: list[ProductoVarianteCreate] = Field(default_factory=list, description="Variantes y colores del producto")

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def validar_no_vacio(cls, v):
        if v is None or not str(v).strip():
            raise ValueError("No puede estar vacío")
        return str(v).strip()


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_unitario_base: Optional[float] = Field(default=None, ge=0.0)
    porcentaje_iva: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    aplica_irpf: Optional[bool] = None
    porcentaje_irpf: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    escalados: Optional[list[ProductoEscaladoCreate]] = None
    variantes: Optional[list[ProductoVarianteCreate]] = None

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def validar_no_vacio_si_presente(cls, v):
        if v is not None and not str(v).strip():
            raise ValueError("No puede estar vacío")
        return str(v).strip() if v is not None else None


class ProductoResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: str
    precio_unitario_base: float = 0.0
    porcentaje_iva: float = 21.0
    aplica_irpf: bool = False
    porcentaje_irpf: float = 15.0
    created_at: Optional[str] = None
    escalados: list[ProductoEscaladoResponse] = Field(default_factory=list)
    variantes: list[ProductoVarianteResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


def calcular_precio_unitario_sugerido(
    precio_base: float,
    escalados: list = None,
    variantes: list = None,
    cantidad: float = 1.0,
    variante_id: Optional[int] = None
) -> float:
    """Calcula el precio unitario sugerido combinando variantes y tramos de cantidad por volumen."""
    precio = precio_base

    # 1. Aplicar tramo de escalado si coincide con la cantidad
    if escalados and cantidad > 0:
        def _get_min(e):
            return e.get("cantidad_minima", 0) if isinstance(e, dict) else getattr(e, "cantidad_minima", 0)
        sorted_esc = sorted(escalados, key=_get_min, reverse=True)
        for esc in sorted_esc:
            c_min = esc.get("cantidad_minima", 0) if isinstance(esc, dict) else getattr(esc, "cantidad_minima", 0)
            c_max = esc.get("cantidad_maxima") if isinstance(esc, dict) else getattr(esc, "cantidad_maxima", None)
            pu = esc.get("precio_unitario") if isinstance(esc, dict) else getattr(esc, "precio_unitario", 0)
            if cantidad >= c_min and (c_max is None or cantidad <= c_max):
                precio = pu
                break

    # 2. Aplicar variante si existe (precio_fijo reemplaza el precio; precio_adicional se suma)
    if variante_id and variantes:
        for v in variantes:
            vid = v.get("id") if isinstance(v, dict) else getattr(v, "id", None)
            if vid == variante_id:
                pf = v.get("precio_fijo") if isinstance(v, dict) else getattr(v, "precio_fijo", None)
                pa = v.get("precio_adicional") if isinstance(v, dict) else getattr(v, "precio_adicional", 0.0)
                if pf is not None:
                    precio = pf
                elif pa:
                    precio += pa
                break

    return round(float(precio), 4)


# --- Descuento Models ---
class DescuentoBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre de la promoción o descuento")
    codigo: Optional[str] = Field(default=None, description="Código promocional o alias único")
    tipo: str = Field(default="porcentaje", pattern="^(porcentaje|fijo)$", description="'porcentaje' o 'fijo'")
    valor: float = Field(..., ge=0.0, description="Porcentaje (ej. 15.0) o importe fijo en euros (ej. 50.0)")
    aplica_a: str = Field(default="todos", pattern="^(todos|productos)$", description="'todos' o 'productos'")
    descripcion: Optional[str] = None
    activo: bool = True
    producto_ids: list[int] = Field(default_factory=list, description="IDs de los productos vinculados si aplica_a == 'productos'")


class DescuentoCreate(DescuentoBase):
    pass


class DescuentoUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1)
    codigo: Optional[str] = None
    tipo: Optional[str] = Field(default=None, pattern="^(porcentaje|fijo)$")
    valor: Optional[float] = Field(default=None, ge=0.0)
    aplica_a: Optional[str] = Field(default=None, pattern="^(todos|productos)$")
    descripcion: Optional[str] = None
    activo: Optional[bool] = None
    producto_ids: Optional[list[int]] = None


class DescuentoResponse(BaseModel):
    id: int
    nombre: str
    codigo: Optional[str] = None
    tipo: str = "porcentaje"
    valor: float = 0.0
    aplica_a: str = "todos"
    descripcion: Optional[str] = None
    activo: bool = True
    created_at: Optional[str] = None
    producto_ids: list[int] = Field(default_factory=list)
    productos_nombres: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Linea Factura Models ---
class LineaFacturaCreate(BaseModel):
    producto_id: Optional[int] = None
    descripcion: str = Field(..., min_length=1, description="Descripción de la línea")
    detalle_material: Optional[str] = Field(default=None, description="Detalle del material, acabado o especificación")
    cantidad: float = Field(default=1.0, gt=0.0, description="La cantidad debe ser mayor a 0")
    precio_unitario: float = Field(default=0.0, description="Precio unitario (puede ser negativo para descuentos o deducciones)")
    porcentaje_descuento: float = Field(default=0.0, ge=0.0, le=100.0)
    porcentaje_iva: float = Field(default=21.0, ge=0.0, le=100.0)
    porcentaje_irpf: float = Field(default=0.0, ge=0.0, le=100.0)
    descuento_id: Optional[int] = None
    precio_unitario_original: Optional[float] = None


class LineaFacturaResponse(LineaFacturaCreate):
    id: int
    factura_id: int
    subtotal_base: float

    model_config = ConfigDict(from_attributes=True)


# --- Factura Models ---
ESTADOS_FACTURA_VALIDOS = {'Borrador', 'Emitida', 'Pagada', 'Vencida', 'Anulada'}


class FacturaCreate(BaseModel):
    cliente_id: int = Field(..., gt=0, description="ID del cliente receptor")
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    observaciones: Optional[str] = None
    lineas: list[LineaFacturaCreate] = Field(..., min_length=1, description="Debe contener al menos una línea")
    estado: str = 'Emitida'
    sin_iva: bool = False
    descuento_id: Optional[int] = None
    descuento_nombre: Optional[str] = None
    descuento_tipo: Optional[str] = None
    descuento_valor: Optional[float] = 0.0
    descuento_importe_total: Optional[float] = 0.0
    descuento_visible: Optional[bool] = True

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in ESTADOS_FACTURA_VALIDOS:
            raise ValueError(f"Estado '{v}' no válido. Opciones: {', '.join(sorted(ESTADOS_FACTURA_VALIDOS))}")
        return v

    @model_validator(mode='after')
    def validar_fechas(self) -> 'FacturaCreate':
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_emision:
            raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha de emisión.")
        return self


class FacturaUpdate(BaseModel):
    estado: str

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in ESTADOS_FACTURA_VALIDOS:
            raise ValueError(f"Estado '{v}' no válido. Opciones: {', '.join(sorted(ESTADOS_FACTURA_VALIDOS))}")
        return v


class FacturaUpdateFull(BaseModel):
    cliente_id: Optional[int] = Field(default=None, gt=0, description="ID del cliente receptor")
    fecha_emision: Optional[date] = Field(default=None, description="Fecha de emisión")
    fecha_vencimiento: Optional[date] = Field(default=None, description="Fecha de vencimiento")
    observaciones: Optional[str] = Field(default=None, max_length=1000)
    estado: Optional[str] = Field(default=None)
    sin_iva: Optional[bool] = None
    descuento_id: Optional[int] = None
    descuento_nombre: Optional[str] = None
    descuento_tipo: Optional[str] = None
    descuento_valor: Optional[float] = None
    descuento_importe_total: Optional[float] = None
    descuento_visible: Optional[bool] = None
    lineas: Optional[list[LineaFacturaCreate]] = Field(default=None, min_length=1, description="Líneas de la factura")


class FacturaResponse(BaseModel):
    id: int
    numero_factura: str
    serie: str
    correlativo: int
    fecha_emision: str
    fecha_vencimiento: Optional[str] = None
    cliente_id: int
    cliente_razon_social: Optional[str] = None
    cliente_nif_cif: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_direccion: Optional[str] = None
    cliente_ciudad: Optional[str] = None
    cliente_provincia: Optional[str] = None
    cliente_forma_pago: Optional[str] = None
    base_imponible_total: float
    iva_total: float
    irpf_total: float
    total_factura: float
    estado: str
    sin_iva: Optional[bool] = False
    descuento_id: Optional[int] = None
    descuento_nombre: Optional[str] = None
    descuento_tipo: Optional[str] = None
    descuento_valor: Optional[float] = 0.0
    descuento_importe_total: Optional[float] = 0.0
    descuento_visible: Optional[bool] = True
    observaciones: Optional[str] = None
    emisor_snapshot: Optional[str] = None
    created_at: Optional[str] = None
    lineas: Optional[list[LineaFacturaResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# --- Configuracion Models ---
class ConfiguracionData(BaseModel):
    nombre: Optional[str] = ""
    nif: Optional[str] = ""
    direccion: Optional[str] = ""
    codigo_postal: Optional[str] = ""
    ciudad: Optional[str] = ""
    provincia: Optional[str] = ""
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    web: Optional[str] = ""
    iban: Optional[str] = ""
    serie_defecto: Optional[str] = "Factura Nº"
    numero_inicio_factura: Optional[int] = Field(default=1, ge=1, description="Número correlativo de inicio de facturación")
    serie_sin_iva: Optional[str] = "Factura Sin IVA Nº"
    numero_inicio_factura_sin_iva: Optional[int] = Field(default=1, ge=1, description="Número correlativo de inicio para facturas sin IVA")
    iva_defecto: Optional[float] = Field(default=21.0, ge=0.0, le=100.0)
    irpf_defecto: Optional[float] = Field(default=0.0, ge=0.0, le=100.0)
    # Textos editoriales y de proceso configurables
    presupuesto_instagram: Optional[str] = ""
    presupuesto_email: Optional[str] = ""
    presupuesto_bienvenida_titulo: Optional[str] = ""
    presupuesto_bienvenida_subtitulo: Optional[str] = ""
    presupuesto_bienvenida_texto: Optional[str] = ""
    presupuesto_proceso_titulo: Optional[str] = ""
    presupuesto_proceso_subtitulo: Optional[str] = ""
    proceso_fase1_titulo: Optional[str] = ""
    proceso_fase1_puntos: Optional[str] = ""
    proceso_fase2_titulo: Optional[str] = ""
    proceso_fase2_puntos: Optional[str] = ""
    proceso_fase3_titulo: Optional[str] = ""
    proceso_fase3_puntos: Optional[str] = ""
    proceso_fase4_titulo: Optional[str] = ""
    proceso_fase4_puntos: Optional[str] = ""
    presupuesto_proceso_cierre: Optional[str] = ""
    factura_condiciones: Optional[str] = ""
    presupuesto_condiciones: Optional[str] = ""
    pdf_storage_dir: Optional[str] = ""
    factura_incluir_portada: Optional[str] = "false"
    onboarding_completado: Optional[str] = "false"

    @field_validator('nif')
    @classmethod
    def validar_nif_emisor(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return ""
        saneado = sanear_identificador(v)
        valido, _, _ = validar_nif_cif_nie(saneado)
        if not valido:
            raise ValueError(f"El NIF/CIF del emisor '{v}' no tiene un formato válido.")
        return saneado

    @field_validator('iban')
    @classmethod
    def validar_iban_emisor(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return ""
        valido, msg, saneado = validar_iban(v, permitir_vacio=True)
        if not valido:
            raise ValueError(msg)
        return saneado

    @field_validator('codigo_postal')
    @classmethod
    def validar_cp_emisor(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return ""
        cp = v.strip()
        if not validar_codigo_postal(cp):
            raise ValueError(f"El código postal '{v}' no es válido para España.")
        return cp


class ConfiguracionResponse(BaseModel):
    datos: ConfiguracionData
    es_valida: bool
    campos_faltantes: list[str] = []


# --- Presupuesto Models ---
class PresupuestoLineaBase(BaseModel):
    descripcion: str = Field(..., min_length=1, description="Descripción del producto")
    detalle_material: Optional[str] = Field(default="", description="Detalle del material, papel, gramaje o especificación")
    cantidad: float = Field(default=1.0, gt=0, description="Cantidad")
    precio_unitario: float = Field(default=0.0, description="Precio unitario sin IVA")
    orden: int = Field(default=1, ge=0)
    descuento_id: Optional[int] = None
    precio_unitario_original: Optional[float] = None


class PresupuestoLineaCreate(PresupuestoLineaBase):
    pass


class PresupuestoLineaResponse(PresupuestoLineaBase):
    id: int
    opcion_id: int
    total: float
    model_config = ConfigDict(from_attributes=True)


class PresupuestoOpcionBase(BaseModel):
    nombre_opcion: str = Field(..., min_length=1, description="Nombre de la variante (ej. Opción A - Sobre artesanal)")
    descripcion_corta: Optional[str] = None
    orden: int = Field(default=1, ge=0)
    descuento_id: Optional[int] = None
    descuento_nombre: Optional[str] = None
    descuento_tipo: Optional[str] = None
    descuento_valor: Optional[float] = 0.0
    descuento_importe_total: Optional[float] = 0.0
    descuento_visible: Optional[bool] = True


class PresupuestoOpcionCreate(PresupuestoOpcionBase):
    lineas: list[PresupuestoLineaCreate] = Field(..., min_length=1, description="Líneas de la opción")


class PresupuestoOpcionResponse(PresupuestoOpcionBase):
    id: int
    presupuesto_id: int
    subtotal: float
    total: float
    lineas: list[PresupuestoLineaResponse] = []
    model_config = ConfigDict(from_attributes=True)


class PresupuestoBase(BaseModel):
    numero_presupuesto: str = Field(..., min_length=1, description="Identificador único (ej. YYYY-MM-DD-nombre)")
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    fecha: date = Field(default_factory=date.today)
    fecha_validez: Optional[date] = None
    titulo: str = Field(default="Presupuesto de Servicios", min_length=1)
    subtitulo: Optional[str] = Field(default="Propuesta de servicios y condiciones comerciales")
    observaciones: Optional[str] = None
    estado: str = Field(default="Borrador", description="Borrador, Enviado, Aceptado, Rechazado, Facturado")
    porcentaje_iva: Optional[float] = 21.0
    porcentaje_irpf: Optional[float] = 0.0
    sin_iva: Optional[bool] = False

    @field_validator("titulo", mode="before")
    @classmethod
    def validar_titulo(cls, v):
        if not v or not str(v).strip():
            return "Presupuesto de Servicios"
        return str(v).strip()

    @field_validator("subtitulo", mode="before")
    @classmethod
    def validar_subtitulo(cls, v):
        if v is None or not str(v).strip():
            return "Propuesta de servicios y condiciones comerciales"
        return str(v).strip()

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v):
        if not v or str(v).strip() == "":
            return date.today()
        return v

    @field_validator("fecha_validez", mode="before")
    @classmethod
    def validar_fecha_validez(cls, v):
        if v == "" or v is None:
            return None
        return v


class PresupuestoCreate(PresupuestoBase):
    opciones: list[PresupuestoOpcionCreate] = Field(..., min_length=1, description="Opciones del presupuesto")


class PresupuestoEstadoUpdate(BaseModel):
    estado: str = Field(..., pattern="^(Borrador|Enviado|Aceptado|Rechazado|Facturado)$")
    opcion_aprobada_id: Optional[int] = None
    motivo: Optional[str] = None
    porcentaje_iva: Optional[float] = None
    porcentaje_irpf: Optional[float] = None
    sin_iva: Optional[bool] = None


class PresupuestoUpdate(BaseModel):
    numero_presupuesto: Optional[str] = None
    cliente_id: Optional[int] = None
    fecha: Optional[date] = None
    fecha_validez: Optional[date] = None
    titulo: Optional[str] = None
    subtitulo: Optional[str] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = None
    opcion_aprobada_id: Optional[int] = None
    porcentaje_iva: Optional[float] = None
    porcentaje_irpf: Optional[float] = None
    sin_iva: Optional[bool] = None
    opciones: Optional[list[PresupuestoOpcionCreate]] = None

    @field_validator("fecha_validez", mode="before")
    @classmethod
    def validar_fecha_validez(cls, v):
        if v == "" or v is None:
            return None
        return v


class PresupuestoResponse(BaseModel):
    id: int
    numero_presupuesto: str
    cliente_id: int
    cliente_nombre: str
    cliente_nif: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_email: Optional[str] = None
    fecha: str
    fecha_validez: Optional[str] = None
    titulo: str
    subtitulo: Optional[str] = None
    estado: str
    total_minimo: float
    total_maximo: float
    cantidad_opciones: int
    porcentaje_iva: Optional[float] = 21.0
    porcentaje_irpf: Optional[float] = 0.0
    sin_iva: Optional[bool] = False
    factura_id: Optional[int] = None
    numero_factura: Optional[str] = None
    opcion_aprobada_id: Optional[int] = None
    opcion_aprobada_nombre: Optional[str] = None
    opcion_aprobada_total: Optional[float] = None
    created_at: str
    model_config = ConfigDict(from_attributes=True)


class PresupuestoDetailResponse(BaseModel):
    id: int
    numero_presupuesto: str
    cliente_id: int
    cliente: ClienteResponse
    fecha: str
    fecha_validez: Optional[str] = None
    titulo: str
    subtitulo: Optional[str] = None
    estado: str
    porcentaje_iva: Optional[float] = 21.0
    porcentaje_irpf: Optional[float] = 0.0
    sin_iva: Optional[bool] = False
    factura_id: Optional[int] = None
    opcion_aprobada_id: Optional[int] = None
    opcion_aprobada_nombre: Optional[str] = None
    opcion_aprobada_total: Optional[float] = None
    observaciones: Optional[str] = None
    opciones: list[PresupuestoOpcionResponse] = []
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)


class PresupuestoConvertirFacturaRequest(BaseModel):
    opcion_id: int = Field(..., gt=0, description="ID de la opción seleccionada/aprobada")
    serie: Optional[str] = None
    fecha_emision: Optional[date] = None
    porcentaje_iva: Optional[float] = Field(default=21.0, ge=0.0, le=100.0)
    porcentaje_irpf: Optional[float] = Field(default=0.0, ge=0.0, le=100.0)
    sin_iva: Optional[bool] = False
    tipo_facturacion: str = Field(default="total", description="'total' o 'anticipo'")
    importe_anticipo: Optional[float] = Field(default=None, ge=0.0)



class PresupuestoPreviewLinea(BaseModel):
    descripcion: Optional[str] = "Producto"
    detalle_material: Optional[str] = ""
    cantidad: float = 1.0
    precio_unitario: float = 0.0
    orden: Optional[int] = 1


class PresupuestoPreviewOpcion(BaseModel):
    nombre_opcion: Optional[str] = "Opción A"
    orden: Optional[int] = 1
    lineas: list[PresupuestoPreviewLinea] = []


class PresupuestoPreviewRequest(BaseModel):
    numero_presupuesto: Optional[str] = "BORRADOR"
    cliente_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    fecha: Optional[date] = None
    fecha_validez: Optional[date] = None
    titulo: Optional[str] = "Presupuesto de Servicios"
    subtitulo: Optional[str] = "Propuesta de servicios y condiciones comerciales"
    opciones: list[PresupuestoPreviewOpcion] = []
    condiciones_texto: Optional[str] = None


class OnboardingRequest(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre o Razón Social del emisor")
    nif: str = Field(..., min_length=1, description="NIF o CIF del emisor")
    direccion: Optional[str] = ""
    codigo_postal: Optional[str] = ""
    ciudad: Optional[str] = ""
    provincia: Optional[str] = ""
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    iban: Optional[str] = ""
    pdf_storage_dir: Optional[str] = ""
    crear_acceso_escritorio: Optional[bool] = True

    @field_validator('nif')
    @classmethod
    def validar_nif(cls, v: str) -> str:
        saneado = sanear_identificador(v)
        valido, _, _ = validar_nif_cif_nie(saneado)
        if not valido:
            raise ValueError(f"El NIF/CIF del emisor '{v}' no tiene un formato válido.")
        return saneado

    @field_validator('iban')
    @classmethod
    def validar_iban(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return ""
        valido, msg, saneado = validar_iban(v, permitir_vacio=True)
        if not valido:
            raise ValueError(msg)
        return saneado

    @field_validator('codigo_postal')
    @classmethod
    def validar_cp(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return ""
        cp = v.strip()
        if not validar_codigo_postal(cp):
            raise ValueError(f"El código postal '{v}' no es válido para España.")
        return cp

class ConfiguracionPresupuestoData(BaseModel):
    presupuesto_instagram: Optional[str] = ""
    presupuesto_email: Optional[str] = ""
    presupuesto_bienvenida_titulo: Optional[str] = "Bienvenidos"
    presupuesto_bienvenida_subtitulo: Optional[str] = "Presentación de Servicios"
    presupuesto_bienvenida_texto: Optional[str] = ""
    presupuesto_condiciones: Optional[str] = ""
    presupuesto_proceso_titulo: Optional[str] = "Proceso de trabajo"
    presupuesto_proceso_subtitulo: Optional[str] = "Fases del proyecto y tiempos de ejecución"
    presupuesto_proceso_cierre: Optional[str] = ""
