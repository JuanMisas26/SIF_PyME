import os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from typing import Any, Optional

try:
    from fpdf import FPDF
except ImportError:
    raise ImportError("fpdf2 not installed. Run: pip install fpdf2")

# ============================================================
# CONFIGURACIÓN DE LA EMPRESA (editar según datos reales)
# ============================================================
EMPRESA = {
    "nombre": "Mi Empresa",
    "nif": "",
    "direccion": "",
    "ciudad": "",
    "codigo_postal": "",
    "provincia": "",
    "telefono": "",
    "email": "",
    "web": "",
    "iban": "",
    "logo_path": None,
}

DEFAULT_PDF_INSTAGRAM = os.getenv("DEFAULT_PDF_INSTAGRAM", "")
DEFAULT_PDF_EMAIL = os.getenv("DEFAULT_PDF_EMAIL", "")

import app.paths as paths_module
from app.paths import STATIC_DIR


def round2(value) -> Decimal:
    """Financial rounding to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_totales_linea(linea: dict[str, Any]) -> dict[str, Any]:
    """Calculate line totals with financial precision."""
    cantidad = Decimal(str(linea.get('cantidad', 1.0)))
    precio = Decimal(str(linea.get('precio_unitario', 0.0)))
    descuento_pct = Decimal(str(linea.get('porcentaje_descuento', 0.0)))
    iva_pct = Decimal(str(linea.get('porcentaje_iva', 21.0)))
    irpf_pct = Decimal(str(linea.get('porcentaje_irpf', 0.0)))

    precio_con_descuento = precio * (1 - descuento_pct / 100)
    subtotal_base = round2(cantidad * precio_con_descuento)
    iva_amount = round2(subtotal_base * iva_pct / 100)
    irpf_amount = round2(subtotal_base * irpf_pct / 100)

    return {
        'subtotal_base': float(subtotal_base),
        'iva_amount': float(iva_amount),
        'irpf_amount': float(irpf_amount),
        'total_linea': float(subtotal_base + iva_amount - irpf_amount)
    }


def calcular_totales_factura(lineas: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate invoice totals aggregating all lines with VAT breakdown."""
    base_total = Decimal('0.00')
    iva_total = Decimal('0.00')
    irpf_total = Decimal('0.00')
    desglose_iva: dict[float, dict[str, float]] = {}

    for linea in lineas:
        totales = calcular_totales_linea(linea)
        base = Decimal(str(totales['subtotal_base']))
        iva = Decimal(str(totales['iva_amount']))
        irpf = Decimal(str(totales['irpf_amount']))
        iva_pct = float(linea.get('porcentaje_iva', 21.0))

        base_total += base
        iva_total += iva
        irpf_total += irpf

        # Acumular en el desglose de IVA (incluso importes negativos como abonos o anticipos)
        if base != 0 or iva != 0:
            if iva_pct not in desglose_iva:
                desglose_iva[iva_pct] = {'base': 0.0, 'cuota': 0.0}
            desglose_iva[iva_pct]['base'] = float(round2(Decimal(str(desglose_iva[iva_pct]['base'])) + base))
            desglose_iva[iva_pct]['cuota'] = float(round2(Decimal(str(desglose_iva[iva_pct]['cuota'])) + iva))

    total_factura = base_total + iva_total - irpf_total

    return {
        'base_imponible_total': float(round2(base_total)),
        'iva_total': float(round2(iva_total)),
        'irpf_total': float(round2(irpf_total)),
        'total_factura': float(round2(total_factura)),
        'desglose_iva': desglose_iva
    }


def formatear_numero_factura(serie: str, correlativo: int) -> str:
    """
    Formatea el número oficial de la factura según la serie y el correlativo.
    Por defecto genera: 'Factura Nº [numero]'.
    Si la serie incluye delimitadores (como '-' o '/'), concatena directamente.
    """
    s = (serie or "Factura Nº").strip()
    if s.endswith(('-', '/', ' ')):
        return f"{s}{correlativo}"
    elif "nº" in s.lower() or "n°" in s.lower():
        return f"{s} {correlativo}"
    else:
        return f"{s}-{correlativo}"


def generar_numero_factura(
    conn,
    serie: Optional[str] = None,
    fecha: Optional[Any] = None,
    sin_iva: bool = False
) -> tuple[str, int]:
    """Genera el siguiente número correlativo de factura de forma configurable.

    Por defecto:
    - Facturas con IVA: serie 'Factura Nº', comenzando en 'numero_inicio_factura' (1 por defecto).
    - Facturas sin IVA: serie 'Factura Sin IVA Nº', comenzando en 'numero_inicio_factura_sin_iva' (1 por defecto).
    Garantiza secuencias correlativas independientes y unicidad absoluta contra cualquier factura existente o borrada.
    """
    cursor = conn.cursor()

    clave_serie = "serie_sin_iva" if sin_iva else "serie_defecto"
    default_serie = "Factura Sin IVA Nº" if sin_iva else "Factura Nº"

    # 1. Determinar serie/prefijo
    if not serie or not str(serie).strip() or str(serie).strip() in ('FAC-2026', 'FAC'):
        try:
            cfg_row = cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave_serie,)).fetchone()
            if cfg_row and cfg_row[0] and cfg_row[0].strip() and cfg_row[0].strip() not in ('FAC-2026', 'FAC'):
                serie = cfg_row[0].strip()
            else:
                serie = default_serie
        except Exception:
            serie = default_serie
    else:
        serie = str(serie).strip()

    # 2. Obtener número de inicio configurado según si es con o sin IVA
    clave_inicio = "numero_inicio_factura_sin_iva" if sin_iva else "numero_inicio_factura"
    numero_inicio = 1
    try:
        cfg_ini = cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave_inicio,)).fetchone()
        if cfg_ini and cfg_ini[0]:
            v_int = int(str(cfg_ini[0]).strip())
            if v_int >= 1:
                numero_inicio = v_int
    except Exception:
        numero_inicio = 1

    # 3. Buscar el correlativo máximo existente para esta serie
    try:
        row = cursor.execute(
            "SELECT MAX(correlativo) as max_corr FROM facturas WHERE serie = ?",
            (serie,)
        ).fetchone()
        max_corr = row['max_corr'] if (row and row['max_corr'] is not None) else 0
    except Exception:
        max_corr = 0

    correlativo = max(max_corr + 1, numero_inicio)

    # 4. Asegurar unicidad absoluta contra cualquier factura existente o borrada
    while True:
        numero = formatear_numero_factura(serie, correlativo)
        exists = cursor.execute(
            "SELECT 1 FROM facturas WHERE numero_factura = ?",
            (numero,)
        ).fetchone()
        if not exists:
            break
        correlativo += 1

    return numero, correlativo


NOMBRES_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def get_pdf_output_path(numero_factura: str, fecha_emision, sin_iva: bool = False) -> Path:
    """Get organized PDF output path: ~/Facturas/PDFs/{YEAR}/{QUARTER}/{MONTH_NUM}_{MONTH_NAME}/{Con_IVA|Sin_IVA}/"""
    if isinstance(fecha_emision, str):
        fecha = datetime.strptime(fecha_emision, '%Y-%m-%d').date()
    elif isinstance(fecha_emision, date):
        fecha = fecha_emision
    else:
        fecha = datetime.now().date()

    base_dir = paths_module.get_pdf_storage_dir()
    trimestre = f"{(fecha.month - 1) // 3 + 1}T"
    nombre_mes = NOMBRES_MESES[fecha.month - 1]
    month_folder = f"{fecha.month:02d}_{nombre_mes}"
    iva_folder = "Sin_IVA" if sin_iva else "Con_IVA"
    iva_dir = base_dir / str(fecha.year) / trimestre / month_folder / iva_folder
    iva_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{numero_factura.replace('/', '-')}.pdf"
    new_path = iva_dir / filename

    # 1. Si existía en la carpeta del régimen opuesto (p. ej. si se cambió el flag sin_iva al editar)
    other_iva_folder = "Con_IVA" if sin_iva else "Sin_IVA"
    other_iva_path = base_dir / str(fecha.year) / trimestre / month_folder / other_iva_folder / filename
    if other_iva_path.exists():
        try:
            import shutil
            if not new_path.exists():
                shutil.move(str(other_iva_path), str(new_path))
            else:
                other_iva_path.unlink()
            if other_iva_path.parent.exists() and not any(other_iva_path.parent.iterdir()):
                other_iva_path.parent.rmdir()
        except Exception:
            pass

    # 2. Compatibilidad con archivos previamente guardados en rutas anteriores sin subcarpeta de IVA:
    # a. Directamente en el mes: {YEAR}/{TRIMESTRE}/{MONTH_NUM}_{MONTH_NAME}/
    legacy_path_in_month = base_dir / str(fecha.year) / trimestre / month_folder / filename
    # b. Ruta sin trimestre: {YEAR}/{MONTH_NUM}_{MONTH_NAME}/
    old_path_no_trim = base_dir / str(fecha.year) / month_folder / filename
    # c. Ruta antigua inicial: {YEAR}/{MONTH:02d}/
    old_path_raw_month = base_dir / str(fecha.year) / f"{fecha.month:02d}" / filename

    for old_path in (legacy_path_in_month, old_path_no_trim, old_path_raw_month):
        if old_path.exists() and not new_path.exists():
            try:
                import shutil
                shutil.move(str(old_path), str(new_path))
                # Limpiar directorio anterior si quedó vacío
                curr = old_path.parent
                while curr != base_dir and curr.exists() and not any(curr.iterdir()):
                    curr.rmdir()
                    curr = curr.parent
                break
            except Exception:
                return old_path

    return new_path


def eliminar_pdf_factura(numero_factura: str, fecha_emision: Any, sin_iva: Optional[bool] = None) -> bool:
    """
    Elimina físicamente el archivo PDF de una factura y limpia directorios padre
    vacíos (con_iva/sin_iva, mes, trimestre, año) para evitar archivos huérfanos o visibilidad de facturas borradas.
    """
    try:
        if isinstance(fecha_emision, str):
            fecha = datetime.strptime(fecha_emision, '%Y-%m-%d').date()
        elif isinstance(fecha_emision, date):
            fecha = fecha_emision
        else:
            fecha = datetime.now().date()

        base_dir = paths_module.get_pdf_storage_dir()
        trimestre = f"{(fecha.month - 1) // 3 + 1}T"
        nombre_mes = NOMBRES_MESES[fecha.month - 1]
        month_folder = f"{fecha.month:02d}_{nombre_mes}"
        filename = f"{numero_factura.replace('/', '-')}.pdf"
        month_dir = base_dir / str(fecha.year) / trimestre / month_folder

        candidatos = [
            month_dir / "Con_IVA" / filename,
            month_dir / "Sin_IVA" / filename,
            month_dir / filename,
            base_dir / str(fecha.year) / month_folder / filename,
            base_dir / str(fecha.year) / f"{fecha.month:02d}" / filename,
        ]

        eliminado = False
        for path in candidatos:
            if path.exists():
                try:
                    path.unlink()
                    eliminado = True
                except Exception:
                    pass

        # Limpiar directorios vacíos hacia arriba (iva_dir, mes, trimestre, año)
        dirs_a_limpiar = [
            month_dir / "Con_IVA",
            month_dir / "Sin_IVA",
            month_dir,
            base_dir / str(fecha.year) / trimestre,
            base_dir / str(fecha.year),
        ]
        for d in dirs_a_limpiar:
            if d.exists() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except Exception:
                    pass

        return eliminado
    except Exception:
        return False


# ── PALETA EDITORIAL (DISEÑO SIF PYME) ──
COLOR_TEXT = (91, 80, 73)          # #5b5049 Warm taupe / espresso
COLOR_TEXT_MUTED = (122, 112, 105)   # #7a7069 Muted taupe
COLOR_BORDER = (213, 204, 190)      # #d5ccbe Sand / beige border
COLOR_CARD_BG = (242, 240, 239)     # #f2f0ef Off-white warm cream
COLOR_WHITE = (255, 255, 255)
COLOR_BAND = (215, 207, 194)        # #d7cfc2 Top band on process page

COLOR_Q1 = (130, 108, 87)           # #826c57
COLOR_Q2 = (171, 150, 121)          # #ab9679
COLOR_Q3 = (83, 68, 56)             # #534438
COLOR_Q4 = (198, 180, 158)          # #c6b49e


class FacturaPDF(FPDF):
    """Custom FPDF class for editorial invoice generation."""
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=False)
        self._setup_fonts()

    def _setup_fonts(self):
        fonts_dir = str(STATIC_DIR / 'fonts')
        georgia = os.path.join(fonts_dir, 'georgia.ttf')
        georgiab = os.path.join(fonts_dir, 'georgiab.ttf')
        georgiai = os.path.join(fonts_dir, 'georgiai.ttf')
        inter = os.path.join(fonts_dir, 'Inter-Regular.ttf')
        inter_b = os.path.join(fonts_dir, 'Inter-Bold.ttf')

        if os.path.exists(georgia):
            self.add_font('Georgia', '', georgia)
            self.add_font('Georgia', 'B', georgiab if os.path.exists(georgiab) else georgia)
            self.add_font('Georgia', 'I', georgiai if os.path.exists(georgiai) else georgia)
            self.serif_font = 'Georgia'
        else:
            self.serif_font = 'Times'

        if os.path.exists(inter):
            self.add_font('Inter', '', inter)
            if os.path.exists(inter_b):
                self.add_font('Inter', 'B', inter_b)
            else:
                self.add_font('Inter', 'B', inter)
            self.sans_font = 'Inter'
        else:
            self.sans_font = 'Helvetica'


def _fit_cell_text(pdf_obj, text: str, max_w: float) -> str:
    """Ajusta un texto al ancho en mm para evitar que sobresalga de la celda en el PDF."""
    if not text:
        return ""
    if pdf_obj.get_string_width(text) <= max_w:
        return text
    ellipsis = "…"
    el_w = pdf_obj.get_string_width(ellipsis)
    while text and (pdf_obj.get_string_width(text) + el_w) > max_w:
        text = text[:-1]
    return text.rstrip() + ellipsis


def fmt_eur(amount: float) -> str:
    """Format euro amounts with Spanish format: 1.234,56 €"""
    return f"{amount:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_date_es(d_str: Any) -> str:
    """Format dates to DD/MM/YYYY"""
    if not d_str:
        return '—'
    try:
        s = str(d_str)[:10]
        parts = s.split('-')
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return s
    except Exception:
        return str(d_str)


def generar_pdf_factura(
    factura_data: dict[str, Any],
    lineas_data: list[dict[str, Any]],
    cliente_data: dict[str, Any],
    output_path: Path,
    emisor_data: Optional[dict[str, Any]] = None
) -> Path:
    """Generate an editorial multi-page PDF invoice matching the brand aesthetic with overflow protection."""

    emisor = dict(EMPRESA)
    if emisor_data:
        for k, v in emisor_data.items():
            if v:
                emisor[k] = v

    pdf = FacturaPDF()

    img_dir = str(STATIC_DIR / 'img' / 'presupuesto')
    portada_img = os.path.join(img_dir, 'portada_default.jpg')
    bienvenida_img = os.path.join(img_dir, 'bienvenida_default.jpg')

    instagram = emisor.get('presupuesto_instagram') or emisor.get('web') or DEFAULT_PDF_INSTAGRAM
    emisor_email = emisor.get('presupuesto_email') or emisor.get('email') or DEFAULT_PDF_EMAIL
    fecha_emision = str(factura_data.get('fecha_emision', '2026-01-01'))[:10]
    year = fecha_emision[:4] if len(fecha_emision) >= 4 else '2026'
    numero_factura = factura_data.get('numero_factura', 'FAC-2026-0001')
    cliente_nombre = cliente_data.get('razon_social', 'Cliente')

    # Totales financieros
    totales_factura = calcular_totales_factura(lineas_data)
    if 'total_factura' in factura_data and factura_data['total_factura'] is not None:
        totales_factura['total_factura'] = float(factura_data['total_factura'])
    if 'base_imponible_total' in factura_data and factura_data['base_imponible_total'] is not None:
        totales_factura['base_imponible_total'] = float(factura_data['base_imponible_total'])
    if 'iva_total' in factura_data and factura_data['iva_total'] is not None:
        totales_factura['iva_total'] = float(factura_data['iva_total'])
    if 'irpf_total' in factura_data and factura_data['irpf_total'] is not None:
        totales_factura['irpf_total'] = float(factura_data['irpf_total'])

    # ══════════════════════════════════════════════════════════
    # PORTADA EDITORIAL (Opcional según configuración, desactivada por defecto para facturas contables)
    # ══════════════════════════════════════════════════════════
    incluir_portada = str(emisor.get('factura_incluir_portada', 'false')).strip().lower() in ('true', '1', 'yes', 'si')
    if incluir_portada:
        pdf.add_page()

        # Fondo / Foto de portada (respetando proporción para no deformar)
        if os.path.exists(portada_img):
            try:
                from PIL import Image
                with Image.open(portada_img) as img:
                    ratio = img.size[0] / img.size[1]
            except Exception:
                ratio = 1.086

            if 0.65 <= ratio <= 0.75:
                # Si la imagen ya tiene proporción vertical A4, cubre la página entera
                pdf.image(portada_img, x=0, y=0, w=210, h=297)
            else:
                # Si no es A4 (como la plantilla original 175x161 mm), se centra sin estirar
                img_w = 175
                img_h = img_w / ratio
                img_x = (210 - img_w) / 2
                img_y = 44
                pdf.image(portada_img, x=img_x, y=img_y, w=img_w, h=img_h)

        # Encima se dibujan los textos
        # Año superior
        pdf.set_xy(25, 20)
        pdf.set_font(pdf.sans_font, '', 13)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(40, 8, year, align='L')

        # Título en la parte inferior derecha
        pdf.set_xy(108, 218)
        pdf.set_font(pdf.serif_font, '', 28)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(85, 10, 'Factura', align='L')

        pdf.set_xy(108, 230)
        pdf.set_font(pdf.serif_font, 'I', 22)
        display_cli = cliente_nombre if len(cliente_nombre) <= 24 else cliente_nombre[:22] + '...'
        pdf.cell(85, 10, f"para {display_cli}", align='L')

        # Redes / Web al pie si existen
        if instagram:
            pdf.set_xy(25, 270)
            pdf.set_font(pdf.sans_font, '', 10)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(160, 6, instagram, align='C')

    # ══════════════════════════════════════════════════════════
    # PÁGINAS DE FACTURA: HOJA DE PRODUCTOS CON CONTROL DE DESBORDAMIENTO
    # ══════════════════════════════════════════════════════════
    card_x, card_y, card_w, card_h = 9.5, 8.5, 191, 280
    table_x = 19
    table_w = 172
    fecha_emision_es = fmt_date_es(factura_data.get('fecha_emision'))
    fecha_venc_es = fmt_date_es(factura_data.get('fecha_vencimiento'))
    estado_factura = factura_data.get('estado', 'Emitida')

    def draw_card_bg():
        pdf.add_page()
        pdf.set_fill_color(*COLOR_BORDER)
        pdf.rect(0, 0, 210, 297, style='F')
        pdf.set_fill_color(*COLOR_CARD_BG)
        pdf.rect(card_x, card_y, card_w, card_h, style='F')

    def render_first_header():
        # Encabezado "Factura"
        pdf.set_xy(table_x, 15)
        pdf.set_font(pdf.sans_font, 'B', 24)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(80, 10, 'Factura', align='L')

        # Subtítulo con Fecha (y Vencimiento si existe)
        sub_text = f"Fecha: {fecha_emision_es}"
        if factura_data.get('fecha_vencimiento'):
            sub_text += f"  ·  Vencimiento: {fecha_venc_es}"

        pdf.set_xy(table_x, 26)
        pdf.set_font(pdf.sans_font, '', 9.5)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(105, 5, sub_text, align='L')

        # Estado de la factura a la derecha
        pdf.set_xy(table_x + table_w - 75, 17)
        pdf.set_font(pdf.sans_font, '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(75, 5, f"ESTADO: {estado_factura.upper()}", align='R')

        # Número de factura debajo del estado
        pdf.set_xy(table_x + table_w - 75, 23)
        pdf.set_font(pdf.sans_font, 'B', 10)
        pdf.set_text_color(*COLOR_TEXT)
        display_num = numero_factura if str(numero_factura).lower().startswith(('factura', 'nº', 'n°')) else f"Nº {numero_factura}"
        pdf.cell(75, 5, display_num, align='R')

        # ── BLOQUE DE DATOS LEGALES: EMISOR Y CLIENTE ──
        y_info = 34

        # EMISOR (Columna izquierda)
        pdf.set_xy(table_x, y_info)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(82, 3.5, 'EMISOR', align='L')

        pdf.set_xy(table_x, y_info + 4)
        pdf.set_font(pdf.sans_font, '', 8.5)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(82, 4, (emisor.get('nombre') or 'Emisor')[:42], align='L')

        emisor_nif_str = f"NIF/CIF: {emisor.get('nif', '')}" if emisor.get('nif') else ""
        pdf.set_xy(table_x, y_info + 8)
        pdf.cell(82, 4, emisor_nif_str, align='L')

        emisor_dir_line = emisor.get('direccion', '') or ''
        emisor_ciudad_line = f"{emisor.get('codigo_postal', '') or ''} {emisor.get('ciudad', '') or ''}".strip()
        full_emisor_loc = ", ".join(filter(None, [emisor_dir_line, emisor_ciudad_line]))
        if full_emisor_loc:
            pdf.set_xy(table_x, y_info + 12)
            pdf.set_font(pdf.sans_font, '', 7.8)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(82, 3.8, full_emisor_loc[:46], align='L')

        # Contactos Emisor (Teléfono y Email en líneas independientes para correos largos)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        em_tel = emisor.get('telefono')
        em_email = emisor.get('email')
        if em_tel and em_email:
            pdf.set_xy(table_x, y_info + 16)
            pdf.cell(82, 3.5, f"Tel: {em_tel}", align='L')
            pdf.set_xy(table_x, y_info + 19.8)
            pdf.cell(82, 3.5, em_email, align='L')
        elif em_tel:
            pdf.set_xy(table_x, y_info + 16)
            pdf.cell(82, 3.5, f"Tel: {em_tel}", align='L')
        elif em_email:
            pdf.set_xy(table_x, y_info + 16)
            pdf.cell(82, 3.5, em_email, align='L')

        # CLIENTE (Columna derecha pegada al borde derecho)
        cli_w = 82
        cli_x = table_x + table_w - cli_w
        pdf.set_xy(cli_x, y_info)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(cli_w, 3.5, 'CLIENTE / DESTINATARIO', align='R')

        pdf.set_xy(cli_x, y_info + 4)
        pdf.set_font(pdf.sans_font, '', 8.5)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(cli_w, 4, cliente_nombre[:40], align='R')

        cli_nif = cliente_data.get('nif_cif')
        cli_nif_str = f"NIF/CIF: {cli_nif.strip()}" if cli_nif and str(cli_nif).strip() else "Cliente Particular (Sin NIF)"
        pdf.set_xy(cli_x, y_info + 8)
        pdf.cell(cli_w, 4, cli_nif_str, align='R')

        cli_dir = cliente_data.get('direccion', '') or ''
        cli_loc = f"{cliente_data.get('codigo_postal', '') or ''} {cliente_data.get('ciudad', '') or ''}".strip()
        full_cli_loc = ", ".join(filter(None, [cli_dir, cli_loc]))
        if full_cli_loc:
            pdf.set_xy(cli_x, y_info + 12)
            pdf.set_font(pdf.sans_font, '', 7.8)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(cli_w, 3.8, full_cli_loc[:46], align='R')

        # Contactos Cliente (Teléfono y Email en líneas independientes para correos largos)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        cli_tel = cliente_data.get('telefono')
        cli_email = cliente_data.get('email')
        if cli_tel and cli_email:
            pdf.set_xy(cli_x, y_info + 16)
            pdf.cell(cli_w, 3.5, f"Tel: {cli_tel}", align='R')
            pdf.set_xy(cli_x, y_info + 19.8)
            pdf.cell(cli_w, 3.5, cli_email, align='R')
        elif cli_tel:
            pdf.set_xy(cli_x, y_info + 16)
            pdf.cell(cli_w, 3.5, f"Tel: {cli_tel}", align='R')
        elif cli_email:
            pdf.set_xy(cli_x, y_info + 16)
            pdf.cell(cli_w, 3.5, cli_email, align='R')

        # ── ENCABEZADO TABLA ──
        table_y = 66
        pdf.set_xy(table_x, table_y + 2)
        pdf.set_font(pdf.sans_font, '', 8.0)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(95, 5.5, 'DESCRIPCIÓN', align='L')
        pdf.cell(22, 5.5, 'CANT.', align='C')
        pdf.cell(26, 5.5, 'PRECIO UNITARIO', align='R')
        pdf.cell(29, 5.5, 'TOTAL', align='R')

        # Línea entre encabezados y productos (0.75 pt ≈ 0.265 mm)
        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)
        pdf.line(table_x, table_y + 9.5, table_x + table_w, table_y + 9.5)

        return table_y + 11.5

    def render_continuation_header(page_num):
        pdf.set_xy(table_x, 16)
        pdf.set_font(pdf.sans_font, 'B', 18)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(100, 8, 'Factura (continuación)', align='L')

        pdf.set_xy(table_x, 24)
        pdf.set_font(pdf.sans_font, '', 9.5)
        display_hdr = numero_factura if str(numero_factura).lower().startswith(('factura', 'nº', 'n°')) else f"Nº {numero_factura}"
        pdf.cell(105, 5, f"{display_hdr}  ·  Fecha: {fecha_emision_es}  ·  Hoja {page_num}", align='L')

        table_y = 31
        pdf.set_xy(table_x, table_y + 2)
        pdf.set_font(pdf.sans_font, '', 8.0)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(95, 5.5, 'DESCRIPCIÓN', align='L')
        pdf.cell(22, 5.5, 'CANT.', align='C')
        pdf.cell(26, 5.5, 'PRECIO UNITARIO', align='R')
        pdf.cell(29, 5.5, 'TOTAL', align='R')

        # Línea entre encabezados y productos (0.75 pt ≈ 0.265 mm)
        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)
        pdf.line(table_x, table_y + 9.5, table_x + table_w, table_y + 9.5)

        return table_y + 11.5

    # Render primera página de productos
    page_num = 1
    draw_card_bg()
    curr_y = render_first_header()

    MAX_Y_WITH_FOOTER = 185.0
    MAX_Y_TABLE_BOTTOM = 265.0

    pdf.set_draw_color(*COLOR_TEXT)
    pdf.set_line_width(0.265)

    for i, l in enumerate(lineas_data):
        dto = float(l.get('porcentaje_descuento', 0.0))
        mat = l.get('detalle_material') or ''
        row_h = 11.5 if (mat and dto > 0) else (10.0 if (mat or dto > 0) else 8.5)
        is_last_line = (i == len(lineas_data) - 1)
        threshold = MAX_Y_WITH_FOOTER if is_last_line else MAX_Y_TABLE_BOTTOM

        if (curr_y + row_h) > threshold:
            draw_card_bg()
            page_num += 1
            curr_y = render_continuation_header(page_num)

        desc = l.get('descripcion', '')
        cant = float(l.get('cantidad', 1.0))
        precio = float(l.get('precio_unitario', 0.0))

        totales_l = calcular_totales_linea(l)
        sub_l = totales_l['subtotal_base']

        cant_str = f"{int(cant)}" if cant == int(cant) else f"{cant:.2f}"
        precio_str = fmt_eur(precio)
        tot_str = fmt_eur(sub_l)

        pdf.set_xy(table_x, curr_y)
        pdf.set_font(pdf.sans_font, '', 8.5)
        pdf.set_text_color(*COLOR_TEXT)
        desc_fit = _fit_cell_text(pdf, desc, 88.0)
        pdf.cell(92, 4.5, desc_fit, align='L')
        pdf.cell(22, 4.5, cant_str, align='C')
        pdf.cell(26, 4.5, precio_str, align='R')
        pdf.cell(29, 4.5, tot_str, align='R')

        sub_y = curr_y + 4.2
        if mat:
            pdf.set_xy(table_x, sub_y)
            pdf.set_font(pdf.sans_font, '', 7.5)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(92, 4, mat[:65], align='L')
            if dto > 0:
                sub_y += 3.8

        es_descuento_visible = bool(factura_data.get('descuento_visible', 1))
        if dto > 0 and es_descuento_visible:
            pdf.set_xy(table_x, sub_y)
            pdf.set_font(pdf.sans_font, '', 7.5)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(92, 4, f"Descuento aplicado: {dto:.1f}%", align='L')

        curr_y += row_h
        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)
        pdf.line(table_x, curr_y, table_x + table_w, curr_y)
        curr_y += 1.5

    # ── BLOQUE DE TOTALES FINANCIEROS Y CONDICIONES ──
    # Si después de las líneas no hay espacio suficiente para totales + banco + condiciones, crear página de resumen
    if curr_y > MAX_Y_WITH_FOOTER:
        draw_card_bg()
        page_num += 1
        pdf.set_xy(table_x, 16)
        pdf.set_font(pdf.sans_font, 'B', 18)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(100, 8, 'Factura - Resumen y Pago', align='L')
        pdf.set_xy(table_x, 24)
        pdf.set_font(pdf.sans_font, '', 9.5)
        display_hdr = numero_factura if str(numero_factura).lower().startswith(('factura', 'nº', 'n°')) else f"Nº {numero_factura}"
        pdf.cell(105, 5, f"{display_hdr}  ·  Fecha: {fecha_emision_es}", align='L')
        tot_box_y = 38
    else:
        tot_box_y = max(curr_y + 4, 138)

    tot_box_x = table_x + 85
    tot_box_w = table_w - 85

    desc_importe = float(factura_data.get('descuento_importe_total', 0.0) or 0.0)
    desc_visible = bool(factura_data.get('descuento_visible', 1))
    desc_nombre = factura_data.get('descuento_nombre') or ''

    if desc_importe > 0 and desc_visible:
        subtotal_bruto = totales_factura['base_imponible_total'] + desc_importe
        pdf.set_xy(tot_box_x, tot_box_y)
        pdf.set_font(pdf.sans_font, '', 8.5)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(50, 4.5, 'Subtotal bruto:', align='L')
        pdf.cell(37, 4.5, fmt_eur(subtotal_bruto), align='R')
        tot_box_y += 4.5

        pdf.set_xy(tot_box_x, tot_box_y)
        pdf.set_text_color(37, 99, 235)
        label_dto = f"Descuento ({desc_nombre[:20]}):" if desc_nombre else "Descuento:"
        pdf.cell(50, 4.5, label_dto, align='L')
        pdf.cell(37, 4.5, f"-{fmt_eur(desc_importe)}", align='R')
        tot_box_y += 4.5
        pdf.set_text_color(*COLOR_TEXT)

    # Base Imponible
    pdf.set_xy(tot_box_x, tot_box_y)
    pdf.set_font(pdf.sans_font, '', 8.5)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(50, 4.5, 'Base imponible:', align='L')
    pdf.cell(37, 4.5, fmt_eur(totales_factura['base_imponible_total']), align='R')

    # IVA (con desglose si existe)
    iva_line_y = tot_box_y + 5
    desglose = totales_factura.get('desglose_iva', {})
    es_factura_sin_iva = bool(factura_data.get('sin_iva') or totales_factura.get('iva_total', 0) == 0)
    if es_factura_sin_iva:
        pdf.set_xy(tot_box_x, iva_line_y)
        pdf.cell(50, 4.5, 'IVA (0% Exento):', align='L')
        pdf.cell(37, 4.5, fmt_eur(0.0), align='R')
        iva_line_y += 4.5
    elif desglose:
        for iva_pct, vals in desglose.items():
            pdf.set_xy(tot_box_x, iva_line_y)
            label = "IVA (0% Exento):" if iva_pct == 0 else f"IVA ({iva_pct:g}%):"
            pdf.cell(50, 4.5, label, align='L')
            pdf.cell(37, 4.5, fmt_eur(vals['cuota']), align='R')
            iva_line_y += 4.5
    else:
        pdf.set_xy(tot_box_x, iva_line_y)
        pdf.cell(50, 4.5, 'IVA (21%):', align='L')
        pdf.cell(37, 4.5, fmt_eur(totales_factura['iva_total']), align='R')
        iva_line_y += 4.5

    # Retención IRPF (si aplica)
    if totales_factura['irpf_total'] > 0:
        pdf.set_xy(tot_box_x, iva_line_y)
        pdf.set_text_color(160, 50, 50)
        pdf.cell(50, 4.5, 'Retención IRPF:', align='L')
        pdf.cell(37, 4.5, f"-{fmt_eur(totales_factura['irpf_total'])}", align='R')
        iva_line_y += 4.5

    # Línea separadora previa al total final (0.75 pt ≈ 0.265 mm)
    pdf.set_draw_color(*COLOR_TEXT)
    pdf.set_line_width(0.265)
    pdf.line(tot_box_x, iva_line_y + 1, table_x + table_w, iva_line_y + 1)

    # TOTAL FACTURA (mismo tipo de letra sans_font que el resto del desglose, en negrita)
    pdf.set_xy(tot_box_x, iva_line_y + 3)
    pdf.set_font(pdf.sans_font, 'B', 10.5)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(45, 6, 'TOTAL FACTURA', align='L')
    pdf.set_font(pdf.sans_font, 'B', 11.5)
    pdf.cell(42, 6, fmt_eur(totales_factura['total_factura']), align='R')

    # ── BLOQUE INFERIOR: PAGO, BANCO Y CONDICIONES ──
    info_y = max(iva_line_y + 14, 246)

    # Caja de transferencia bancaria
    pdf.set_fill_color(248, 246, 243)
    pdf.set_draw_color(*COLOR_BORDER)
    pdf.set_line_width(0.2)
    pdf.rect(table_x, info_y, 95, 24, style='FD')

    pdf.set_xy(table_x + 3, info_y + 2)
    pdf.set_font(pdf.sans_font, '', 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(89, 3.5, 'DATOS PARA TRANSFERENCIA BANCARIA', align='L')

    iban = emisor.get('iban', '')
    pdf.set_xy(table_x + 3, info_y + 6.5)
    pdf.set_font(pdf.sans_font, '', 9)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(89, 4.5, f"IBAN: {iban if iban else 'A consultar con el emisor'}", align='L')

    pdf.set_xy(table_x + 3, info_y + 11.5)
    pdf.set_font(pdf.sans_font, '', 7.5)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    pdf.cell(89, 3.5, f"Beneficiario: {emisor.get('nombre', 'Emisor')}", align='L')

    pdf.set_xy(table_x + 3, info_y + 15.5)
    pdf.set_font(pdf.sans_font, '', 7.5)
    display_concepto = numero_factura if str(numero_factura).lower().startswith('factura') else f"Factura {numero_factura}"
    pdf.cell(89, 3.5, f"Concepto: {display_concepto}", align='L')

    # Observaciones o notas (justificadas con última línea a la izquierda)
    observaciones = factura_data.get('observaciones', '')
    if observaciones:
        obs_x = table_x + 100
        obs_w = table_w - 100
        pdf.set_fill_color(248, 246, 243)
        pdf.rect(obs_x, info_y, obs_w, 24, style='FD')

        pdf.set_xy(obs_x + 3, info_y + 2)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(obs_w - 6, 3.5, 'OBSERVACIONES', align='L')

        pdf.set_xy(obs_x + 3, info_y + 6.5)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.multi_cell(obs_w - 6, 3.5, observaciones[:220], align='J')

    # Condiciones al pie de la factura (justificadas con última línea a la izquierda)
    cond_y = info_y + 26
    pdf.set_xy(table_x, cond_y)
    pdf.set_font(pdf.sans_font, '', 6.8)
    pdf.set_text_color(*COLOR_TEXT_MUTED)
    condiciones_default = emisor.get(
        'factura_condiciones'
    ) or emisor.get(
        'presupuesto_condiciones'
    ) or (
        "Factura emitida de acuerdo con la legislación vigente. El pago deberá realizarse dentro del plazo acordado mediante la modalidad indicada.\n"
        "Muchas gracias por su confianza en nuestros servicios profesionales."
    )
    for linea_c in [c.strip() for c in condiciones_default.split('\n') if c.strip()][:4]:
        pdf.set_x(table_x)
        pdf.multi_cell(table_w, 3.2, linea_c, align='J')
        pdf.ln(0.5)

    # Guardar archivo
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
