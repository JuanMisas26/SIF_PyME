from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.paths import TEMPLATES_DIR
from app.database import db_connection

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_sidebar_counts():
    try:
        with db_connection() as conn:
            facturas = conn.execute("SELECT COUNT(*) FROM facturas WHERE is_deleted = 0").fetchone()[0]
            presupuestos = conn.execute("SELECT COUNT(*) FROM presupuestos WHERE is_deleted = 0").fetchone()[0]
            clientes = conn.execute("SELECT COUNT(*) FROM clientes WHERE is_deleted = 0").fetchone()[0]
            productos = conn.execute("SELECT COUNT(*) FROM productos WHERE is_deleted = 0").fetchone()[0]
            descuentos = conn.execute("SELECT COUNT(*) FROM descuentos WHERE is_deleted = 0 AND activo = 1").fetchone()[0]
            papelera = conn.execute("SELECT (SELECT COUNT(*) FROM facturas WHERE is_deleted = 1) + (SELECT COUNT(*) FROM presupuestos WHERE is_deleted = 1)").fetchone()[0]
            return {
                "facturas": facturas,
                "presupuestos": presupuestos,
                "clientes": clientes,
                "productos": productos,
                "descuentos": descuentos,
                "papelera": papelera
            }
    except Exception:
        return {"facturas": 0, "presupuestos": 0, "clientes": 0, "productos": 0, "descuentos": 0, "papelera": 0}


templates.env.globals['get_sidebar_counts'] = get_sidebar_counts


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/macos", response_class=HTMLResponse)
async def macos_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/nueva-factura", response_class=HTMLResponse)
async def nueva_factura(request: Request):
    return templates.TemplateResponse(request=request, name="nueva_factura.html", context={"factura_id": None})


@router.get("/facturas/{id}/editar", response_class=HTMLResponse)
async def editar_factura_page(request: Request, id: int):
    return templates.TemplateResponse(request=request, name="nueva_factura.html", context={"factura_id": id})



@router.get("/facturas/{id}", response_class=RedirectResponse)
async def ver_factura_redirect(id: int):
    return RedirectResponse(url=f"/api/facturas/{id}/pdf", status_code=303)


@router.get("/clientes", response_class=HTMLResponse)
async def clientes_page(request: Request):
    return templates.TemplateResponse(request=request, name="clientes.html")


@router.get("/productos", response_class=HTMLResponse)
async def productos_page(request: Request):
    return templates.TemplateResponse(request=request, name="productos.html")


@router.get("/descuentos", response_class=HTMLResponse)
async def descuentos_page(request: Request):
    return templates.TemplateResponse(request=request, name="descuentos.html")


@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion_page(request: Request):
    return templates.TemplateResponse(request=request, name="configuracion.html")


@router.get("/presupuestos", response_class=HTMLResponse)
async def presupuestos_page(request: Request):
    return templates.TemplateResponse(request=request, name="presupuestos.html")


@router.get("/nuevo-presupuesto", response_class=HTMLResponse)
async def nuevo_presupuesto_page(request: Request):
    return templates.TemplateResponse(request=request, name="nuevo_presupuesto.html", context={"presupuesto_id": None})


@router.get("/presupuestos/{id}/editar", response_class=HTMLResponse)
async def editar_presupuesto_page(request: Request, id: int):
    return templates.TemplateResponse(request=request, name="nuevo_presupuesto.html", context={"presupuesto_id": id})



@router.get("/papelera", response_class=HTMLResponse)
async def papelera_page(request: Request):
    return templates.TemplateResponse(request=request, name="papelera.html")
