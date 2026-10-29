"""
SIF PyME — Generador Oficial del Manual de Usuario en PDF (docs/MANUAL_DE_USUARIO.pdf).
Crea un documento PDF editorial completo, profesional y de alta resolución
con capturas reales de pantalla de cada sección y guías paso a paso para el usuario.
"""

import sys
import os
import argparse
import unicodedata
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.paths import STATIC_DIR

ASSETS_DIR = PROJECT_ROOT / "docs" / "assets" / "manual"
OUTPUT_PDF = PROJECT_ROOT / "docs" / "MANUAL_DE_USUARIO.pdf"

# Colores de la paleta editorial SIF PyME
C_PRIMARY = (15, 23, 42)       # #0F172A Dark Slate Navy
C_ACCENT = (2, 132, 199)       # #0284C7 Sky Blue
C_TEXT = (30, 41, 59)          # #1E293B Charcoal text
C_MUTED = (100, 116, 139)      # #64748B Secondary text
C_BG_CARD = (248, 250, 252)    # #F8FAFC Subtle background
C_BORDER = (226, 232, 240)     # #E2E8F0 Border divider
C_WHITE = (255, 255, 255)

# Colores de Callout Boxes
C_TIP_BG = (240, 249, 255)     # #F0F9FF Sky blue
C_TIP_BORDER = (2, 132, 199)   # #0284C7 Sky blue
C_FISCAL_BG = (255, 251, 235)  # #FFFBEB Amber
C_FISCAL_BORDER = (217, 119, 6) # #D97706 Amber
C_WARN_BG = (255, 241, 242)    # #FFF1F2 Rose
C_WARN_BORDER = (225, 29, 72)  # #E11D48 Rose


class ManualPDF(FPDF):
    """Clase editorial para el Manual de Usuario de SIF PyME."""

    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=False)
        self.set_margins(16, 16, 16)
        self._setup_fonts()
        self.current_chapter = ""
        self.total_pages_count = 12

        # Metadatos del documento PDF
        self.set_title("SIF PyME - Manual de Usuario")
        self.set_author("SIF PyME")
        self.set_subject("Manual de Usuario Oficial y Guia de Operaciones v1.0.0")
        self.set_creator("SIF PyME Documentation Engine")
        self.set_keywords("SIF PyME, facturacion, presupuestos, manual, pyme, autonomos, macOS")

    def _setup_fonts(self):
        fonts_dir = STATIC_DIR / 'fonts'
        georgia = fonts_dir / 'georgia.ttf'
        georgiab = fonts_dir / 'georgiab.ttf'
        georgiai = fonts_dir / 'georgiai.ttf'
        georgiaz = fonts_dir / 'georgiaz.ttf'
        inter = fonts_dir / 'Inter-Regular.ttf'

        if georgia.exists():
            self.add_font('Georgia', '', str(georgia))
            self.add_font('Georgia', 'B', str(georgiab) if georgiab.exists() else str(georgia))
            self.add_font('Georgia', 'I', str(georgiai) if georgiai.exists() else str(georgia))
            self.add_font('Georgia', 'BI', str(georgiaz) if georgiaz.exists() else (str(georgiab) if georgiab.exists() else str(georgia)))
            self.serif_font = 'Georgia'
        else:
            self.serif_font = 'Times'

        if inter.exists():
            self.add_font('Inter', '', str(inter))
            self.add_font('Inter', 'B', str(inter))
            self.add_font('Inter', 'I', str(inter))
            self.add_font('Inter', 'BI', str(inter))
            self.sans_font = 'Inter'
        else:
            self.sans_font = 'Helvetica'

    def header(self):
        # No mostrar encabezado en la portada (página 1)
        if self.page_no() == 1:
            return

        self.set_xy(16, 8)
        self.set_font(self.sans_font, '', 7.5)
        self.set_text_color(*C_MUTED)
        self.cell(70, 5, "SIF PyME  ·  MANUAL DE USUARIO", align='L')

        if self.current_chapter:
            self.set_font(self.sans_font, '', 7.5)
            self.set_text_color(*C_ACCENT)
            self.cell(108, 5, self.current_chapter.upper(), align='R')

        # Línea divisoria superior sutil
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(16, 14, 194, 14)

    def footer(self):
        # No mostrar pie en la portada (página 1)
        if self.page_no() == 1:
            return

        # Línea divisoria inferior
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(16, 283, 194, 283)

        self.set_xy(16, 285)
        self.set_font(self.sans_font, '', 7.5)
        self.set_text_color(*C_MUTED)
        self.cell(120, 5, "SIF PyME v1.0.0 — Sistema Local de Facturación y Presupuestos (macOS / Windows / Linux)", align='L')

        self.set_font(self.sans_font, '', 7.5)
        self.set_text_color(*C_PRIMARY)
        page_str = f"Página {self.page_no()} de {self.total_pages_count}"
        self.cell(58, 5, page_str, align='R')

    # ────────────────────────────────────────────────────────────
    # COMPONENTES DE MAQUETACIÓN
    # ────────────────────────────────────────────────────────────

    def add_chapter_page(self, badge_num: str, title: str, subtitle: str = ""):
        """Añade una nueva página y establece el capítulo ANTES de invocar el encabezado."""
        self.current_chapter = title
        self.add_page()
        # Registrar marcador en el panel de navegación de esquemas PDF (Outlines)
        outline_title = f"{badge_num}: {title}".replace("—", "-").replace("·", "-")
        safe_outline = unicodedata.normalize('NFKD', outline_title).encode('ascii', 'ignore').decode('ascii').strip()
        self.start_section(safe_outline, level=0)
        self.draw_chapter_title(badge_num, title, subtitle)

    def draw_chapter_title(self, badge_num: str, title: str, subtitle: str = ""):
        self.current_chapter = title
        y = self.get_y()
        if y < 18:
            self.set_y(18)
            y = 18

        # Badge número
        self.set_fill_color(*C_ACCENT)
        self.set_text_color(*C_WHITE)
        self.set_font(self.sans_font, '', 7.5)
        badge_w = self.get_string_width(badge_num) + 8
        self.rect(16, y, badge_w, 4.8, style='F')
        self.set_xy(16, y)
        self.cell(badge_w, 4.8, badge_num, align='C')

        # Título principal
        self.set_xy(16 + badge_w + 4, y - 0.5)
        self.set_font(self.serif_font, 'B', 14)
        self.set_text_color(*C_PRIMARY)
        self.cell(178 - badge_w - 4, 6, title, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Subtítulo descriptivo
        if subtitle:
            self.set_x(16)
            self.set_font(self.sans_font, '', 8.5)
            self.set_text_color(*C_MUTED)
            self.cell(178, 4.5, subtitle, align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(2.5)

    def draw_section_subtitle(self, title: str):
        self.set_font(self.serif_font, 'B', 10.5)
        self.set_text_color(*C_PRIMARY)
        self.cell(178, 5.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def draw_paragraph(self, text: str, font_size: float = 8.5, line_h: float = 4.2):
        self.set_font(self.sans_font, '', font_size)
        self.set_text_color(*C_TEXT)
        self.multi_cell(178, line_h, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def draw_bullet(self, title: str, desc: str, bullet_char: str = "•"):
        self.set_left_margin(21)
        self.set_x(16)
        # Si el título ya contiene numeración propia (ej. "1. Selección..."), formatear como paso numerado
        if bullet_char and not (title and title[0].isdigit()):
            self.set_font(self.sans_font, '', 8.5)
            self.set_text_color(*C_ACCENT)
            self.cell(5, 4.2, bullet_char, align='L')
        elif title and title[0].isdigit():
            parts = title.split(' ', 1)
            num_part = parts[0]
            rest_part = parts[1] if len(parts) > 1 else ""
            self.set_font(self.sans_font, 'B', 8.5)
            self.set_text_color(*C_ACCENT)
            self.cell(5, 4.2, num_part, align='L')
            title = rest_part
        else:
            self.set_x(21)

        self.set_text_color(*C_PRIMARY)
        self.set_font(self.sans_font, 'B', 8.5)
        self.write(4.2, title + " ")
        self.set_text_color(*C_TEXT)
        self.set_font(self.sans_font, '', 8.5)
        self.write(4.2, desc)
        self.ln(5.2)
        self.set_left_margin(16)

    def draw_image_figure(self, img_path: Path, caption: str, h_mm: float = 78, w_mm: float = 178):
        y = self.get_y()
        # Caja contenedora con borde sutil
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.rect(16, y, w_mm, h_mm, style='FD')

        # Dibujar imagen real
        if img_path.exists():
            self.image(str(img_path), x=16.3, y=y + 0.3, w=w_mm - 0.6, h=h_mm - 0.6)
        else:
            self.set_xy(16, y + h_mm / 2 - 4)
            self.set_font(self.sans_font, '', 9)
            self.set_text_color(*C_MUTED)
            self.cell(w_mm, 8, f"[Imagen pendiente: {img_path.name}]", align='C')

        # Pie de foto explicativo
        self.set_xy(16, y + h_mm + 1.5)
        self.set_font(self.sans_font, '', 7.5)
        self.set_text_color(*C_MUTED)
        self.multi_cell(w_mm, 3.8, f"Figura: {caption}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def draw_two_images(self, img1: Path, cap1: str, img2: Path, cap2: str, h_mm: float = 52):
        y = self.get_y()
        w = 87
        gap = 4

        # Imagen 1
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.25)
        self.rect(16, y, w, h_mm, style='FD')
        if img1.exists():
            self.image(str(img1), x=16.2, y=y + 0.2, w=w - 0.4, h=h_mm - 0.4)

        # Imagen 2
        self.rect(16 + w + gap, y, w, h_mm, style='FD')
        if img2.exists():
            self.image(str(img2), x=16 + w + gap + 0.2, y=y + 0.2, w=w - 0.4, h=h_mm - 0.4)

        # Pies de foto
        self.set_xy(16, y + h_mm + 1.2)
        self.set_font(self.sans_font, '', 7)
        self.set_text_color(*C_MUTED)
        self.cell(w, 3.5, cap1, align='C')

        self.set_xy(16 + w + gap, y + h_mm + 1.2)
        self.cell(w, 3.5, cap2, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2.5)

    def draw_callout_box(self, title: str, text: str, kind: str = "tip"):
        if kind == "fiscal":
            bg = C_FISCAL_BG
            border = C_FISCAL_BORDER
            tag = "CONSEJO FISCAL & NORMATIVA"
        elif kind == "warning":
            bg = C_WARN_BG
            border = C_WARN_BORDER
            tag = "SEGURIDAD & ADVERTENCIA"
        else:
            bg = C_TIP_BG
            border = C_TIP_BORDER
            tag = "CONSEJO PRÁCTICO"

        y = self.get_y()
        # Pre-calcular altura del texto
        self.set_font(self.sans_font, '', 8)
        lines = len(self.multi_cell(168, 3.8, text, dry_run=True, output="LINES"))
        box_h = max(18.0, 9.0 + (lines * 3.8))

        # Fondo
        self.set_fill_color(*bg)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.rect(16, y, 178, box_h, style='FD')

        # Franja lateral de acento
        self.set_fill_color(*border)
        self.rect(16, y, 2.5, box_h, style='F')

        # Título de caja
        self.set_xy(21, y + 2.5)
        self.set_font(self.sans_font, '', 7.5)
        self.set_text_color(*border)
        self.cell(168, 4, f"[{tag}]  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Texto
        self.set_x(21)
        self.set_font(self.sans_font, '', 8)
        self.set_text_color(*C_TEXT)
        self.multi_cell(168, 3.8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_y(y + box_h + 2.5)

    def draw_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]):
        y = self.get_y()
        total_w = sum(col_widths)

        # Cabecera
        self.set_fill_color(*C_PRIMARY)
        self.set_text_color(*C_WHITE)
        self.set_font(self.sans_font, '', 7.5)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 5.5, h, border=0, align='L', fill=True)
        self.ln(5.5)

        # Filas
        self.set_font(self.sans_font, '', 7.5)
        for row_idx, row in enumerate(rows):
            bg = C_BG_CARD if row_idx % 2 == 1 else C_WHITE
            self.set_fill_color(*bg)
            self.set_text_color(*C_TEXT)
            self.set_draw_color(*C_BORDER)
            self.set_line_width(0.15)

            # Altura fija o dinámica de celda
            for i, val in enumerate(row):
                # Primera columna en negrita suave
                if i == 0:
                    self.set_text_color(*C_PRIMARY)
                else:
                    self.set_text_color(*C_TEXT)
                self.cell(col_widths[i], 5, val, border='B', align='L', fill=True)
            self.ln(5)

        self.ln(2)


def build_manual_pdf(output_path: Path = OUTPUT_PDF) -> Path:
    """Construye y maqueta el manual de usuario completo de 11 páginas."""
    pdf = ManualPDF()

    # ══════════════════════════════════════════════════════════
    # PÁGINA 1: PORTADA EDITORIAL PROFESIONAL
    # ══════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.start_section("Portada: SIF PyME - Manual de Usuario", level=0)

    # Hero Banner Superior Oscuro
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 105, style='F')

    # Acento Azul en el borde inferior del hero
    pdf.set_fill_color(*C_ACCENT)
    pdf.rect(0, 103, 210, 2, style='F')

    # Logotipo / Identidad visual oficial de la aplicación (Requirement R1.1)
    logo_path = ASSETS_DIR / "app_logo.png"
    if not logo_path.exists():
        ico_src = PROJECT_ROOT / "app" / "static" / "icon.ico"
        if ico_src.exists():
            from PIL import Image
            with Image.open(ico_src) as im:
                im.save(logo_path)

    if logo_path.exists():
        pdf.set_fill_color(30, 41, 59)
        pdf.set_draw_color(51, 65, 85)
        pdf.set_line_width(0.25)
        pdf.rect(162, 20, 32, 32, style='FD')
        pdf.image(str(logo_path), x=164, y=22, w=28, h=28)

    # Etiqueta de Versión Superior
    pdf.set_xy(16, 20)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_draw_color(51, 65, 85)
    pdf.rect(16, 20, 62, 6.5, style='FD')
    pdf.set_xy(16, 20)
    pdf.set_font(pdf.sans_font, '', 8)
    pdf.set_text_color(224, 242, 254)
    pdf.cell(62, 6.5, "VERSIÓN OFICIAL 1.0.0 · 2026", align='C')

    # Título Principal en el Hero (Requirement R1.1)
    pdf.set_xy(16, 32)
    pdf.set_font(pdf.serif_font, 'B', 24)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(142, 11, "SIF PyME — Manual de Usuario", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(16)
    pdf.set_font(pdf.serif_font, '', 14)
    pdf.set_text_color(186, 230, 253) # Celeste suave
    pdf.cell(142, 8, "Sistema Local de Facturación & Presupuestos", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)
    pdf.set_x(16)
    pdf.set_font(pdf.sans_font, '', 9)
    pdf.set_text_color(203, 213, 225)
    pdf.multi_cell(142, 4.8, "Manual de usuario integral, guía operativa paso a paso y documentación técnica de arquitectura local independiente para pequeñas empresas, autónomos y estudios creativos.")

    # Cuerpo de la Portada
    pdf.set_y(120)
    pdf.set_font(pdf.serif_font, 'B', 15)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(178, 7, "MANUAL DE USUARIO Y OPERACIONES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font(pdf.sans_font, '', 9.5)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(178, 5, "Guía completa para la gestión comercial, presupuestación y emisión legal de facturas", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Grid de 4 Pilares de la Aplicación
    pdf.set_y(140)
    card_w = 86
    card_h = 36
    gap = 6

    pillars = [
        ("100% Local y Privado", "Tus datos financieros residen exclusivamente en tu propio disco duro. Sin telemetría, sin suscripciones forzosas y con base de datos SQLite transaccional.", 16, 140),
        ("Estándar macOS HIG", "Interfaz limpia inspirada en las guías de diseño de Apple: ventanas unificadas, inspector lateral NSTableView y modales en hoja (Sheets).", 16 + card_w + gap, 140),
        ("Presupuestos con Opciones", "Propuestas comerciales multipágina con alternativas comparables A/B/C, tramos por volumen y conversión a factura legal en 1 clic.", 16, 140 + card_h + gap),
        ("Auditoría Time Machine", "Historial inmutable de versiones para cada documento y papelera de reciclaje lógica para recuperación garantizada de información.", 16 + card_w + gap, 140 + card_h + gap)
    ]

    for title, desc, cx, cy in pillars:
        pdf.set_fill_color(*C_BG_CARD)
        pdf.set_draw_color(*C_BORDER)
        pdf.set_line_width(0.2)
        pdf.rect(cx, cy, card_w, card_h, style='FD')

        # Borde de acento izquierdo
        pdf.set_fill_color(*C_ACCENT)
        pdf.rect(cx, cy, 2, card_h, style='F')

        pdf.set_xy(cx + 6, cy + 3.5)
        pdf.set_font(pdf.serif_font, 'B', 9.5)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(card_w - 10, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_x(cx + 6)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*C_TEXT)
        pdf.multi_cell(card_w - 10, 3.6, desc)

    # Tarjeta de Metadatos y Fecha al pie
    pdf.set_y(232)
    pdf.set_fill_color(*C_WHITE)
    pdf.set_draw_color(*C_BORDER)
    pdf.rect(16, 232, 178, 38, style='FD')

    pdf.set_xy(22, 236)
    pdf.set_font(pdf.serif_font, 'B', 9)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(166, 4.5, "FICHA TÉCNICA DEL MANUAL", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    meta_items = [
        ("Aplicación:", "SIF PyME — Software de Facturación para PyME"),
        ("Versión Documentada:", "1.0.0 Oficial (Compilación de Producción)"),
        ("Plataformas Soportadas:", "macOS (Apple Silicon / Intel), Windows 10/11 y Linux"),
        ("Marco Normativo:", "Cumplimiento del Real Decreto 1619/2012 de Facturación"),
        ("Fecha de Edición:", "Octubre de 2026 · Documentación Oficial")
    ]
    for lbl, val in meta_items:
        pdf.set_x(22)
        pdf.set_font(pdf.sans_font, '', 8)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(42, 4.2, lbl)
        pdf.set_font(pdf.sans_font, '', 8)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(124, 4.2, val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ══════════════════════════════════════════════════════════
    # PÁGINA 2: ÍNDICE GENERAL & FILOSOFÍA DEL SISTEMA
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 01", "Índice de Contenidos & Filosofía del Sistema", "Estructura del manual y principios fundamentales de diseño y seguridad")

    # Tabla de Contenidos Paginada
    pdf.set_fill_color(*C_BG_CARD)
    pdf.set_draw_color(*C_BORDER)
    pdf.rect(16, 30, 178, 70, style='FD')

    pdf.set_xy(22, 33)
    pdf.set_font(pdf.serif_font, 'B', 10)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(166, 5, "TABLA DE CONTENIDOS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    toc_items = [
        ("Capítulo 01 · Filosofía del Sistema & Estructura Operativa", "2"),
        ("Capítulo 02 · Módulo de Facturación (I) — Navegación e Inspector", "3"),
        ("Capítulo 03 · Módulo de Facturación (II) — Emisión, IVA y Portada Opcional", "4"),
        ("Capítulo 04 · Módulo de Presupuestos — Opciones Comparables", "5"),
        ("Capítulo 05 · Catálogo de Productos — Escalados y Variantes", "6"),
        ("Capítulo 06 · Módulo de Descuentos Comerciales — Promociones y Visibilidad", "7"),
        ("Capítulo 07 · Módulo de Clientes — Directorio y Validación Fiscal", "8"),
        ("Capítulo 08 · Módulo de Seguridad — Versiones y Papelera", "9"),
        ("Capítulo 09 · Configuración, Onboarding y Respaldos", "10"),
        ("Capítulo 10 · Guía de Atajos de Teclado y Controles Globales", "11"),
        ("Capítulo 11 · Preguntas Frecuentes & Ficha Técnica", "12"),
    ]

    for title, page_str in toc_items:
        pdf.set_x(22)
        pdf.set_font(pdf.sans_font, '', 7.8)
        pdf.set_text_color(*C_TEXT)
        pdf.cell(144, 4.6, title)

        # Puntos suspensivos y número de página
        pdf.set_font(pdf.sans_font, '', 7.8)
        pdf.set_text_color(*C_ACCENT)
        pdf.cell(18, 4.6, f"Pág. {page_str}", align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Sección de Filosofía
    pdf.set_y(106)
    pdf.draw_section_subtitle("Filosofía y Principios de Arquitectura")
    pdf.draw_paragraph("SIF PyME ha sido concebido para profesionales, pequeñas empresas y autónomos que buscan un control absoluto y soberano sobre sus datos de facturación sin depender de conexiones remotas, servicios de suscripción en la nube ni transferir información sensible a servidores de terceros.")

    pdf.draw_bullet("Privacidad y Soberanía Total de Datos:", "La aplicación funciona de manera 100% local. Todos los registros contables, historiales y fichas de clientes se almacenan en un archivo SQLite local con modo WAL (Write-Ahead Logging), garantizando integridad y rendimiento óptimo.")
    pdf.draw_bullet("Diseño Nativo macOS Human Interface Guidelines:", "La interfaz respeta los patrones de usabilidad de los sistemas de escritorio modernos: barras de herramientas unificadas, paneles laterales de inspección rápida (NSInspector), cuadros modales nativos en hoja (Sheets) y controles de selector integrados.")
    pdf.draw_bullet("Almacenamiento Estructurado y Predecible:", "Los documentos emitidos en formato PDF oficial se organizan automáticamente en carpetas físicas por Año y Mes en la ruta elegida por el usuario, permitiendo auditorías sencillas y sincronización transparente con iCloud Drive o OneDrive.")

    pdf.draw_callout_box(
        "Almacenamiento Sincronizado en la Nube",
        "Aunque SIF PyME opera de forma 100% local, puedes seleccionar como carpeta de almacenamiento de facturas tu unidad de iCloud Drive o OneDrive en los Ajustes del Sistema. De este modo, tendrás tus PDFs oficiales sincronizados automáticamente en todos tus dispositivos móviles sin arriesgar la privacidad de la base de datos.",
        kind="tip"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 3: MÓDULO DE FACTURACIÓN (I) — NAVEGACIÓN E INSPECTOR
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 02", "Módulo de Facturación (I) — Navegación e Inspector", "Visualización de tabla, filtros temporales, búsqueda y panel de detalle")

    # Captura principal de facturas
    pdf.draw_image_figure(
        ASSETS_DIR / "01_facturas_principal.png",
        "Pantalla principal de Facturación: barra de filtros temporales, tabla de facturas e Inspector Lateral activo a la derecha.",
        h_mm=76
    )

    pdf.draw_section_subtitle("Controles de la Interfaz y Flujo Operativo")
    pdf.draw_paragraph("La pantalla de Facturación proporciona una vista panorámica de todas las facturas emitidas, borradores y documentos cobrados del ejercicio fiscal:")

    pdf.draw_bullet("Barra Lateral (Sidebar):", "Permite la navegación instantánea entre los módulos de la aplicación. Muestra contadores dinámicos actualizados en vivo con el número total de facturas activas, presupuestos, clientes registrados y documentos en papelera.")
    pdf.draw_bullet("Filtro de Estado:", "Filtra el listado según la situación del cobro: Emitida (pendiente de cobro), Pagada (ingreso confirmado), Vencida (plazo de pago expirado), Borrador o Anulada.")
    pdf.draw_bullet("Filtro por Ejercicio y Periodo:", "Selector del año fiscal y desglose por periodos: Año Completo, trimestres fiscales (1T, 2T, 3T, 4T) o meses específicos (Enero a Diciembre).")
    pdf.draw_bullet("Buscador Reactivo:", "Búsqueda instantánea con filtrado en tiempo real sin recargar página: busca por número de factura (FAC-...), razón social del cliente, NIF/CIF, email o teléfono.")
    pdf.draw_bullet("Inspector Lateral (NSInspector):", "Al hacer clic sobre cualquier fila de la tabla, el panel lateral derecho muestra la información completa del documento (cliente, fecha, estado e importes) y ofrece acceso directo a las acciones principales.")

    # Tabla de Botones del Inspector
    pdf.draw_table(
        ["Botón / Control", "Ubicación", "Función Realizada"],
        [
            ["Vista Previa PDF", "Inspector lateral", "Abre en el visor nativo el PDF oficial generado de la factura."],
            ["Editar Factura", "Inspector lateral", "Abre el formulario para modificar líneas o datos (crea nueva versión)."],
            ["Historial Versiones…", "Inspector lateral", "Abre el modal de auditoría Time Machine con todas las revisiones."],
            ["Eliminar Factura…", "Inspector lateral", "Envía la factura a la Papelera de Reciclaje (borrado lógico seguro)."],
        ],
        [40, 36, 102]
    )

    pdf.draw_callout_box(
        "Liquidación Trimestral del IVA (Modelo 303)",
        "Para preparar la declaración trimestral de Hacienda, selecciona el Año en curso y el Periodo correspondiente (ej. 3T). La barra inferior calculará automáticamente la Base Imponible total y el total facturado del trimestre, facilitando el traslado exacto a las casillas del Modelo 303 de la AEAT.",
        kind="fiscal"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 4: MÓDULO DE FACTURACIÓN (II) — EMISIÓN, IVA Y PORTADA
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 03", "Módulo de Facturación (II) — Emisión, IVA y Portada", "Formulario de alta, líneas, régimen de IVA, portada opcional y anticipos")

    pdf.draw_image_figure(
        ASSETS_DIR / "02_nueva_factura.png",
        "Formulario de emisión de factura: autocompletado de cliente, líneas con tramos por volumen y panel de resumen económico.",
        h_mm=74
    )

    pdf.draw_section_subtitle("Guía Paso a Paso para Emitir una Factura")
    pdf.draw_paragraph("Para crear una nueva factura oficial, pulsa el botón «+ Nueva Factura» en la barra superior o utiliza el atajo Cmd+N / Ctrl+N:")

    pdf.draw_bullet("1. Selección del Cliente:", "Escribe en el campo destinatario para autocompletar desde el directorio. Puedes pulsar «Nuevo Cliente…» para darlo de alta al instante sin perder la factura.")
    pdf.draw_bullet("2. Régimen de IVA y Fechas:", "Establece la fecha legal y activa la casilla «Sin IVA» si es una operación exenta; la serie y numeración conmutarán automáticamente a la serie exenta independiente.")
    pdf.draw_bullet("3. Líneas de Concepto y Anticipos:", "Añade conceptos del catálogo o libres. Admite partidas negativas (anticipos o entregas a cuenta) deduciendo proporcionalmente la base imponible y cuota de IVA.")
    pdf.draw_bullet("4. Partidas Exentas al 0% de IVA:", "En facturas con IVA ordinario, puedes incluir líneas específicas al 0% (suplidos o servicios formativos) sin que el sistema fuerce su recargo al 21%.")
    pdf.draw_bullet("5. Portada Editorial Opcional:", "Por defecto las facturas se emiten en formato legal directo de 1 página. En Ajustes puedes habilitar portada gráfica para proyectos de diseño o arquitectura.")
    pdf.draw_bullet("6. Emisión Oficial y Guardado:", "Pulsa «Emitir Factura y Descargar PDF». El sistema asignará el correlativo continuo único, generará el PDF y creará un snapshot automático de seguridad.")

    pdf.draw_callout_box(
        "Requisitos Legales de la Factura Completa (RD 1619/2012)",
        "Para que una factura sea deducible y plenamente válida ante la Agencia Tributaria, debe incluir obligatoriamente: número de serie correlativo, fecha de expedición, NIF/CIF y razón social tanto del emisor como del receptor, descripción de las operaciones, tipo impositivo aplicado y fecha de operación si difiere de la de expedición. SIF PyME valida estos campos antes de permitir la emisión.",
        kind="fiscal"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 5: MÓDULO DE PRESUPUESTOS — OPCIONES COMPARABLES
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 04", "Módulo de Presupuestos — Opciones Comparables", "Propuestas comerciales multipágina, opciones A/B/C y facturación en 1 clic")

    pdf.draw_two_images(
        ASSETS_DIR / "03_presupuestos_principal.png",
        "Listado con estados, rangos de precio y acción Facturar.",
        ASSETS_DIR / "04_nuevo_presupuesto.png",
        "Editor de propuesta con pestañas por opción A/B y líneas.",
        h_mm=54
    )

    pdf.draw_section_subtitle("Estructura de Presupuestos con Múltiples Opciones")
    pdf.draw_paragraph("SIF PyME incluye un motor editorial único para elaborar dossiers de presupuestos profesionales con alternativas comparables (por ejemplo, «Opción A · Acabado Artesanal Premium» frente a «Opción B · Acabado Estándar Elegante»):")

    pdf.draw_bullet("Ciclo de Vida del Presupuesto:", "Los presupuestos transitan por cinco estados controlados: Borrador (en elaboración), Enviado (remitido al cliente), Aceptado (oferta aprobada), Rechazado o Facturado.")
    pdf.draw_bullet("Pestañas de Opciones Comparables:", "Cada presupuesto puede contener múltiples opciones con sus propias líneas y totales independientes. El cliente recibe un único documento PDF con ambas cotizaciones claramente estructuradas.")
    pdf.draw_bullet("Botón «Duplicar Opción»:", "Permite clonar íntegramente la opción activa para crear una variante rápida (por ejemplo, cambiando únicamente la calidad del papel o el tipo de sobre) sin tener que reescribir las líneas.")
    pdf.draw_bullet("Rangos de Precios Automáticos:", "En el listado general, los presupuestos con múltiples opciones muestran el rango económico mínimo y máximo (ej. «256,52 € — 405,35 €») para una visualización comercial inmediata.")

    pdf.draw_section_subtitle("Facturación Directa en 1 Clic y Trazabilidad")
    pdf.draw_paragraph("Cuando el cliente aprueba la propuesta, no es necesario volver a teclear los conceptos en el módulo de facturación:")
    pdf.draw_bullet("Conversión Directa («Facturar…»):", "Al pulsar «Facturar…» en el menú de acciones del presupuesto, el sistema solicita qué opción aprobó el cliente y genera automáticamente una factura oficial con su correlativo legal, asociando ambos documentos.")
    pdf.draw_bullet("Reapertura Segura:", "Si el cliente solicita un cambio de opción tras haber facturado, la acción «Reabrir y volver a Borrador» traslada la factura previa a la papelera y permite facturar la nueva opción con total transparencia contable.")

    # Tabla de Botones y Acciones de Presupuestos
    pdf.draw_table(
        ["Botón / Control", "Ubicación", "Función Realizada"],
        [
            ["+ Nuevo Presupuesto", "Toolbar superior", "Abre el formulario para redactar un presupuesto multipágina con opciones."],
            ["PDF", "Fila / Acciones", "Genera y abre el dossier PDF oficial para presentar la propuesta al cliente."],
            ["Editar", "Fila de tabla", "Modifica datos del proyecto, opciones A/B/C y partidas presupuestadas."],
            ["Facturar…", "Menú Acciones", "Convierte la opción aprobada en factura legal correlativa con un solo clic."],
            ["Reabrir", "Menú Acciones", "Permite devolver un presupuesto aceptado a borrador para cotizar cambios."],
        ],
        [38, 34, 106]
    )

    pdf.draw_callout_box(
        "Técnica Comercial: El Efecto Contraste con Doble Opción",
        "Presentar siempre dos alternativas (una estándar completa y una opción superior o premium con acabados especiales) incrementa la tasa de aceptación hasta un 30%. El cliente compara entre tus opciones en lugar de buscar presupuestos en la competencia.",
        kind="tip"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 6: MÓDULO DE CATÁLOGO — ESCALADOS Y VARIANTES
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 05", "Catálogo de Productos — Escalados y Variantes", "Gestión de productos sin códigos artificiales, tramos por volumen y atributos")

    pdf.draw_two_images(
        ASSETS_DIR / "05_productos_catalogo.png",
        "Directorio de productos con badges de variantes y tramos.",
        ASSETS_DIR / "05b_producto_modal_escalado.png",
        "Modal de escalado de precios por tramos de cantidad.",
        h_mm=54
    )

    pdf.draw_section_subtitle("Filosofía de Catálogo Sin Códigos Forzados")
    pdf.draw_paragraph("En la mayoría de estudios y pequeñas empresas de servicios creativos o artesanos, memorizar códigos SKU artificiales resulta engorroso. SIF PyME organiza el catálogo mediante búsqueda semántica por nombre y descripción técnica:")

    pdf.draw_bullet("Pestaña 1 · Datos Generales:", "Nombre comercial del producto o servicio, descripción técnica detallada, precio unitario de referencia, porcentaje de IVA aplicable y retención de IRPF opcional.")
    pdf.draw_bullet("Pestaña 2 · Escalado de Precios por Volumen:", "Permite definir tramos automáticos de precio según la cantidad encargada. Por ejemplo: de 1 a 49 unidades a 2,50 €/ud; de 50 a 99 unidades a 2,10 €/ud; de 100 unidades en adelante a 1,85 €/ud. Al presupuestar o facturar, el precio unitario se ajusta solo según la cantidad introducida.")
    pdf.draw_bullet("Pestaña 3 · Variantes y Colores:", "Configuración de atributos especiales como colores de forro, acabados en relieve o tipos de papel, cada uno con su recargo monetario (+€) o precio fijo y visualización de muestra cromática con código hexadecimal.")
    pdf.draw_bullet("Función Rápida «Guardar en Catálogo»:", "Si durante la redacción de una factura o presupuesto introduces un concepto nuevo no registrado previamente, puedes pulsar el botón «Guardar en catálogo» para incorporarlo a la base de datos sin salir del formulario.")

    pdf.draw_table(
        ["Pestaña", "Parámetros Clave", "Beneficio Operativo"],
        [
            ["General", "Nombre, detalle técnico, IVA, IRPF", "Búsqueda semántica instantánea en autocompletado."],
            ["Escalados", "Cant. Mínima, Cant. Máxima, Precio €", "Aplicación automática de tarifas mayoristas por volumen."],
            ["Variantes", "Color, acabado, recargo adicional €", "Gestión ágil de personalizaciones sin multiplicar referencias."],
        ],
        [32, 68, 78]
    )

    pdf.draw_callout_box(
        "Buenas Prácticas en Tarifas por Volumen",
        "Define siempre el último tramo de escalado dejando el campo «Cantidad Máxima» vacío («En adelante…»). De este modo, cualquier volumen superior continuará beneficiándose del precio por tramo mayorista sin generar inconsistencias en los cálculos.",
        kind="tip"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 7: MÓDULO DE DESCUENTOS COMERCIALES
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 06", "Módulo de Descuentos — Promociones y Visibilidad", "Campañas en %, importes fijos €, alcance por catálogo y visibilidad fiscal")

    pdf.draw_section_subtitle("Gestión de Tarifas Promocionales y Bonificaciones")
    pdf.draw_paragraph("SIF PyME incorpora un motor exclusivo de Descuentos Comerciales (/descuentos) para articular políticas de fidelización, acuerdos de distribución o campañas por volumen con total flexibilidad:")

    pdf.draw_bullet("Tipología de Descuentos:", "Define bonificaciones porcentuales (% sobre la base) o deducciones monetarias fijas en euros (ej. «Campaña Bienvenida 50,00 €» o «Descuento Volumen 10%»).")
    pdf.draw_bullet("Alcance Global o por Producto:", "Los descuentos pueden aplicarse al total del documento («Todos los productos») o acotarse a referencias concretas del catálogo seleccionadas en el formulario.")
    pdf.draw_bullet("Modo Descuento Visible:", "El descuento se desglosa explícitamente en el PDF antes de impuestos, permitiendo al cliente final visualizar con claridad el ahorro obtenido.")
    pdf.draw_bullet("Modo Descuento Oculto (Neto):", "Aplica el descuento internamente en el precio unitario efectivo sin mostrar deducciones adicionales en el PDF. Ideal para tarifas de distribución o presupuestos entre profesionales.")

    pdf.draw_table(
        ["Modalidad", "Ámbito de Aplicación", "Comportamiento en PDF Oficial"],
        [
            ["Porcentaje Global", "Todos los productos", "Línea visible de deducción % con recálculo de base imponible."],
            ["Importe Fijo Global", "Todos los productos", "Descuento en € netos distribuido sobre el subtotal de la oferta."],
            ["Específico de Catálogo", "Productos seleccionados", "Aplica bonificación únicamente a los conceptos sujetos a promoción."],
            ["Descuento Oculto", "Global o por producto", "Precio unitario ajustado en factura/presupuesto sin revelar el margen."],
        ],
        [44, 46, 88]
    )

    pdf.draw_section_subtitle("Aplicación Fluida en Facturas y Presupuestos")
    pdf.draw_paragraph("Al emitir una factura o redactar una opción de presupuesto, el selector «Descuento Comercial» carga automáticamente las promociones vigentes. El panel de liquidación económica recalcula en tiempo real las bases imponibles, el IVA y las retenciones.")

    pdf.draw_callout_box(
        "Tratamiento Fiscal del Descuento Comercial (Ley del IVA)",
        "Según el art. 78 de la Ley 37/1992 del IVA, los descuentos y bonificaciones concedidos previa o simultáneamente al momento en que la operación se realice no forman parte de la base imponible. SIF PyME deduce el descuento antes del cómputo tributario para garantizar la total exactitud contable.",
        kind="fiscal"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 8: MÓDULO DE CLIENTES — DIRECTORIO Y VALIDACIÓN
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 07", "Módulo de Clientes — Directorio y Validación Fiscal", "Alta de clientes, validación oficial de NIF/NIE/CIF y clientes particulares")

    pdf.draw_image_figure(
        ASSETS_DIR / "06_clientes_directorio.png",
        "Directorio unificado de clientes: identificadores fiscales validados, badge de particular, contacto y acciones rápidas.",
        h_mm=76
    )

    pdf.draw_section_subtitle("Gestión Integral de Fichas de Clientes")
    pdf.draw_paragraph("El directorio de Clientes centraliza la información fiscal y comercial de todos los destinatarios de tus facturas y presupuestos:")

    pdf.draw_bullet("Validación Estricta de NIF, NIE y CIF:", "La aplicación incorpora el algoritmo oficial de verificación de Hacienda. Si introduces un NIF, NIE o CIF incorrecto (por ejemplo una letra que no cuadra con el número), el sistema alerta al usuario y bloquea el guardado para evitar requerimientos tributarios.")
    pdf.draw_bullet("Edición y Modificación de Clientes:", "Desde la tabla del directorio, cada cliente cuenta con un botón «Editar» que permite actualizar su razón social, domicilio, teléfonos o correo electrónico. Las modificaciones se aplican a futuras emisiones respetando el snapshot histórico de facturas ya emitidas.")
    pdf.draw_bullet("Autocompletado Reactivo en Facturación:", "Al redactar una nueva factura o presupuesto, basta con escribir las primeras letras del cliente en el campo destinatario para que el sistema autocomplete al instante todos sus datos fiscales y forma de pago.")
    pdf.draw_bullet("Soporte para Clientes Particulares:", "El identificador fiscal es opcional. Para clientes particulares que no requieran factura con deducción fiscal o para facturas simplificadas, puedes registrar al cliente únicamente con su nombre y teléfono.")
    pdf.draw_bullet("Regla de Unicidad Fiscal:", "No es posible dar de alta dos clientes activos con el mismo NIF o CIF. Si intentas registrar un NIF duplicado, el sistema te redirigirá a la ficha existente para prevenir inconsistencias en los libros contables.")
    pdf.draw_bullet("Modal Rápido In-Situ:", "Desde la pantalla de emisión de facturas o presupuestos, puedes pulsar «Nuevo Cliente…» para dar de alta y seleccionar a un cliente al instante sin abandonar la redacción de la factura.")
    pdf.draw_bullet("Eliminación Protegida:", "Al eliminar un cliente, la aplicación comprueba cuántas facturas y presupuestos tiene asociados y traslada toda la información a la Papelera de Reciclaje, permitiendo una restauración total si fue accidental.")

    pdf.draw_callout_box(
        "Verificación de Datos Censales en el Censo VIES / AEAT",
        "Antes de emitir una factura exenta de IVA a un cliente comunitario o empresa extranjera, comprueba que su NIF-IVA está activo en el censo VIES de la Comisión Europea. En clientes nacionales, asegúrate de que la razón social coincida exactamente con la registrada en el censo de la Agencia Tributaria.",
        kind="fiscal"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 9: MÓDULO DE SEGURIDAD — VERSIONES Y PAPELERA
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 08", "Módulo de Seguridad — Versiones y Papelera", "Auditoría histórica con Time Machine, reversión de documentos y recuperación lógica")

    pdf.draw_image_figure(
        ASSETS_DIR / "07_papelera_versiones.png",
        "Papelera de reciclaje: documentos eliminados organizados por pestañas, fecha de borrado, importes y botones de restauración.",
        h_mm=76
    )

    pdf.draw_section_subtitle("Auditoría Histórica con Time Machine")
    pdf.draw_paragraph("Cada vez que creas, modificas una línea o alteras el estado de una factura o presupuesto, SIF PyME genera un snapshot inmutable de auditoría en la base de datos:")

    pdf.draw_bullet("Inmutabilidad y Trazabilidad:", "Desde el botón «Historial de Versiones…» del inspector lateral puedes consultar la evolución cronológica de cualquier documento: fecha y hora exacta de cada cambio, motivo de la modificación e importe total de la versión.")
    pdf.draw_bullet("Restauración sin Pérdida:", "Al seleccionar una versión antigua y pulsar «Restaurar esta versión», el sistema no sobreescribe la base de datos: crea una nueva versión con el contenido recuperado, preservando intacto el historial anterior.")

    pdf.draw_section_subtitle("Papelera de Reciclaje y Borrado Lógico")
    pdf.draw_paragraph("Eliminar un documento en SIF PyME nunca destruye los datos de inmediato:")
    pdf.draw_bullet("Borrado Lógico Preventivo:", "Al pulsar «Eliminar», el documento pasa a la Papelera de Reciclaje (`is_deleted = 1`). Deja de figurar en los listados activos y contadores, pero conserva todas sus líneas, importes y PDFs intactos.")
    pdf.draw_bullet("Acción «Restaurar»:", "Devuelve la factura o presupuesto al listado activo en su estado original con un solo clic.")
    pdf.draw_bullet("Acción «Destruir Definitivamente»:", "Purga irreversible del documento individual tras solicitar confirmación expresa.")
    pdf.draw_bullet("Botón «Vaciar Papelera…»:", "Elimina de forma definitiva todo el contenido de la papelera tras solicitar confirmación modal de seguridad.")

    pdf.draw_callout_box(
        "Conservación Obligatoria de Facturas por Ley (4 Años)",
        "El artículo 29 de la Ley General Tributaria establece la obligación de conservar las facturas emitidas y recibidas durante al menos 4 años (plazo de prescripción fiscal). Nunca destruyas definitivamente una factura emitida oficial: en caso de error, utiliza las funciones de edición con nueva versión o emisión de factura rectificativa.",
        kind="warning"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 10: MÓDULO DE CONFIGURACIÓN Y COPIAS DE SEGURIDAD
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 09", "Configuración, Onboarding y Respaldos", "Setup fiscal, series diferenciadas Con/Sin IVA, almacenamiento y snapshots")

    pdf.draw_image_figure(
        ASSETS_DIR / "08_configuracion_empresa.png",
        "Ajustes del sistema: datos fiscales del emisor, series independientes con/sin IVA, carpetas y copias de seguridad.",
        h_mm=74
    )

    pdf.draw_section_subtitle("Configuración Fiscal y Preferencias del Emisor")
    pdf.draw_paragraph("En la pantalla de Ajustes de Empresa (`/configuracion`) defines los datos fiscales que encabezarán tus facturas y presupuestos:")

    pdf.draw_bullet("Datos Obligatorios del Emisor:", "El Nombre o Razón Social y el NIF/CIF son estrictamente obligatorios. Sin ellos, el botón de emisión permanece bloqueado por seguridad jurídica.")
    pdf.draw_bullet("Series y Numeración Diferenciadas:", "Permite configurar series e inicios independientes para Facturas Con IVA (ej. «FAC-2026-001») y Facturas Exentas Sin IVA (ej. «FS-2026-001»), clasificándose en carpetas físicas separadas en disco.")
    pdf.draw_bullet("Asistente de Bienvenida (Onboarding):", "Guía inicial en ventana modal para parametrizar datos fiscales y sugerir la mejor ruta de almacenamiento (Local, iCloud Drive o OneDrive).")
    pdf.draw_bullet("Indicador de Estado Dinámico:", "El indicador superior muestra «Configuración completa» únicamente cuando todos los datos fiscales indispensables están correctamente cumplimentados.")
    pdf.draw_bullet("Snapshot del Emisor en Facturas:", "Cada vez que emites una factura, se guarda una copia exacta (snapshot) de los datos del emisor vigentes en ese momento, protegiendo las facturas del pasado.")

    pdf.draw_section_subtitle("Almacenamiento de Documentos y Motor de Copias")
    pdf.draw_bullet("Rutas Sugeridas de Almacenamiento:", "Pulsa «Rutas Sugeridas…» para elegir entre la carpeta Documentos de tu usuario, tu unidad de iCloud Drive / OneDrive o una carpeta personalizada.")
    pdf.draw_bullet("Motor de Snapshots Automáticos:", "La aplicación genera una copia de seguridad automática de la base de datos cada vez que se emite o modifica una factura, reteniendo automáticamente los últimos 50 respaldos.")
    pdf.draw_bullet("Copias Manuales y Restauración:", "Puedes pulsar «Crear Copia de Seguridad Ahora» en cualquier momento o restaurar una copia previa, lo cual genera siempre un respaldo preventivo de seguridad antes de aplicar la restauración.")

    pdf.draw_callout_box(
        "Organización Automática de Archivos PDF",
        "Los archivos PDF generados por la aplicación se organizan en tu disco dentro de subcarpetas automáticas estructuradas por Año y Mes (ej. `~/Documents/Facturas/PDFs/2026/10/FAC-2026-10-21-001.pdf`). Esto permite respaldar o enviar a tu gestoría carpetas completas de un trimestre sin mezclar documentos.",
        kind="tip"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 11: ATAJOS DE TECLADO, PAGINACIÓN Y CONTROLES
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 10", "Guía de Atajos de Teclado y Controles Globales", "Productividad, paginación de datos, sumatorios en tiempo real y atajos rápidos")

    pdf.draw_section_subtitle("Controles de Interfaz y Navegación Eficiente")
    pdf.draw_paragraph("SIF PyME está optimizado para permitir una operativa extraordinariamente ágil, minimizando el uso del ratón y ofreciendo información resumida instantánea en todas las vistas:")

    pdf.draw_bullet("Selector de Paginación Rápida:", "En el pie de cada tabla puedes seleccionar visualizar 25, 50 o 100 elementos por página. Los controles «Anterior» y «Siguiente» permiten desplazarse velozmente entre páginas de registros.")
    pdf.draw_bullet("Barra de Sumatorios Dinámicos:", "La barra inferior no solo muestra el recuento de registros: calcula en tiempo real la suma exacta de las Bases Imponibles y el Importe Total facturado en la página visible, permitiendo cotejar cifras de un vistazo.")
    pdf.draw_bullet("Búsqueda con Filtrado Reactivo:", "El cuadro de búsqueda procesa tu texto en tiempo real con debounce integrado, evitando recargas molestas de la aplicación mientras buscas un cliente o número.")

    pdf.draw_section_subtitle("Tabla de Referencia Rápida de Controles y Atajos")
    pdf.draw_table(
        ["Atajo / Control", "Pantalla Aplicable", "Acción Realizada"],
        [
            ["Cmd / Ctrl + N", "Global (Cualquiera)", "Abre de inmediato el formulario para crear una Nueva Factura."],
            ["Cmd / Ctrl + P", "Global (Cualquiera)", "Abre de inmediato el formulario para crear un Nuevo Presupuesto."],
            ["Cmd / Ctrl + F", "Facturas / Clientes", "Enfoca automáticamente la barra de búsqueda del listado."],
            ["Escape (Esc)", "Modales y Hojas", "Cierra cualquier diálogo modal, inspector lateral o ventana de aviso."],
            ["Enter", "Diálogos modales", "Confirma la acción predeterminada del diálogo (Guardar / Seleccionar)."],
            ["Clic en fila", "Listado de Facturas", "Selecciona la factura y abre sus detalles completos en el Inspector."],
            ["Doble clic fila", "Listado de Facturas", "Abre directamente la factura en modo edición completa."],
            ["Tabulador (Tab)", "Formularios", "Salta ordenadamente de un campo al siguiente sin tocar el ratón."],
        ],
        [36, 42, 100]
    )

    pdf.draw_section_subtitle("Anatomía de Controles: Toolbar, Inspector y Botones de Acción")
    pdf.draw_paragraph("Cada módulo de SIF PyME respeta estrictamente los principios de diseño de macOS HIG para garantizar previsibilidad y velocidad de trabajo:")

    pdf.draw_bullet("Barra de Herramientas Superior (Toolbar):", "Concentra las acciones de creación global: «+ Nueva Factura» (botón primario de acento azul), «+ Nuevo Presupuesto», selector del ejercicio fiscal activo y cajón de búsqueda en vivo con icono de lupa.")
    pdf.draw_bullet("Botones de Acción por Registro:", "Cada fila de las tablas incorpora accesos rápidos: «PDF» (apertura o descarga inmediata), «Editar» (modificación con snapshot automático de versión) y menú «Acciones» para transiciones de estado.")
    pdf.draw_bullet("Inspector Lateral (NSInspector):", "Panel contextual derecho en facturas que se activa al pulsar cualquier fila. Presenta el desglose económico exacto (Base, IVA, IRPF y Total), estado del cobro y accesos a «Historial de Versiones…» y «Eliminar Factura…».")
    pdf.draw_bullet("Paginación y Sumatorios en Vivo:", "La barra inferior permite conmutar la vista entre 25, 50 o 100 registros por página, avanzar/retroceder con «Anterior» / «Siguiente» y consultar la suma total de las bases imponibles de la página actual.")

    pdf.draw_callout_box(
        "Flujo de Trabajo Recomendado para Máxima Eficiencia",
        "Para emitir una factura en menos de 20 segundos: pulsa Cmd+N (o Ctrl+N), teclea las 3 primeras letras del cliente y presiona Enter; salta con Tabulador a las líneas, añade los conceptos desde el catálogo con autocompletado y pulsa «Emitir Factura y Descargar PDF». Todo el proceso se ejecuta sin levantar las manos del teclado.",
        kind="tip"
    )

    # ══════════════════════════════════════════════════════════
    # PÁGINA 12: PREGUNTAS FRECUENTES (FAQ) Y FICHA TÉCNICA
    # ══════════════════════════════════════════════════════════
    pdf.add_chapter_page("CAPÍTULO 11", "Preguntas Frecuentes & Ficha Técnica", "Resolución de incidencias comunes, soporte operativo y especificaciones técnicas")

    pdf.draw_section_subtitle("Preguntas Frecuentes y Solución de Dudas")

    faqs = [
        ("¿Por qué el botón «Emitir Factura» aparece bloqueado o deshabilitado?",
         "La causa más habitual es que no se han completado los datos fiscales obligatorios del emisor. Accede a Ajustes de Empresa (`/configuracion`) y asegúrate de rellenar la Razón Social y el NIF/CIF hasta que el badge superior marque «Configuración completa»."),
        ("El sistema indica: «El identificador fiscal no es válido».",
         "El validador integrado comprueba la letra de control de los NIFs y CIFs. Comprueba que el número no tenga errores tipográficos. Si se trata de un cliente particular que no requiere factura con NIF, déjalo en blanco."),
        ("¿Dónde se guardan físicamente mis datos y mis facturas?",
         "En macOS los datos se guardan en `~/Library/Application Support/SIF PyME` y los PDFs en `~/Documents/Facturas/PDFs`. En Windows se almacenan en `C:\\Users\\TuUsuario\\Facturas`. Puedes modificar la ruta de PDFs en Ajustes."),
        ("¿Cómo rectifico una factura emitida que contenía un error?",
         "Selecciona la factura en la tabla y pulsa «Editar Factura». Modifica los datos erróneos y pulsa «Guardar Cambios y Descargar PDF». El documento PDF se regenerará con los datos corregidos y la versión anterior quedará registrada en el historial."),
        ("¿Qué ocurre si cambio de ordenador o formateo el equipo?",
         "Dado que SIF PyME es 100% local, basta con copiar la carpeta `Facturas` o hacer una copia de seguridad desde Ajustes → Copias de Seguridad → «Crear Copia de Seguridad Ahora». Al restaurarla en tu nuevo ordenador, recuperarás todos tus datos intactos."),
        ("¿Necesito conexión a Internet para utilizar el programa?",
         "No. SIF PyME es 100% independiente y funciona sin conexión a Internet. Solo necesitarás conexión si decides enviar los PDFs por correo electrónico a tus clientes desde tu cliente de correo habitual.")
    ]

    for q, a in faqs:
        pdf.set_font(pdf.serif_font, 'B', 8.5)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(178, 4.2, f"• {q}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_x(20)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*C_TEXT)
        pdf.multi_cell(174, 3.6, a, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    # Ficha Técnica y Cierre
    pdf.set_y(228)
    pdf.set_fill_color(*C_BG_CARD)
    pdf.set_draw_color(*C_BORDER)
    pdf.rect(16, 228, 178, 48, style='FD')

    pdf.set_xy(22, 232)
    pdf.set_font(pdf.serif_font, 'B', 9.5)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(166, 5, "ESPECIFICACIONES TÉCNICAS DE LA PLATAFORMA", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    specs = [
        ("Motor de Base de Datos:", "SQLite 3 con Journal Mode WAL (Write-Ahead Logging) y Foreign Keys activas."),
        ("Servidor de Aplicación:", "FastAPI + Uvicorn ASGI en hilo local dedicado (127.0.0.1)."),
        ("Entorno Desktop:", "PySide6 (Qt 6) con motor QWebEngineView (Chromium embebido nativo) sin navegador externo."),
        ("Generación Editorial PDF:", "fpdf2 con gestión de desbordamiento, tipografía TrueType UTF-8 y redondeo financiero Decimal."),
        ("Versionado y Auditoría:", "Control de versiones inmutable con snapshots JSON de auditoría por documento."),
        ("Garantía de Privacidad:", "Cero telemetría, cero almacenamiento en la nube no autorizado y cifrado de reposo por sistema.")
    ]
    for s_lbl, s_val in specs:
        pdf.set_x(22)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(42, 3.8, s_lbl)
        pdf.set_font(pdf.sans_font, '', 7.5)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(124, 3.8, s_val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    target_pdf = Path(output_path).resolve()
    target_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(target_pdf))
    print(f"[Manual Generator] Manual de usuario generado con éxito en: {target_pdf}")
    print(f"[Manual Generator] Tamaño del archivo: {target_pdf.stat().st_size} bytes ({target_pdf.stat().st_size / 1024:.2f} KB)")
    print(f"[Manual Generator] Total de páginas maquetadas: {pdf.page_no()}")
    return target_pdf


def main():
    parser = argparse.ArgumentParser(description="Generador del Manual de Usuario de SIF PyME")
    parser.add_argument("--recapture", action="store_true", help="Vuelve a capturar todas las pantallas antes de generar el PDF")
    parser.add_argument("-o", "--output", type=str, default=str(OUTPUT_PDF), help="Ruta de destino del archivo PDF generado")
    args = parser.parse_args()

    # Si se solicitó recapture o si faltan capturas, ejecutar el pipeline de capturas
    needed_screenshots = [
        "01_facturas_principal.png",
        "02_nueva_factura.png",
        "03_presupuestos_principal.png",
        "04_nuevo_presupuesto.png",
        "05_productos_catalogo.png",
        "05b_producto_modal_escalado.png",
        "06_clientes_directorio.png",
        "07_papelera_versiones.png",
        "08_configuracion_empresa.png"
    ]

    missing = [s for s in needed_screenshots if not (ASSETS_DIR / s).exists()]

    if args.recapture or missing:
        print(f"[Manual] Iniciando pipeline de capturas reales (Faltantes: {len(missing)})...")
        from scripts.capture_screenshots import run_capture_pipeline
        run_capture_pipeline()

    build_manual_pdf(output_path=Path(args.output).resolve())


if __name__ == "__main__":
    main()
