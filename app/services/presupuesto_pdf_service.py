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
    Genera el PDF editorial completo para un presupuesto con control de desbordamiento y textos configurables.
    """
    pdf = EditorialPresupuestoPDF()
    img_dir = str(STATIC_DIR / 'img' / 'presupuesto')
    portada_img = os.path.join(img_dir, 'portada_default.jpg')
    bienvenida_img = os.path.join(img_dir, 'bienvenida_default.jpg')

    instagram = config.get('presupuesto_instagram') or config.get('web') or DEFAULT_PRESUPUESTO_INSTAGRAM
    email = config.get('presupuesto_email') or config.get('email') or DEFAULT_PRESUPUESTO_EMAIL
    year = str(presupuesto.get('fecha', '2026'))[:4]
    cliente_nombre = presupuesto.get('cliente_nombre') or ''
    titulo = presupuesto.get('titulo') or 'Presupuesto de Servicios'
    subtitulo = presupuesto.get('subtitulo') or 'Propuesta de servicios y condiciones comerciales'
    opciones = presupuesto.get('opciones', [])

    # ══════════════════════════════════════════════════════════
    # PÁGINA 1: PORTADA (Fondo completo + textos superpuestos)
    # ══════════════════════════════════════════════════════════
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
    pdf.set_xy(21, 21)
    pdf.set_font(pdf.sans_font, '', 13)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(40, 8, year, align='L')

    # Título en la parte inferior derecha con personalización por cliente
    pdf.set_xy(108, 214)
    pdf.set_font(pdf.serif_font, '', 28)
    pdf.set_text_color(*COLOR_TEXT)

    if ' para ' in titulo:
        partes_titulo = titulo.split(' para ', 1)
        linea_1 = partes_titulo[0].strip()
        linea_2 = f"para {partes_titulo[1].strip()}"
    elif cliente_nombre and (not titulo or titulo in ['Presupuesto', 'Presupuesto de Servicios']):
        linea_1 = "Presupuesto"
        linea_2 = f"para {cliente_nombre}"
    elif ' de ' in titulo and cliente_nombre:
        linea_1 = "Presupuesto"
        linea_2 = f"para {cliente_nombre}"
    else:
        linea_1 = titulo
        linea_2 = None

    if linea_2:
        pdf.cell(85, 10, linea_1, align='L')
        pdf.set_xy(108, 226)
        font_size = 26 if len(linea_2) <= 20 else (22 if len(linea_2) <= 28 else 18)
        pdf.set_font(pdf.serif_font, 'I', font_size)
        pdf.cell(85, 10, linea_2, align='L')
    else:
        pdf.cell(85, 10, linea_1, align='L')

    # Redes / Web al pie si existen
    if instagram:
        pdf.set_xy(25, 270)
        pdf.set_font(pdf.sans_font, '', 10)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(160, 6, instagram, align='C')

    # ══════════════════════════════════════════════════════════
    # PÁGINA 2: BIENVENIDOS
    # ══════════════════════════════════════════════════════════
    pdf.add_page()
    if os.path.exists(bienvenida_img):
        try:
            from PIL import Image
            with Image.open(bienvenida_img) as img:
                b_ratio = img.size[0] / img.size[1]
        except Exception:
            b_ratio = 0.707

        if 0.65 <= b_ratio <= 0.75:
            # Fondo A4 completo diseñado
            pdf.image(bienvenida_img, x=0, y=0, w=210, h=297)
            top_text_y = 126
        else:
            img_w = 175
            img_h = 84
            img_x = (210 - img_w) / 2
            img_y = 15
            pdf.image(bienvenida_img, x=img_x, y=img_y, w=img_w, h=img_h)
            top_text_y = 108
    else:
        top_text_y = 108

    # Encabezado "Bienvenidos"
    pdf.set_xy(25, top_text_y)
    pdf.set_font(pdf.serif_font, '', 28)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(160, 10, config.get('presupuesto_bienvenida_titulo') or 'Bienvenidos', align='C')

    # Subtítulo en cursiva
    pdf.set_xy(25, top_text_y + 11)
    pdf.set_font(pdf.serif_font, 'I', 13)
    pdf.cell(160, 8, config.get('presupuesto_bienvenida_subtitulo') or 'Propuesta de servicios y condiciones comerciales', align='C')

    # Texto cuerpo
    texto_bienvenida = config.get('presupuesto_bienvenida_texto', '')
    if not texto_bienvenida:
        texto_bienvenida = DEFAULT_BIENVENIDA_TEXTO

    pdf.set_xy(25, top_text_y + 27)
    pdf.set_font(pdf.sans_font, '', 9.2)
    pdf.set_text_color(*COLOR_TEXT)
    for parrafo in texto_bienvenida.replace('\r\n', '\n').split('\n\n'):
        if not parrafo.strip():
            continue
        pdf.set_x(25)
        pdf.multi_cell(160, 5.0, parrafo.strip(), align='J')
        pdf.ln(4)

    # Pie página 2: Año a la izq, EMAIL a la der
    pdf.set_xy(25, 262)
    pdf.set_font(pdf.sans_font, '', 14)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(40, 6, year, align='L')

    if email:
        pdf.set_xy(110, 258)
        pdf.set_font(pdf.sans_font, '', 8)
        pdf.cell(76, 4, 'EMAIL', align='R')
        pdf.set_xy(110, 263)
        pdf.set_font(pdf.sans_font, '', 9.2)
        pdf.cell(76, 5, email, align='R')

    # ══════════════════════════════════════════════════════════
    # PÁGINAS 3..N: OPCIONES DE PRESUPUESTO CON CONTROL DE DESBORDAMIENTO
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
        pdf.set_xy(table_x, 24)
        pdf.set_font(pdf.serif_font, '', 28)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(100, 10, 'Presupuesto', align='L')

        pdf.set_xy(table_x, 35)
        pdf.set_font(pdf.serif_font, 'I', 13)
        pdf.multi_cell(100, 5.5, subtitulo, align='L')

        if op_name:
            pdf.set_xy(125, 28)
            pdf.set_font(pdf.sans_font, '', 9)
            pdf.cell(65, 6, op_name.upper(), align='R')

        table_y = 60
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

    # ══════════════════════════════════════════════════════════
    # PÁGINA FINAL: PROCESO / METODOLOGÍA DE TRABAJO
    # ══════════════════════════════════════════════════════════
    pdf.add_page()
    # Fondo general
    pdf.set_fill_color(*COLOR_CARD_BG)
    pdf.rect(0, 0, 210, 297, style='F')

    # Franja superior beige
    pdf.set_fill_color(*COLOR_BAND)
    pdf.rect(0, 0, 210, 60, style='F')

    # Título proceso / metodología
    pdf.set_xy(20, 18)
    pdf.set_font(pdf.serif_font, '', 28)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(170, 10, config.get('presupuesto_proceso_titulo') or 'Proceso de trabajo', align='C')

    pdf.set_xy(20, 31)
    pdf.set_font(pdf.serif_font, 'I', 13)
    pdf.cell(170, 7, config.get('presupuesto_proceso_subtitulo') or 'Fases del proyecto y tiempos de ejecución', align='C')

    # 4 Cuadrantes configurables
    fases_data = [
        {
            "titulo": config.get('proceso_fase1_titulo') or "Planificación y requerimientos",
            "puntos_str": config.get('proceso_fase1_puntos') or "• Definición del alcance\n• Elaboración de propuesta\n• Aprobación y confirmación\n• Calendario de trabajo",
            "rect": (20, 75, 80, 62),
            "color": COLOR_Q1
        },
        {
            "titulo": config.get('proceso_fase2_titulo') or "Desarrollo inicial",
            "puntos_str": config.get('proceso_fase2_puntos') or "• Ejecución de tareas iniciales\n• Presentación de avances\n• Selección de opciones\n• Primera revisión",
            "rect": (110, 75, 80, 62),
            "color": COLOR_Q2
        },
        {
            "titulo": config.get('proceso_fase3_titulo') or "Revisiones y ajustes",
            "puntos_str": config.get('proceso_fase3_puntos') or "• Aplicación de comentarios\n• Validación de especificaciones\n• Control de calidad\n• Aprobación final",
            "rect": (20, 144, 80, 62),
            "color": COLOR_Q3
        },
        {
            "titulo": config.get('proceso_fase4_titulo') or "Entrega y cierre",
            "puntos_str": config.get('proceso_fase4_puntos') or "• Puesta en marcha / Entrega final\n• Validación de conformidad\n• Soporte y garantía\n• Facturación final",
            "rect": (110, 144, 80, 62),
            "color": COLOR_Q4
        }
    ]

    for fase in fases_data:
        qx, qy, qw, qh = fase["rect"]
        pdf.set_fill_color(*fase["color"])
        pdf.rect(qx, qy, qw, qh, style='F')

        # Título del cuadrante en cursiva blanca
        pdf.set_xy(qx + 5, qy + 5)
        pdf.set_font(pdf.serif_font, 'I', 11)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.cell(qw - 10, 6, fase["titulo"], align='L')

        # Línea separadora blanca fina
        pdf.set_draw_color(*COLOR_WHITE)
        pdf.set_line_width(0.3)
        pdf.line(qx + 5, qy + 13, qx + qw - 5, qy + 13)

        # Viñetas
        py = qy + 16
        pdf.set_font(pdf.sans_font, '', 7.8)
        puntos = []
        for raw_line in fase["puntos_str"].split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('•') or line.startswith('-'):
                puntos.append(line.lstrip('•-').strip())
            else:
                if puntos:
                    puntos[-1] += ' ' + line
                else:
                    puntos.append(line)

        for p in puntos[:5]:
            pdf.set_xy(qx + 5, py)
            pdf.cell(3, 4, "•", align='L')
            pdf.set_xy(qx + 9, py)
            pdf.multi_cell(qw - 14, 3.8, p, align='L')
            py = pdf.get_y() + 0.8

    # Texto inferior de cierre
    pdf.set_xy(20, 218)
    pdf.set_font(pdf.serif_font, '', 20)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(170, 8, config.get('presupuesto_proceso_titulo') or 'Proceso de trabajo', align='L')

    cierre_texto = config.get(
        'presupuesto_proceso_cierre'
    ) or (
        "Nuestro compromiso se basa en ofrecer un servicio riguroso, adaptado a los más altos estándares de calidad y con una comunicación fluida durante todas las etapas de ejecución."
    )
    pdf.set_xy(20, 229)
    pdf.set_font(pdf.sans_font, '', 8.5)
    pdf.set_text_color(*COLOR_TEXT)
    for parrafo in cierre_texto.replace('\r\n', '\n').split('\n\n'):
        if not parrafo.strip():
            continue
        pdf.set_x(20)
        pdf.multi_cell(170, 4.4, parrafo.strip(), align='J')
        pdf.ln(3)

    # Pie página 5: Año y Redes / Web
    pdf.set_xy(20, 265)
    pdf.set_font(pdf.sans_font, '', 13)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(40, 6, year, align='L')

    if instagram:
        pdf.set_xy(110, 265)
        pdf.set_font(pdf.sans_font, '', 10)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(80, 6, instagram, align='R')

    pdf_bytes = bytes(pdf.output())
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
