import os
from fpdf import FPDF
from app.paths import STATIC_DIR

# ── PALETA EDITORIAL (BLANCO Y NEGRO NEUTRO POR DEFECTO) ──
COLOR_TEXT = (20, 20, 20)          # #141414 Black / deep neutral
COLOR_TEXT_MUTED = (90, 90, 90)    # #5a5a5a Neutral medium gray
COLOR_BORDER = (215, 215, 215)     # #d7d7d7 Neutral light gray border
COLOR_CARD_BG = (255, 255, 255)    # #ffffff Pure white
COLOR_WHITE = (255, 255, 255)
COLOR_BAND = (240, 240, 240)       # #f0f0f0 Neutral subtle gray band

# 4 Quadrants in grayscale / monochrome
COLOR_Q1 = (35, 35, 35)            # #232323 Deep charcoal
COLOR_Q2 = (70, 70, 70)            # #464646 Medium dark gray
COLOR_Q3 = (50, 50, 50)            # #323232 Charcoal
COLOR_Q4 = (100, 100, 100)         # #646464 Medium gray

DEFAULT_PRESUPUESTO_INSTAGRAM = os.getenv("DEFAULT_PRESUPUESTO_INSTAGRAM", "")
DEFAULT_PRESUPUESTO_EMAIL = os.getenv("DEFAULT_PRESUPUESTO_EMAIL", "")
DEFAULT_BIENVENIDA_TEXTO = os.getenv(
    "DEFAULT_BIENVENIDA_TEXTO",
    "Le agradecemos su interés en nuestros servicios profesionales. Presentamos a continuación nuestra propuesta detallada con el alcance de las partidas, especificaciones técnicas y condiciones económicas adaptadas a sus necesidades.\n\n"
    "Quedamos a su entera disposición para resolver cualquier duda o ajustar la propuesta según sus preferencias."
)


class EditorialPresupuestoPDF(FPDF):
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


def generar_pdf_presupuesto(presupuesto: dict, config: dict, output_path: str = None) -> bytes:
    """
    Genera el PDF del presupuesto (sin portada, sin página de bienvenida y sin página final de proceso).
    Contiene directamente las páginas con las opciones, partidas, subtotales, totales y condiciones.
    """
    pdf = EditorialPresupuestoPDF()

    cliente_nombre = presupuesto.get('cliente_nombre') or ''
    titulo = presupuesto.get('titulo') or 'Presupuesto de Servicios'
    subtitulo = presupuesto.get('subtitulo') or 'Propuesta de servicios y condiciones comerciales'
    opciones = presupuesto.get('opciones', [])
    if not opciones:
        opciones = [{'nombre_opcion': '', 'lineas': []}]

    # ══════════════════════════════════════════════════════════
    # PÁGINAS DE OPCIONES DE PRESUPUESTO CON CONTROL DE DESBORDAMIENTO
    # ══════════════════════════════════════════════════════════
    condiciones_texto = config.get('presupuesto_condiciones', '')
    card_x, card_y, card_w, card_h = 9.5, 8.5, 191, 280
    table_x = 19
    table_w = 172

    def draw_presupuesto_card_bg():
        pdf.add_page()
        pdf.set_fill_color(*COLOR_BORDER)
        pdf.rect(0, 0, 210, 297, style='F')
        pdf.set_fill_color(*COLOR_CARD_BG)
        pdf.rect(card_x, card_y, card_w, card_h, style='F')

    def render_op_first_header(op_name):
        pdf.set_xy(table_x, 20)
        pdf.set_font(pdf.serif_font, '', 26)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(100, 10, 'Presupuesto', align='L')

        pdf.set_xy(table_x, 31)
        pdf.set_font(pdf.serif_font, 'I', 11)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.multi_cell(100, 4.5, subtitulo, align='L')

        num_pres = presupuesto.get('numero_presupuesto') or ''
        fecha_pres = presupuesto.get('fecha') or ''
        fecha_str = str(fecha_pres)[:10] if fecha_pres else ''

        # Información del documento y cliente a la derecha
        y_meta = 20
        if num_pres:
            pdf.set_xy(110, y_meta)
            pdf.set_font(pdf.sans_font, 'B', 10)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(80, 4.5, f"Nº {num_pres}", align='R')
            y_meta += 5

        if fecha_str:
            pdf.set_xy(110, y_meta)
            pdf.set_font(pdf.sans_font, '', 8.5)
            pdf.set_text_color(*COLOR_TEXT_MUTED)
            pdf.cell(80, 4, f"Fecha: {fecha_str}", align='R')
            y_meta += 4.5

        if cliente_nombre:
            pdf.set_xy(110, y_meta)
            pdf.set_font(pdf.sans_font, '', 8.5)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(80, 4, f"Cliente: {cliente_nombre}", align='R')
            y_meta += 4.5

        if op_name:
            pdf.set_xy(110, y_meta)
            pdf.set_font(pdf.sans_font, 'B', 8.5)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(80, 4.5, op_name.upper(), align='R')

        table_y = 56
        pdf.set_xy(table_x, table_y + 2)
        pdf.set_font(pdf.sans_font, '', 8.0)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(108, 5.5, 'DESCRIPCIÓN', align='L')
        pdf.cell(24, 5.5, 'CANT.', align='C')
        pdf.cell(40, 5.5, 'TOTAL', align='R')

        # Línea entre encabezados y productos (0.75 pt ≈ 0.265 mm)
        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)
        pdf.line(table_x, table_y + 9.5, table_x + table_w, table_y + 9.5)

        return table_y + 11.5

    def render_op_continuation_header(op_name, page_num):
        pdf.set_xy(table_x, 18)
        pdf.set_font(pdf.serif_font, '', 20)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(100, 8, f'Presupuesto - {op_name} (cont.)', align='L')

        table_y = 30
        pdf.set_xy(table_x, table_y + 2)
        pdf.set_font(pdf.sans_font, '', 8.0)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(108, 5.5, 'DESCRIPCIÓN', align='L')
        pdf.cell(24, 5.5, 'CANT.', align='C')
        pdf.cell(40, 5.5, 'TOTAL', align='R')

        # Línea entre encabezados y productos (0.75 pt ≈ 0.265 mm)
        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)
        pdf.line(table_x, table_y + 9.5, table_x + table_w, table_y + 9.5)

        return table_y + 11.5

    for opcion in opciones:
        op_name = opcion.get('nombre_opcion', '')
        lineas = opcion.get('lineas', [])
        page_num = 1

        draw_presupuesto_card_bg()
        curr_y = render_op_first_header(op_name)

        MAX_Y_WITH_CONDITIONS = 180.0
        MAX_Y_TABLE_BOTTOM = 265.0

        pdf.set_draw_color(*COLOR_TEXT)
        pdf.set_line_width(0.265)

        for i, l in enumerate(lineas):
            mat = l.get('detalle_material', '')
            row_h = 10.5 if mat else 8.5
            is_last = (i == len(lineas) - 1)
            threshold = MAX_Y_WITH_CONDITIONS if is_last else MAX_Y_TABLE_BOTTOM

            if (curr_y + row_h) > threshold:
                draw_presupuesto_card_bg()
                page_num += 1
                curr_y = render_op_continuation_header(op_name, page_num)

            desc = l.get('descripcion', '')
            cant = l.get('cantidad', 1)
            total_l = l.get('total', 0.0)

            cant_str = f"{int(cant)}" if cant == int(cant) else f"{cant:.2f}"
            tot_str = f"{total_l:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

            pdf.set_xy(table_x, curr_y)
            pdf.set_font(pdf.sans_font, '', 8.5)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(108, 4.5, desc[:58], align='L')
            pdf.cell(24, 4.5, cant_str, align='C')
            pdf.cell(40, 4.5, tot_str, align='R')

            if mat:
                pdf.set_xy(table_x, curr_y + 4.2)
                pdf.set_font(pdf.sans_font, '', 7.5)
                pdf.set_text_color(*COLOR_TEXT_MUTED)
                pdf.cell(108, 4, mat[:65], align='L')

            curr_y += row_h
            pdf.set_draw_color(*COLOR_TEXT)
            pdf.set_line_width(0.265)
            pdf.line(table_x, curr_y, table_x + table_w, curr_y)
            curr_y += 1.5

        # TOTAL box
        total_opcion = opcion.get('total', 0.0)
        desc_importe_op = float(opcion.get('descuento_importe_total', 0.0) or 0.0)
        desc_vis_op = bool(opcion.get('descuento_visible', 1))
        desc_nom_op = opcion.get('descuento_nombre') or ''

        if desc_importe_op > 0 and desc_vis_op:
            sub_bruto_op = total_opcion + desc_importe_op
            sub_bruto_str = f"{sub_bruto_op:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
            desc_str = f"-{desc_importe_op:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

            pdf.set_xy(table_x, curr_y + 1)
            pdf.set_font(pdf.sans_font, '', 8)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(108, 3.5, 'Subtotal:', align='L')
            pdf.set_xy(table_x + 112, curr_y + 1)
            pdf.cell(60, 3.5, sub_bruto_str, align='R')

            pdf.set_xy(table_x, curr_y + 5)
            pdf.set_text_color(*COLOR_TEXT)
            lbl_dto_op = f"Descuento ({desc_nom_op[:20]}):" if desc_nom_op else "Descuento:"
            pdf.cell(108, 3.5, lbl_dto_op, align='L')
            pdf.set_xy(table_x + 112, curr_y + 5)
            pdf.cell(60, 3.5, desc_str, align='R')
            curr_y += 7.5

        tot_opcion_str = f"{total_opcion:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

        pdf.set_xy(table_x, curr_y + 2)
        pdf.set_font(pdf.sans_font, 'B', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(108, 4, 'TOTAL', align='L')
        pdf.set_xy(table_x, curr_y + 6)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*COLOR_TEXT_MUTED)
        pdf.cell(108, 4, 'Precio sin iva', align='L')

        pdf.set_xy(table_x + 112, curr_y + 3)
        pdf.set_font(pdf.sans_font, 'B', 10)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(60, 6, tot_opcion_str, align='R')

        curr_y += 13

        # ── BLOQUE DE CONDICIONES AL PIE ──
        # Anclamos las condiciones a la parte inferior de la tarjeta (y=221) para eliminar el gran espacio vacío inferior
        if curr_y > 215:
            draw_presupuesto_card_bg()
            pdf.set_xy(20, 20)
            pdf.set_font(pdf.serif_font, '', 16)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(100, 6, f'Condiciones - {op_name}', align='L')
            cond_y = 35
        else:
            cond_y = max(curr_y + 6, 221)

        pdf.set_xy(table_x, cond_y)
        pdf.set_font(pdf.sans_font, '', 6.8)
        pdf.set_text_color(*COLOR_TEXT)

        condiciones_a_mostrar = condiciones_texto or (
            "• Validez de la oferta: Este presupuesto tiene una validez de 30 días naturales a partir de su fecha de emisión.\n"
            "• Forma de pago: 50% a la aceptación del presupuesto y 50% a la finalización y entrega del trabajo, salvo pacto en contrario.\n"
            "• Plazos de entrega: Los plazos acordados comenzarán a contar a partir de la recepción de toda la información y material necesario.\n"
            "• Modificaciones: Cualquier modificación o ampliación sobre el alcance inicial será presupuestada por separado.\n"
            "• Impuestos: Los precios indicados no incluyen IVA salvo que se indique expresamente lo contrario."
        )
        lineas_cond = [c.strip() for c in condiciones_a_mostrar.split('\n') if c.strip()]
        for item in lineas_cond:
            if pdf.get_y() > 275:
                break
            pdf.set_x(table_x)
            pdf.multi_cell(table_w, 3.4, item, align='L')
            pdf.ln(0.8)

    pdf_bytes = bytes(pdf.output())
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
